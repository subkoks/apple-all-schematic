"""Writable data-root resolution and runtime path overrides.

In development the app uses the repo's ``data/`` dir (parity with the CLI). When frozen
into a ``.app`` (read-only bundle) it must write elsewhere, so state/session/organized go
to ``~/Library/Application Support/<app>`` and downloads default to ``~/Downloads/Apple
Schematics``. Rather than edit the CLI modules, :func:`apply` reassigns their path globals
once at startup — ``process_channel`` reads ``DOWNLOAD_DIR`` at call time and the organizer
functions take explicit dirs, so this is sufficient and keeps the CLI untouched.
"""

from __future__ import annotations

import contextlib
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths

import organize_downloads as organizer
import tg_schematic_downloader as scraper

from .settings import LEGACY_APP_NAME, Settings


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def data_root() -> Path:
    """Writable root for state/session/organized."""
    if is_frozen():
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if base:
            return Path(base)
    return scraper.BASE_DIR / "data"


def default_download_dir() -> Path:
    if is_frozen():
        dl = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if dl:
            return Path(dl) / "BoardVault"
    return data_root() / "downloads"


def default_organized_dir() -> Path:
    return data_root() / "organized"


def migrate_legacy() -> None:
    """One-time copy of data from the pre-rebrand dir (Apple Schematic Downloader).

    Renaming the app moved the QStandardPaths data dir; without this the user would lose
    their Telegram session (forcing re-login) and settings. No-op once migrated or when no
    legacy dir exists.
    """
    new_root = data_root()
    if (new_root / "settings.json").exists():
        return
    legacy_root = new_root.parent / LEGACY_APP_NAME
    if not legacy_root.is_dir() or legacy_root == new_root:
        return
    new_root.mkdir(parents=True, exist_ok=True)
    for item in legacy_root.iterdir():
        dest = new_root / item.name
        if dest.exists() or not item.is_file():
            continue
        with contextlib.suppress(OSError):
            shutil.copy2(item, dest)


def apply(settings: Settings) -> None:
    """Reassign scraper/organizer path globals based on env + settings. Run once at startup."""
    migrate_legacy()
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)

    download_dir = Path(settings.download_dir) if settings.download_dir else default_download_dir()
    organized_dir = (
        Path(settings.organized_dir) if settings.organized_dir else default_organized_dir()
    )
    state_file = root / "state.json"

    scraper.STATE_FILE = state_file
    scraper.SESSION_FILE = root / "tg_scraper_session"
    organizer.STATE_FILE = state_file
    organizer.STATE_BACKUP = root / "state.json.bak"
    organizer.MANIFEST_FILE = root / "organize_manifest.json"
    organizer.ORGANIZED_DIR = organized_dir

    set_download_dir(download_dir)


def set_download_dir(path: Path | str) -> Path:
    """Point both modules at a new downloads folder (created if missing). Returns the path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    scraper.DOWNLOAD_DIR = p
    organizer.DOWNLOAD_DIR = p
    return p


def set_organized_dir(path: Path | str) -> Path:
    p = Path(path)
    organizer.ORGANIZED_DIR = p
    return p


# ── Live accessors (read the current module globals) ────────────────────────────


def download_dir() -> Path:
    return scraper.DOWNLOAD_DIR


def organized_dir() -> Path:
    return organizer.ORGANIZED_DIR


def state_file() -> Path:
    return scraper.STATE_FILE


def session_file() -> Path:
    return scraper.SESSION_FILE
