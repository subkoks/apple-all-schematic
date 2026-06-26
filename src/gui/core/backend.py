"""Download orchestration bridged to Qt signals.

Owns a single Telethon client for the app session and runs the channel loop as a
cancellable :class:`asyncio.Task` on the shared qasync event loop. Progress events
from :func:`tg_schematic_downloader.process_channel` are re-emitted as Qt signals so
widgets can update live without touching stdout or running a worker thread.
"""

from __future__ import annotations

import asyncio
import contextlib

from PySide6.QtCore import QObject, Signal
from telethon import TelegramClient

import tg_schematic_downloader as scraper

from .auth import AuthError, AuthPrompts, build_client, ensure_authorized
from .config import get_credentials, load_config


class DownloadController(QObject):
    """Drives scraping and surfaces progress as Qt signals."""

    # Raw structured events from process_channel (see its emit() payloads).
    event = Signal(dict)
    log = Signal(str)
    running_changed = Signal(bool)
    finished = Signal(dict)  # totals summary
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._client: TelegramClient | None = None
        self._task: asyncio.Task | None = None
        self.config = load_config()

    # ── Client / auth ──────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def has_client(self) -> bool:
        return self._client is not None

    async def ensure_ready(self, prompts: AuthPrompts) -> None:
        """Build (once) and authorize the client, walking the login UI if needed."""
        creds = get_credentials()
        if not creds.is_complete:
            raise AuthError("Telegram API credentials are not set.")
        if self._client is None:
            self._client = await build_client(creds.api_id, creds.api_hash)
        await ensure_authorized(self._client, prompts)

    async def is_authorized(self) -> bool:
        return self._client is not None and await self._client.is_user_authorized()

    async def shutdown(self) -> None:
        self.stop()
        if self._client is not None:
            with contextlib.suppress(Exception):  # best-effort teardown
                await self._client.disconnect()

    # ── Run / stop ─────────────────────────────────────────────────────────────

    def start(
        self,
        channels: list[str],
        *,
        apple_only: bool,
        keyword_filter: list[str] | None,
        limit: int | None,
        resume: bool,
    ) -> None:
        if self.is_running:
            return
        self._task = asyncio.ensure_future(
            self._run(channels, apple_only, keyword_filter, limit, resume)
        )

    def stop(self) -> None:
        if self.is_running:
            self._task.cancel()

    async def _run(
        self,
        channels: list[str],
        apple_only: bool,
        keyword_filter: list[str] | None,
        limit: int | None,
        resume: bool,
    ) -> None:
        self.running_changed.emit(True)
        totals = {"channels": 0, "downloaded": 0, "skipped": 0, "errors": 0}

        def on_event(ev: dict) -> None:
            if ev.get("type") == "channel_done":
                totals["channels"] += 1
                totals["downloaded"] += ev.get("count", 0)
                totals["skipped"] += ev.get("skipped", 0)
                totals["errors"] += ev.get("errors", 0)
            self.event.emit(ev)

        if self._client is None:
            self.failed.emit("Not connected to Telegram.")
            self.running_changed.emit(False)
            return

        state = scraper.load_state() if resume else {"downloaded": {}}
        try:
            for channel in channels:
                await scraper.process_channel(
                    client=self._client,
                    channel=channel,
                    state=state,
                    apple_only=apple_only,
                    keyword_filter=keyword_filter,
                    limit=limit,
                    resume=resume,
                    progress=on_event,
                )
            self.finished.emit(totals)
            self.log.emit(
                f"Done — {totals['downloaded']} downloaded, "
                f"{totals['skipped']} skipped, {totals['errors']} errors"
            )
        except asyncio.CancelledError:
            self.log.emit("Stopped by user. State is saved up to the last file.")
            raise
        except Exception as e:  # noqa: BLE001 — report any run failure to the UI
            self.failed.emit(str(e))
        finally:
            self.running_changed.emit(False)
