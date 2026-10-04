"""Credential-free protocol and Telethon adapter tests."""

import asyncio
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import native_engine as engine


def events(protocol):
    return [json.loads(line) for line in protocol.output.getvalue().splitlines()]


def options(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path,
        download_dir=tmp_path / "downloads",
        organized_dir=None,
        operation="download",
        list_channels=False,
        limit=1,
        channels=["testchannel"],
        filter=None,
        apple=True,
        resume=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_progress_and_redaction():
    protocol = engine.Protocol(io.StringIO())
    protocol.progress(
        dict(type="file_bytes", channel="testchannel", filename="a.pdf", received=2, total=4)
    )
    protocol.progress(dict(type="file_error", channel="testchannel", error="SENSITIVE"))
    assert events(protocol)[0] == dict(
        type="progress",
        version=1,
        channel="testchannel",
        filename="a.pdf",
        done=2,
        total=4,
        bytes=2,
    )
    assert "SENSITIVE" not in protocol.output.getvalue()


@pytest.mark.parametrize(
    "line",
    [b"[]", b"null", b"broken", b'{"command":"unknown"}', b"x" * (engine.MAX_COMMAND_BYTES + 1)],
)
def test_invalid_commands(line):
    protocol = engine.Protocol(io.StringIO())
    protocol.command(line)
    assert events(protocol)[0]["type"] == "error"


async def test_login_response_and_cancel():
    protocol = engine.Protocol(io.StringIO())
    task = asyncio.create_task(protocol.prompt("phone"))
    await asyncio.sleep(0)
    protocol.command(b'{"command":"login_response","field":"phone","value":"fixture"}')
    assert await task == "fixture"
    assert "fixture" not in protocol.output.getvalue()
    protocol.command(b'{"command":"cancel"}')
    assert protocol.cancelled.is_set()


async def test_eof_cancels():
    protocol = engine.Protocol(io.StringIO())
    reader = asyncio.StreamReader()
    reader.feed_eof()
    await protocol.read_commands(reader)
    assert protocol.cancelled.is_set()


async def test_authorize_2fa():
    protocol = engine.Protocol(io.StringIO())
    protocol.prompt = AsyncMock(side_effect=["fixture-phone", "fixture-code", "fixture-password"])
    client = SimpleNamespace(
        is_user_authorized=AsyncMock(return_value=False),
        send_code_request=AsyncMock(return_value=SimpleNamespace(phone_code_hash="fixture")),
        sign_in=AsyncMock(side_effect=[engine.SessionPasswordNeededError(None), None]),
    )
    await engine.authorize(client, protocol)
    assert client.sign_in.await_count == 2
    assert protocol.output.getvalue() == ""


async def test_operation_preserves_selected_channels(tmp_path, monkeypatch):
    monkeypatch.setenv("TG_API_ID", "12345")
    monkeypatch.setenv("TG_API_HASH", "fixture-only")
    client = SimpleNamespace(
        connect=AsyncMock(), disconnect=AsyncMock(), is_user_authorized=AsyncMock(return_value=True)
    )
    process = AsyncMock()
    monkeypatch.setattr(engine.scraper, "process_channel", process)
    protocol = engine.Protocol(io.StringIO())
    await engine.operation(options(tmp_path), protocol, lambda *args: client)
    assert process.call_args.args[1] == "testchannel"
    client.disconnect.assert_awaited_once()


async def test_terminal_event_on_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "operation", AsyncMock(side_effect=RuntimeError("SENSITIVE")))
    protocol = engine.Protocol(io.StringIO())
    assert await engine.serve(options(tmp_path), protocol, asyncio.StreamReader()) == 1
    assert events(protocol)[-1] == dict(type="done", version=1, status="error")
    assert "SENSITIVE" not in protocol.output.getvalue()


async def test_cancel_pending_work(tmp_path, monkeypatch):
    async def work(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(engine, "operation", work)
    protocol = engine.Protocol(io.StringIO())
    reader = asyncio.StreamReader()
    reader.feed_data(b'{"command":"cancel"}\n')
    await asyncio.wait_for(engine.serve(options(tmp_path), protocol, reader), timeout=1)
    assert events(protocol)[-1]["status"] == "cancelled"
