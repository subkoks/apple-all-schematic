"""Native-only preview and undo adapter; legacy GUI/organizer remain untouched."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import organize_downloads as organizer
import tg_schematic_downloader as scraper

PLAN_FILE = "native-plan.json"
JOURNAL_FILE = "native-organize-journal.json"
PLAN_BATCH_SIZE = 100
COPY_CHUNK_BYTES = 1024 * 1024


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".native-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def signature(path: Path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev]


def confined(path: Path, root: Path):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or path == root:
        raise ValueError("Unsafe path")


def read_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def scan(download: Path, library: Path):
    board = organizer.build_board_lookup(organizer.REFERENCE_FILE)
    models = organizer.build_model_lookup(organizer.REFERENCE_FILE)
    moves = []
    reserved = set()
    for src in organizer.scan_files(download):
        confined(src, download)
        category, confidence = organizer.classify(src.name, board, models)
        dest = library / category / src.name
        counter = 0
        while dest.exists() or str(dest).casefold() in reserved:
            counter += 1
            dest = library / category / f"{src.stem}_{counter}{src.suffix}"
        confined(dest, library)
        reserved.add(str(dest).casefold())
        moves.append(
            dict(
                src=str(src),
                dest=str(dest),
                category=category,
                confidence=confidence,
                signature=signature(src),
            )
        )
    return moves


async def move_exclusive(src: Path, dest: Path):
    """Never overwrite an existing file; keep original until durable copy exists."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    original = signature(src)
    created = False
    try:
        with src.open("rb") as source, dest.open("xb") as target:
            created = True
            while chunk := source.read(COPY_CHUNK_BYTES):
                target.write(chunk)
                await asyncio.sleep(0)
            target.flush()
            os.fsync(target.fileno())
        if signature(src) != original:
            raise ValueError("Source changed")
        shutil.copystat(src, dest)
        src.unlink()
    except BaseException:
        if created and src.exists():
            dest.unlink(missing_ok=True)
        raise


def update_paths(state_path: Path, mapping: dict):
    if not state_path.exists():
        return
    state = read_json(state_path, {})
    downloaded = state.get("downloaded")
    if not isinstance(downloaded, dict):
        raise ValueError("Invalid state")
    for key, path in downloaded.items():
        downloaded[key] = mapping.get(path, path)
    atomic_json(state_path, state)


async def perform(args, root: Path, protocol):
    download = scraper.DOWNLOAD_DIR
    library = (args.organized_dir or root / "organized").expanduser().resolve()
    if library == download or library.is_relative_to(download) or download.is_relative_to(library):
        raise ValueError("Overlapping roots")
    plan_path, journal_path = root / PLAN_FILE, root / JOURNAL_FILE
    if args.operation == "scan":
        moves = scan(download, library)
        plan = dict(id=uuid.uuid4().hex, download=str(download), library=str(library), moves=moves)
        atomic_json(plan_path, plan)
        for offset in range(0, max(1, len(moves)), PLAN_BATCH_SIZE):
            protocol.emit("plan", planID=plan["id"], moves=moves[offset : offset + PLAN_BATCH_SIZE])
        return

    journal = read_json(journal_path, {"batches": []})
    if args.operation == "organize":
        plan = read_json(plan_path, {})
        if (
            not args.plan_id
            or plan.get("id") != args.plan_id
            or plan.get("download") != str(download)
            or plan.get("library") != str(library)
        ):
            raise ValueError("Preview no longer valid")
        moves = plan["moves"]
        for move in moves:
            src, dest = Path(move["src"]), Path(move["dest"])
            confined(src, download)
            confined(dest, library)
            if signature(src) != move["signature"] or dest.exists():
                raise ValueError("Preview changed; scan again")
        if not moves:
            return
        # Validate state before the first filesystem mutation.
        state = read_json(scraper.STATE_FILE, {"downloaded": {}})
        if not isinstance(state.get("downloaded"), dict):
            raise ValueError("Invalid state")
        batch = dict(download=str(download), library=str(library), moves=[])
        journal["batches"].append(batch)
        atomic_json(journal_path, journal)
        for move in moves:
            src, dest = Path(move["src"]), Path(move["dest"])
            confined(src, download)
            confined(dest, library)
            if signature(src) != move["signature"]:
                raise ValueError("Source changed")
            record = dict(
                src=str(src), dest=str(dest), signature=move["signature"], status="pending"
            )
            batch["moves"].append(record)
            atomic_json(journal_path, journal)
            await move_exclusive(src, dest)
            record["status"] = "moved"
            record["destination_signature"] = signature(dest)
            atomic_json(journal_path, journal)
            update_paths(scraper.STATE_FILE, {str(src): str(dest)})
            protocol.emit("file_done", filename=src.name, path=str(dest))
        plan_path.unlink(missing_ok=True)
        return

    if not journal["batches"]:
        raise ValueError("Nothing to undo")
    batch = journal["batches"][-1]
    if batch["download"] != str(download) or batch["library"] != str(library):
        raise ValueError("Restore original folders before undo")
    for move in reversed(batch["moves"]):
        original, current = Path(move["src"]), Path(move["dest"])
        confined(original, download)
        confined(current, library)
        if move["status"] == "undone":
            continue
        if move["status"] == "pending" and original.exists() and not current.exists():
            move["status"] = "undone"
            atomic_json(journal_path, journal)
            continue
        # Refuse ambiguous partial copies or changed files rather than deleting user data.
        if original.exists() or not current.exists():
            raise ValueError("Undo conflict")
        expected = move.get("destination_signature")
        if expected is not None and signature(current) != expected:
            raise ValueError("Organized file changed")
        if expected is None and signature(current)[:2] != move["signature"][:2]:
            raise ValueError("Incomplete move")
        await move_exclusive(current, original)
        update_paths(scraper.STATE_FILE, {str(current): str(original)})
        move["status"] = "undone"
        atomic_json(journal_path, journal)
        protocol.emit("file_done", filename=original.name, path=str(original))
    journal["batches"].pop()
    atomic_json(journal_path, journal)
