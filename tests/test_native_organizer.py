"""Native organization acceptance uses only temporary fixture files."""

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import native_engine
import native_organizer as native


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    download = tmp_path / "downloads"
    channel = download / "fixture"
    channel.mkdir(parents=True)
    source = channel / "iphone.pdf"
    source.write_bytes(b"fixture-document")
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"downloaded": {"fixture:1": str(source)}}))
    monkeypatch.setattr(native.scraper, "DOWNLOAD_DIR", download)
    monkeypatch.setattr(native.scraper, "STATE_FILE", state)
    args = SimpleNamespace(operation="scan", organized_dir=tmp_path / "organized", plan_id=None)
    return tmp_path, source, state, args, native_engine.Protocol(io.StringIO())


async def preview(fixture):
    root, source, state, args, protocol = fixture
    await native.perform(args, root, protocol)
    plan = json.loads((root / native.PLAN_FILE).read_text())
    args.plan_id = plan["id"]
    return plan


async def test_scan_execute_undo_preserves_new_state(fixture):
    root, source, state, args, protocol = fixture
    plan = await preview(fixture)
    assert source.exists()
    dest = Path(plan["moves"][0]["dest"])
    args.operation = "organize"
    await native.perform(args, root, protocol)
    assert dest.read_bytes() == b"fixture-document"
    assert not source.exists()
    updated = json.loads(state.read_text())
    assert updated["downloaded"]["fixture:1"] == str(dest)
    updated["downloaded"]["new:2"] = "new-download.pdf"
    state.write_text(json.dumps(updated))
    args.operation = "undo"
    await native.perform(args, root, protocol)
    assert source.exists() and not dest.exists()
    assert json.loads(state.read_text())["downloaded"] == {
        "fixture:1": str(source),
        "new:2": "new-download.pdf",
    }


async def test_existing_destination_is_preserved(fixture):
    root, source, state, args, protocol = fixture
    existing = args.organized_dir / "Apple/Phones/iPhone/iphone.pdf"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing")
    plan = await preview(fixture)
    assert plan["moves"][0]["dest"] != str(existing)
    args.operation = "organize"
    await native.perform(args, root, protocol)
    assert existing.read_text() == "existing"


@pytest.mark.parametrize("change", ["source", "destination", "plan", "symlink"])
async def test_reject_stale_or_unsafe_preview(fixture, change):
    root, source, state, args, protocol = fixture
    plan = await preview(fixture)
    dest = Path(plan["moves"][0]["dest"])
    if change == "source":
        source.write_text("changed")
    elif change == "destination":
        dest.parent.mkdir(parents=True)
        dest.write_text("do not overwrite")
    elif change == "plan":
        args.plan_id = "stale"
    else:
        source.unlink()
        source.symlink_to(state)
    args.operation = "organize"
    with pytest.raises(ValueError):
        await native.perform(args, root, protocol)
    assert source.exists()


async def test_undo_conflict_preserves_both_files(fixture):
    root, source, state, args, protocol = fixture
    plan = await preview(fixture)
    args.operation = "organize"
    await native.perform(args, root, protocol)
    source.write_text("new file")
    args.operation = "undo"
    with pytest.raises(ValueError):
        await native.perform(args, root, protocol)
    assert source.read_text() == "new file"
    assert Path(plan["moves"][0]["dest"]).exists()


async def test_cancel_copy_keeps_original(tmp_path):
    import asyncio

    src, dest = tmp_path / "src", tmp_path / "dest"
    src.write_bytes(b"a" * (native.COPY_CHUNK_BYTES * 2))
    task = asyncio.create_task(native.move_exclusive(src, dest))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert src.exists() and not dest.exists()
