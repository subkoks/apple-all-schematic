"""Versioned JSON-lines adapter. No Qt imports and no interactive terminal prompts."""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import logging
import os
import sys
import time
from pathlib import Path

from telethon.errors import SessionPasswordNeededError

import tg_schematic_downloader as scraper
from validation import validate_channel_names, validate_keywords

PROTOCOL_VERSION = 1
MAX_COMMAND_BYTES = 16_384
MAX_LOGIN_LENGTH = 4_096
MAX_MESSAGE_LIMIT = 1_000_000
PROGRESS_INTERVAL_SECONDS = 0.1


class Protocol:
    def __init__(self, output):
        self.output = output
        self.responses: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        self.cancelled = asyncio.Event()
        self.pending: str | None = None
        self.had_errors = False
        self.last_progress: dict[str, float] = {}

    def emit(self, event_type: str, **fields):
        if event_type == "error":
            self.had_errors = True
        self.output.write(
            json.dumps({"type": event_type, "version": PROTOCOL_VERSION, **fields}) + "\n"
        )
        self.output.flush()

    def command(self, line: bytes):
        try:
            if len(line) > MAX_COMMAND_BYTES:
                raise ValueError
            command = json.loads(line)
            if not isinstance(command, dict):
                raise ValueError
            if command.get("command") == "cancel":
                self.cancelled.set()
                return
            if command.get("command") != "login_response":
                raise ValueError
            value = command.get("value")
            if (
                command.get("field") != self.pending
                or self.pending is None
                or not isinstance(value, str)
                or not value
                or len(value) > MAX_LOGIN_LENGTH
                or self.responses.full()
            ):
                raise ValueError
            self.responses.put_nowait(value)
        except (ValueError, UnicodeError):
            self.emit("error", message="Invalid or unexpected engine command.")

    async def prompt(self, field: str) -> str:
        self.pending = field
        self.emit("login_required", field=field)
        try:
            return await self.responses.get()
        finally:
            self.pending = None

    async def read_commands(self, reader: asyncio.StreamReader):
        try:
            while line := await reader.readline():
                self.command(line)
        except (ValueError, OSError):
            self.emit("error", message="Command stream failed.")
        finally:
            # A parent that closes stdin must not leave an orphan login/download.
            self.cancelled.set()

    def progress(self, event: dict):
        kind = event["type"]
        if kind in {"file_error", "resolve_error"}:
            self.emit("error", channel=event["channel"], message="Channel or file download failed.")
            return
        if kind == "file_bytes":
            now = time.monotonic()
            channel = event["channel"]
            if (
                event["received"] != event["total"]
                and now - self.last_progress.get(channel, 0) < PROGRESS_INTERVAL_SECONDS
            ):
                return
            self.last_progress[channel] = now
            self.emit(
                "progress",
                channel=event["channel"],
                filename=event["filename"],
                done=event["received"],
                total=event["total"],
                bytes=event["received"],
            )
            return
        self.emit(kind, **{k: v for k, v in event.items() if k != "type"})


def configure_paths(args):
    root = args.data_dir or Path.home() / "Library/Application Support/subkoks/BoardVault"
    root = root.expanduser().resolve()
    scraper.STATE_FILE = root / "state.json"
    scraper.SESSION_FILE = root / "tg_scraper_session"
    scraper.DOWNLOAD_DIR = (
        (args.download_dir or Path.home() / "Downloads/BoardVault").expanduser().resolve()
    )
    return root


async def authorize(client, protocol: Protocol):
    if await client.is_user_authorized():
        return
    phone = (await protocol.prompt("phone")).strip()
    sent = await client.send_code_request(phone)
    code = (await protocol.prompt("code")).strip()
    try:
        await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        await client.sign_in(password=await protocol.prompt("password"))


async def operation(args, protocol: Protocol, client_factory=None):
    root = configure_paths(args)
    if args.operation == "config" or args.list_channels:
        protocol.emit("config", channels=scraper.CHANNELS)
        return
    if args.limit is not None and not 0 <= args.limit <= MAX_MESSAGE_LIMIT:
        raise ValueError("Invalid limit")
    channels = validate_channel_names(args.channels or sum(scraper.CHANNELS.values(), []))
    keywords = validate_keywords(args.filter) if args.filter else None
    root.mkdir(parents=True, exist_ok=True)
    # Native processes serialize shared state/session access. Qt users must close Qt first.
    with (root / "native-engine.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.operation in {"scan", "organize", "undo"}:
            from native_organizer import perform

            await perform(args, root, protocol)
            return
        api_id = os.environ.get("TG_API_ID", "")
        api_hash = os.environ.get("TG_API_HASH", "")
        if not api_id.isdecimal() or not api_hash:
            protocol.emit("error", message="Set Telegram API credentials in Settings.")
            return
        factory = client_factory or scraper.TelegramClient
        client = factory(str(scraper.SESSION_FILE), int(api_id), api_hash)
        try:
            await client.connect()
            if args.operation == "logout":
                if await client.is_user_authorized():
                    await client.log_out()
                return
            await authorize(client, protocol)
            if args.operation == "login":
                return
            state = scraper.load_state() if args.resume else {"downloaded": {}}
            for channel in channels:
                await scraper.process_channel(
                    client,
                    channel,
                    state,
                    args.apple,
                    keywords,
                    args.limit,
                    args.resume,
                    protocol.progress,
                    safe_files=True,
                    exact_keywords=True,
                )
        finally:
            await client.disconnect()


async def serve(args, protocol: Protocol, reader: asyncio.StreamReader):
    command_task = asyncio.create_task(protocol.read_commands(reader))
    work = asyncio.create_task(operation(args, protocol))
    cancellation = asyncio.create_task(protocol.cancelled.wait())
    status = "ok"
    try:
        completed, _ = await asyncio.wait((work, cancellation), return_when=asyncio.FIRST_COMPLETED)
        if cancellation in completed and not work.done():
            status = "cancelled"
            work.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await work
    except Exception:
        status = "error"
        # Exceptions can include phone numbers, login codes or API credentials.
        protocol.emit("error", message="Engine operation failed. Check settings and try again.")
    finally:
        for task in (work, cancellation, command_task):
            task.cancel()
        await asyncio.gather(work, cancellation, command_task, return_exceptions=True)
    if protocol.had_errors and status == "ok":
        status = "error"
    protocol.emit("done", status=status)
    return 1 if status == "error" else 0


def run(args):
    output = sys.stdout
    protocol = Protocol(output)
    logging.disable(logging.CRITICAL)

    async def start():
        reader = asyncio.StreamReader(limit=MAX_COMMAND_BYTES)
        transport, _ = await asyncio.get_running_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer
        )
        try:
            return await serve(args, protocol, reader)
        finally:
            transport.close()

    # Existing human-readable prints and third-party diagnostics must never reach IPC/logs.
    with (
        open(os.devnull, "w") as sink,
        contextlib.redirect_stdout(sink),
        contextlib.redirect_stderr(sink),
    ):
        try:
            return asyncio.run(start())
        except Exception:
            protocol.emit("error", message="Engine could not start.")
            protocol.emit("done", status="error")
            return 1
