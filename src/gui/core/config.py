"""Configuration + credential access for the GUI.

Single source of truth for paths (reused from the existing CLI modules) and for
the channel / keyword / download-tuning data in ``args/config.json``. Credentials
are read from the environment (``.env`` is loaded by importing the scraper module)
and can be persisted back to ``.env`` without ever being logged.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import tg_schematic_downloader as scraper

# Reuse the canonical paths defined by the CLI so the GUI and CLI never diverge.
BASE_DIR: Path = scraper.BASE_DIR
DATA_DIR: Path = BASE_DIR / "data"
DOWNLOAD_DIR: Path = scraper.DOWNLOAD_DIR
STATE_FILE: Path = scraper.STATE_FILE
SESSION_FILE: Path = scraper.SESSION_FILE
CONFIG_FILE: Path = BASE_DIR / "args" / "config.json"
ENV_FILE: Path = BASE_DIR / ".env"


@dataclass(frozen=True)
class DownloadTuning:
    max_retries: int = 3
    retry_base_delay_seconds: int = 2
    parallel_channels: int = 3
    state_save_interval: int = 1


@dataclass(frozen=True)
class AppConfig:
    """Channel/keyword/extension config, loaded from ``args/config.json`` with a
    fallback to the constants baked into the scraper module."""

    channels: dict[str, list[str]] = field(default_factory=dict)
    apple_keywords: list[str] = field(default_factory=list)
    allowed_extensions: list[str] = field(default_factory=list)
    download: DownloadTuning = field(default_factory=DownloadTuning)

    @property
    def all_channels(self) -> list[str]:
        return [c for names in self.channels.values() for c in names]


def load_config() -> AppConfig:
    """Read ``args/config.json``; fall back to scraper module constants.

    A user channel override (saved in :class:`gui.core.settings.Settings`) takes
    precedence over both, so add/remove edits made in the UI win.
    """
    channels = {k: list(v) for k, v in scraper.CHANNELS.items()}
    keywords = list(scraper.APPLE_KEYWORDS)
    extensions = sorted(scraper.ALLOWED_EXTENSIONS)
    tuning = DownloadTuning()

    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            raw = {}
        if isinstance(raw.get("channels"), dict):
            channels = {k: list(v) for k, v in raw["channels"].items()}
        if isinstance(raw.get("apple_keywords"), list):
            keywords = list(raw["apple_keywords"])
        if isinstance(raw.get("allowed_extensions"), list):
            extensions = list(raw["allowed_extensions"])
        dl = raw.get("download")
        if isinstance(dl, dict):
            tuning = DownloadTuning(
                max_retries=int(dl.get("max_retries", tuning.max_retries)),
                retry_base_delay_seconds=int(
                    dl.get("retry_base_delay_seconds", tuning.retry_base_delay_seconds)
                ),
                parallel_channels=int(dl.get("parallel_channels", tuning.parallel_channels)),
                state_save_interval=int(dl.get("state_save_interval", tuning.state_save_interval)),
            )

    # User override from settings wins when present.
    from .settings import Settings

    override = Settings.load().channels
    if override:
        channels = {k: list(v) for k, v in override.items() if v}

    return AppConfig(
        channels=channels,
        apple_keywords=keywords,
        allowed_extensions=extensions,
        download=tuning,
    )


@dataclass(frozen=True)
class Credentials:
    api_id: str | None
    api_hash: str | None

    @property
    def is_complete(self) -> bool:
        return bool(self.api_id and self.api_hash)


def get_credentials() -> Credentials:
    """Read Telegram API credentials from the environment (``.env`` already loaded)."""
    return Credentials(
        api_id=os.environ.get("TG_API_ID") or None,
        api_hash=os.environ.get("TG_API_HASH") or None,
    )


def save_credentials(api_id: str, api_hash: str) -> None:
    """Persist credentials to ``.env`` (gitignored) and the live environment.

    Rewrites only the two managed keys, preserving any other lines. Never logs values.
    """
    api_id = api_id.strip()
    api_hash = api_hash.strip()

    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()

    managed = {"TG_API_ID": api_id, "TG_API_HASH": api_hash}
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in managed:
            out.append(f"{key}={managed[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in managed.items():
        if key not in seen:
            out.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(out) + "\n")
    os.environ["TG_API_ID"] = api_id
    os.environ["TG_API_HASH"] = api_hash
