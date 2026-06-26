"""Async bridge to ``organize_downloads`` for the GUI.

Wraps the existing, env-free organizer functions and runs their blocking filesystem
work in a thread so the Qt/asyncio loop stays responsive. Returns structured data
(no stdout scraping).
"""

from __future__ import annotations

import asyncio
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import organize_downloads as organizer


@dataclass
class OrganizePlan:
    moves: list[dict]
    category_counts: dict[str, int]
    confidence_counts: dict[str, int]

    @property
    def total(self) -> int:
        return len(self.moves)


def _aggregate(moves: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    cat: Counter[str] = Counter()
    conf: Counter[str] = Counter()
    for m in moves:
        cat[m["category"]] += 1
        conf[m["confidence"]] += 1
    return dict(cat.most_common()), dict(conf.most_common())


def _build_plan_sync() -> OrganizePlan:
    if not organizer.REFERENCE_FILE.exists():
        raise FileNotFoundError(f"Reference file not found: {organizer.REFERENCE_FILE}")
    board_map = organizer.build_board_lookup(organizer.REFERENCE_FILE)
    model_map = organizer.build_model_lookup(organizer.REFERENCE_FILE)
    files = organizer.scan_files(organizer.DOWNLOAD_DIR)
    moves = organizer.plan_moves(files, board_map, model_map, organizer.ORGANIZED_DIR)
    cat, conf = _aggregate(moves)
    return OrganizePlan(moves=moves, category_counts=cat, confidence_counts=conf)


async def build_plan() -> OrganizePlan:
    """Scan + classify downloads, returning the planned moves (no filesystem changes)."""
    return await asyncio.to_thread(_build_plan_sync)


def _execute_sync(moves: list[dict]) -> dict:
    if organizer.STATE_FILE.exists():
        shutil.copy2(str(organizer.STATE_FILE), str(organizer.STATE_BACKUP))
    organizer.save_manifest(organizer.MANIFEST_FILE, moves)
    moved = organizer.execute_moves(moves, verbose=False)
    updated = organizer.update_state(organizer.STATE_FILE, moves)
    return {"moved": moved, "state_updated": updated, "manifest": str(organizer.MANIFEST_FILE)}


async def execute(moves: list[dict]) -> dict:
    """Back up state, write the undo manifest, move files, and update state.json."""
    return await asyncio.to_thread(_execute_sync, moves)


def _undo_sync() -> dict:
    if not organizer.MANIFEST_FILE.exists():
        raise FileNotFoundError("No organize manifest found — nothing to undo.")
    manifest = json.loads(organizer.MANIFEST_FILE.read_text())
    organizer.undo_moves(organizer.MANIFEST_FILE, organizer.STATE_FILE, organizer.STATE_BACKUP)
    return {"restored": manifest.get("move_count", 0)}


async def undo() -> dict:
    """Reverse the last organization using the manifest."""
    return await asyncio.to_thread(_undo_sync)


def organized_root() -> Path:
    return organizer.ORGANIZED_DIR


def manifest_exists() -> bool:
    return organizer.MANIFEST_FILE.exists()
