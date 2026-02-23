#!/usr/bin/env python3
"""
tg_schematic_downloader.py — Bulk download Apple schematics from Telegram channels
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Force unbuffered output for real-time logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv()

try:
    from telethon import TelegramClient
    from telethon.tl.types import MessageMediaDocument
    from tqdm import tqdm
except ImportError:
    print("Missing deps: pip install telethon tqdm python-dotenv")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "data" / "downloads"
STATE_FILE = BASE_DIR / "data" / "state.json"
SESSION_FILE = BASE_DIR / "data" / "tg_scraper_session"

CHANNELS = {
    "laptop": [
        "schematicslaptop",
        "biosarchive",
        "BIOSARCHIVE_PHOTOS",
        "freeschematicdiagram",
    ],
    "mobile": [
        "SMART_PHONE_SCHEMATICS",
        "mobileshematic",
        "schematicmobile",
    ],
}

APPLE_KEYWORDS = [
    # Product names
    "iphone", "ipad", "macbook", "imac", "mac mini", "mac pro",
    "mac studio", "apple watch", "airpods", "apple tv", "homepod", "ipod",
    # Board numbers
    "820-0", "051-",
    # iPhone codenames
    "n61", "n71", "d10", "d20", "d22", "n841", "d321", "d421",
    "d52g", "d16", "d63", "d73", "d83",
    # iPad codenames
    "j72", "j217", "j120",
    # Mac codenames
    "j137", "j680", "j152", "j314", "j316",
    # Apple Watch SoCs
    "s4", "s5", "s6", "s7", "s8", "s9", "t8301", "t8302",
]

ALLOWED_EXTENSIONS = {
    ".pdf", ".zip", ".rar", ".7z", ".brd", ".bvr", ".bdv",
    ".cad", ".fz", ".asc", ".tvw", ".pcb",
}

# ── State ──────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"downloaded": {}}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Helpers ────────────────────────────────────────────────────────────────────

def is_apple(filename: str, caption: str) -> bool:
    text = f"{filename} {caption}".lower()
    return any(kw in text for kw in APPLE_KEYWORDS)


def get_filename(message) -> str | None:
    if not isinstance(message.media, MessageMediaDocument):
        return None
    doc = message.media.document
    for attr in doc.attributes:
        if hasattr(attr, "file_name") and attr.file_name:
            return attr.file_name
    # Fallback: use doc id + mime type guess
    ext = doc.mime_type.split("/")[-1] if doc.mime_type else "bin"
    return f"file_{doc.id}.{ext}"


def has_allowed_ext(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ── Core ───────────────────────────────────────────────────────────────────────

async def process_channel(
    client: TelegramClient,
    channel: str,
    state: dict,
    apple_only: bool,
    keyword_filter: list[str] | None,
    limit: int | None,
    resume: bool,
):
    print(f"\n{'─'*60}")
    print(f"Channel: @{channel}")

    out_dir = DOWNLOAD_DIR / channel
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = state["downloaded"]
    count = skipped = errors = 0

    try:
        entity = await client.get_entity(channel)
    except Exception as e:
        print(f"  ✗ Could not resolve @{channel}: {e}")
        return

    kwargs = {"limit": limit} if limit else {}

    async for message in client.iter_messages(entity, **kwargs):
        filename = get_filename(message)
        if not filename:
            continue

        if not has_allowed_ext(filename):
            continue

        caption = message.message or ""
        state_key = f"{channel}:{message.id}"

        if resume and state_key in downloaded:
            skipped += 1
            continue

        if apple_only and not is_apple(filename, caption):
            continue

        if keyword_filter:
            text = f"{filename} {caption}".lower()
            if not any(k.lower() in text for k in keyword_filter):
                continue

        dest = out_dir / filename

        # Handle duplicate filenames
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            dest = out_dir / f"{stem}_{message.id}{suffix}"

        try:
            print(f"  ↓ {filename}")
            await client.download_media(
                message,
                file=str(dest),
            )
            downloaded[state_key] = str(dest)
            count += 1
            save_state(state)
        except Exception as e:
            print(f"  ✗ Failed {filename}: {e}")
            errors += 1

    print(f"  Done — {count} downloaded, {skipped} skipped, {errors} errors")


async def main(args):
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")

    if not api_id or not api_hash:
        print("Set TG_API_ID and TG_API_HASH env vars (or .env file)")
        sys.exit(1)

    if args.list_channels:
        print("\nLaptop/Desktop channels:")
        for c in CHANNELS["laptop"]:
            print(f"  @{c}")
        print("\nMobile channels:")
        for c in CHANNELS["mobile"]:
            print(f"  @{c}")
        print("\nApple keywords:")
        print("  " + ", ".join(APPLE_KEYWORDS))
        return

    state = load_state() if args.resume else {"downloaded": {}}

    channels = []
    if args.apple:
        channels = CHANNELS["laptop"] + CHANNELS["mobile"]
    elif args.channels:
        channels = [c.lstrip("@") for c in args.channels]
    else:
        channels = CHANNELS["laptop"] + CHANNELS["mobile"]

    keyword_filter = args.filter if args.filter else None
    apple_only = args.apple

    async with TelegramClient(str(SESSION_FILE), int(api_id), api_hash) as client:
        for channel in channels:
            await process_channel(
                client=client,
                channel=channel,
                state=state,
                apple_only=apple_only,
                keyword_filter=keyword_filter,
                limit=args.limit,
                resume=args.resume,
            )

    print(f"\n✓ All done. State saved to {STATE_FILE}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Telegram Apple schematic downloader")
    p.add_argument("--apple", action="store_true", help="Download all Apple files (uses keyword filter)")
    p.add_argument("--resume", action="store_true", help="Skip already-downloaded files")
    p.add_argument("--limit", type=int, default=None, metavar="N", help="Max messages to scan per channel")
    p.add_argument("--filter", nargs="+", metavar="KW", help="Only download files matching these keywords")
    p.add_argument("--channels", nargs="+", metavar="CH", help="Specific channels to scrape (overrides default list)")
    p.add_argument("--list-channels", action="store_true", help="Print available channels and keywords, then exit")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
