"""Tests for state management: load_state, save_state."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tg_schematic_downloader as scraper


@pytest.fixture
def tmp_state_file(tmp_path: Path):
    """Temporarily redirect STATE_FILE to a tmp directory."""
    state_file = tmp_path / "state.json"
    with patch.object(scraper, "STATE_FILE", state_file):
        yield state_file


class TestLoadState:
    def test_returns_empty_when_no_file(self, tmp_state_file: Path) -> None:
        assert not tmp_state_file.exists()
        result = scraper.load_state()
        assert result == {"downloaded": {}}

    def test_loads_existing_state(self, tmp_state_file: Path) -> None:
        data = {"downloaded": {"ch:123": "/path/to/file.pdf"}}
        tmp_state_file.write_text(json.dumps(data))
        result = scraper.load_state()
        assert result == data

    def test_preserves_all_entries(self, tmp_state_file: Path) -> None:
        entries = {f"ch:{i}": f"/path/{i}.pdf" for i in range(100)}
        data = {"downloaded": entries}
        tmp_state_file.write_text(json.dumps(data))
        result = scraper.load_state()
        assert len(result["downloaded"]) == 100


class TestSaveState:
    def test_creates_file(self, tmp_state_file: Path) -> None:
        state = {"downloaded": {"test:1": "/file.pdf"}}
        asyncio.run(scraper.save_state(state))
        assert tmp_state_file.exists()
        loaded = json.loads(tmp_state_file.read_text())
        assert loaded == state

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "nested" / "state.json"
        with patch.object(scraper, "STATE_FILE", nested):
            asyncio.run(scraper.save_state({"downloaded": {}}))
        assert nested.exists()

    def test_overwrites_existing(self, tmp_state_file: Path) -> None:
        tmp_state_file.write_text('{"downloaded": {"old": "data"}}')
        new_state = {"downloaded": {"new": "data"}}
        asyncio.run(scraper.save_state(new_state))
        loaded = json.loads(tmp_state_file.read_text())
        assert loaded == new_state


class TestStateRoundTrip:
    def test_save_then_load(self, tmp_state_file: Path) -> None:
        original = {
            "downloaded": {
                "schematicslaptop:12345": "/data/downloads/schematicslaptop/MacBook.pdf",
                "biosarchive:67890": "/data/downloads/biosarchive/iMac_820-02.rar",
            }
        }
        asyncio.run(scraper.save_state(original))
        loaded = scraper.load_state()
        assert loaded == original
