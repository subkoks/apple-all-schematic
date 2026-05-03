#!/usr/bin/env python3
"""
tg_schematic_downloader.py — Bulk download Apple schematics from Telegram channels
"""

import os
import re
import sys
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

from validation import (
    ValidationError,
    sanitize_filename,
    validate_channel_names,
    validate_extensions,
    validate_keywords,
)

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
        "notebookschematic",
        "laptop_bios_schematic",
        "alischematics",
        "hrtechno",
    ],
    "mobile": [
        "SMART_PHONE_SCHEMATICS",
        "mobileshematic",
        "schematicmobile",
    ],
    "apple": [
        "Mac_Shematic_Santale",
    ],
}

APPLE_KEYWORDS = [
    # Product names
    "iphone", "ipad", "macbook", "imac", "mac mini", "mac pro",
    "mac studio", "apple watch", "airpods", "apple tv", "homepod", "ipod",
    "apple",
    # Board numbers (820-xxxx covers all Apple logic boards)
    "820-", "051-",
    # iPhone codenames (longer ones safe as substrings, short ones via regex)
    "n841", "d321", "d421", "d52g",
    # iPad codenames
    "j72", "j217", "j120", "j517", "j522", "j523",
    # Mac codenames — MacBook Pro
    "j137", "j680", "j152", "j314", "j316", "j414", "j416",
    "j493", "j503", "j504", "j505",
    # Mac codenames — MacBook Air
    "j413", "j415", "j513", "j614", "j615",
    # Mac codenames — iMac / Mac Mini / Mac Studio / Mac Pro
    "j185", "j273", "j274", "j375", "j473", "j474",
    "j180", "j375c", "j474s",
    # Apple Watch SoCs
    "t8301", "t8302",
    # MLB / chip identifiers often in filenames
    "mlb", "emc",
]

# Regex patterns for Apple model numbers (A1xxx, A2xxx, A3xxx) and EMC numbers
# Use (?<![a-z0-9]) / (?![a-z0-9]) instead of \b because \b treats _ as word char
APPLE_PATTERNS = re.compile(
    r"(?<![a-z0-9])a[123]\d{3}(?![a-z0-9])"    # A1278, A2141, A3113 etc.
    r"|(?<![a-z0-9])emc\s*\d{4}(?![a-z0-9])"   # EMC 2835, EMC3178 etc.
    r"|(?<![a-z0-9])(?:n61|n71|d10|d20|d22|d16|d63|d73|d83|d93)(?![a-z0-9])",  # short iPhone codenames
    re.IGNORECASE,
)

ALLOWED_EXTENSIONS = validate_extensions({
    # Schematics
    ".pdf",
    # Archives (may contain boardview + schematic bundles)
    ".zip", ".rar", ".7z",
    # OpenBoardView / boardview formats
    ".brd", ".bvr", ".bdv", ".bv", ".cad", ".fz", ".asc",
    ".tvw", ".pcb", ".ddb", ".cst", ".f2b", ".gr",
    # BIOS / firmware
    ".bin", ".rom",
})

# Validate the hardcoded channel list at import time so typos (e.g. a stray
# path separator or empty string) fail loudly rather than poisoning a run.
CHANNELS = {
    category: validate_channel_names(names)
    for category, names in CHANNELS.items()
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
    if any(kw in text for kw in APPLE_KEYWORDS):
        return True
    return bool(APPLE_PATTERNS.search(text))


def get_filename(message) -> str | None:
    if not isinstance(message.media, MessageMediaDocument):
        return None
    doc = message.media.document
    raw_name: str | None = None
    for attr in doc.attributes:
        if hasattr(attr, "file_name") and attr.file_name:
            raw_name = attr.file_name
            break
    if raw_name is None:
        # Fallback: use doc id + mime type guess. Sanitise the mime subtype
        # since it also comes from the remote server.
        mime_subtype = (doc.mime_type or "bin").split("/")[-1]
        mime_subtype = re.sub(r"[^A-Za-z0-9]", "", mime_subtype) or "bin"
        raw_name = f"file_{doc.id}.{mime_subtype}"
    return sanitize_filename(raw_name)


def has_allowed_ext(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ── Core ───────────────────────────────────────────────────────────────────────

APPLE_ONLY_CHANNELS = set(CHANNELS["apple"])


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

        # Apple-only channels: download everything, no keyword filter needed
        if apple_only and channel not in APPLE_ONLY_CHANNELS:
            if not is_apple(filename, caption):
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
        print("\nApple-specific channels:")
        for c in CHANNELS["apple"]:
            print(f"  @{c}")
        print("\nApple keywords:")
        print("  " + ", ".join(APPLE_KEYWORDS))
        print("\nAllowed extensions:")
        print("  " + ", ".join(sorted(ALLOWED_EXTENSIONS)))
        return

    state = load_state() if args.resume else {"downloaded": {}}

    channels = []
    all_channels = CHANNELS["laptop"] + CHANNELS["mobile"] + CHANNELS["apple"]
    if args.apple:
        channels = all_channels
    elif args.channels:
        try:
            channels = validate_channel_names(args.channels)
        except ValidationError as e:
            print(f"Invalid --channels value: {e}")
            sys.exit(2)
    else:
        channels = all_channels

    if args.filter:
        try:
            keyword_filter = validate_keywords(args.filter)
        except ValidationError as e:
            print(f"Invalid --filter value: {e}")
            sys.exit(2)
    else:
        keyword_filter = None
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
