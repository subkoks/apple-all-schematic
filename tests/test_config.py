"""Tests for config loading and validation."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tg_schematic_downloader as scraper


class TestConfigLoading:
    def test_defaults_used_when_no_config(self, tmp_path: Path) -> None:
        fake_config = tmp_path / "nonexistent.json"
        with patch.object(scraper, "CONFIG_FILE", fake_config):
            config = scraper.load_config()
        assert config == {}

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        config_data = {
            "channels": {"test": ["channel1"]},
            "apple_keywords": ["iphone"],
            "allowed_extensions": [".pdf"],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        with patch.object(scraper, "CONFIG_FILE", config_file):
            result = scraper.load_config()
        assert result["channels"] == {"test": ["channel1"]}
        assert result["apple_keywords"] == ["iphone"]


class TestConfigIntegrity:
    """Validate the shipped args/config.json matches hardcoded defaults."""

    def test_config_json_exists(self) -> None:
        config_path = Path(__file__).parent.parent / "args" / "config.json"
        assert config_path.exists(), "args/config.json should exist"

    def test_config_json_valid(self) -> None:
        config_path = Path(__file__).parent.parent / "args" / "config.json"
        with open(config_path) as f:
            data = json.load(f)
        assert "channels" in data
        assert "apple_keywords" in data
        assert "allowed_extensions" in data
        assert "download" in data

    def test_config_channels_match_defaults(self) -> None:
        config_path = Path(__file__).parent.parent / "args" / "config.json"
        with open(config_path) as f:
            data = json.load(f)
        # All default channel categories should be present
        assert "laptop" in data["channels"]
        assert "mobile" in data["channels"]
        assert "apple" in data["channels"]
        assert len(data["channels"]["laptop"]) == 8
        assert len(data["channels"]["mobile"]) == 3
        assert len(data["channels"]["apple"]) == 1

    def test_config_extensions_are_dotted(self) -> None:
        config_path = Path(__file__).parent.parent / "args" / "config.json"
        with open(config_path) as f:
            data = json.load(f)
        for ext in data["allowed_extensions"]:
            assert ext.startswith("."), f"Extension '{ext}' should start with '.'"

    def test_download_settings_valid(self) -> None:
        config_path = Path(__file__).parent.parent / "args" / "config.json"
        with open(config_path) as f:
            data = json.load(f)
        dl = data["download"]
        assert dl["max_retries"] >= 1
        assert dl["retry_base_delay_seconds"] > 0
        assert dl["parallel_channels"] >= 1
