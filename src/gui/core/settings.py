"""User preferences, persisted as JSON in the platform config directory.

Holds everything the user can change from the UI that is not a secret: theme, download /
organized locations, channel-list overrides, and a few behaviour defaults. Credentials are
deliberately *not* stored here — they live in ``.env`` (see :mod:`gui.core.config`).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "BoardVault"
APP_TAGLINE = "Apple schematic & boardview downloader"
LEGACY_APP_NAME = "Apple Schematic Downloader"

VALID_THEMES = ("system", "dark", "light")


def settings_file() -> Path:
    """Resolved lazily: QStandardPaths needs QApplication.applicationName set first."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    root = Path(base) if base else Path.home() / ".config" / APP_NAME
    return root / "settings.json"


@dataclass
class Settings:
    theme: str = "system"
    download_dir: str | None = None
    organized_dir: str | None = None
    channels: dict[str, list[str]] = field(default_factory=dict)
    default_apple_only: bool = True
    default_limit: int = 0
    default_resume: bool = True
    reveal_on_complete: bool = False

    # ── persistence ─────────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> Settings:
        path = settings_file()
        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                raw = {}
        else:
            raw = {}
        known = set(cls.__dataclass_fields__)
        data = {k: v for k, v in raw.items() if k in known}
        inst = cls(**data)
        if inst.theme not in VALID_THEMES:
            inst.theme = "system"
        return inst

    def save(self) -> None:
        path = settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    # ── channel override helpers ────────────────────────────────────────────────

    def has_channel_override(self) -> bool:
        return bool(self.channels)

    def set_channels(self, channels: dict[str, list[str]]) -> None:
        self.channels = {k: list(v) for k, v in channels.items() if v}

    def add_channel(self, category: str, name: str) -> None:
        self.channels.setdefault(category, [])
        if name not in self.channels[category]:
            self.channels[category].append(name)

    def remove_channel(self, category: str, name: str) -> None:
        if category in self.channels and name in self.channels[category]:
            self.channels[category].remove(name)
            if not self.channels[category]:
                del self.channels[category]
