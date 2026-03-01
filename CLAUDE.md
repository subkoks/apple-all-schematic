# Project Rules — apple-all-schematic

## Project Overview

- **Name:** apple-all-schematic
- **Type:** CLI tool — Telegram scraper for Apple device schematics
- **Stack:** Python 3.13 + Telethon (async Telegram client) + tqdm
- **Status:** Active — downloading complete, now upgrading and optimizing
- **Repo:** github.com/subkoks/apple-all-schematic

## Architecture

- **Pattern:** Single async script with CLI argument parsing
- **Entry point:** `src/tg_schematic_downloader.py` (245 lines)
- **State:** JSON file at `data/state.json` — tracks downloaded files by `channel:message_id`
- **Auth:** Telethon session file at `data/tg_scraper_session.session`
- **Downloads:** Organized by channel in `data/downloads/<channel_name>/`

## Key Files to Read First

- `src/tg_schematic_downloader.py` — entire application logic
- `goals/APPLE_ALL_SCHEMATIC_PLAN.md` — project plan, channel list, keyword reference
- `.env.example` — required Telegram API credentials
- `data/state.json` — resume state (275KB, 1800+ entries)
- `monitor.sh` — real-time download monitoring script

## Project Conventions

- All paths use `pathlib.Path`, rooted from `BASE_DIR = Path(__file__).parent.parent`
- State is saved after every successful download for crash resilience
- Channel names are used as-is for directory names (case-sensitive)
- Duplicate filenames get `_{message_id}` suffix appended
- Apple keyword matching is case-insensitive against both filename and caption

## Hardcoded Configuration (in main script)

- 12 Telegram channels (8 laptop, 3 mobile, 1 apple-specific)
- 50+ Apple keywords for `--apple` filter (820- prefix matches all Apple boards)
- 18 allowed file extensions: schematics (.pdf), archives (.zip, .rar, .7z), boardview (.brd, .bvr, .bdv, .bv, .cad, .fz, .asc, .tvw, .pcb, .ddb, .cst, .f2b, .gr), firmware (.bin, .rom)

## Environment Variables

- `TG_API_ID` — Telegram API ID (integer, from my.telegram.org)
- `TG_API_HASH` — Telegram API hash (string, from my.telegram.org)
- Source: `.env` file (gitignored) or shell exports

## Commands

- **Install:** `pip install -r requirements.txt`
- **Full run:** `python src/tg_schematic_downloader.py --apple --resume`
- **Test run:** `python src/tg_schematic_downloader.py --apple --limit 2000`
- **Filter:** `python src/tg_schematic_downloader.py --filter iphone "820-02"`
- **List channels:** `python src/tg_schematic_downloader.py --list-channels`
- **Monitor:** `./monitor.sh`

## Project-Specific Rules

- Keep the script portable — single file, minimal dependencies (telethon, tqdm, python-dotenv)
- State file (`state.json`) is critical — read it before any operations that modify download tracking
- Telegram session file must stay in `data/` and stay gitignored
- When adding new channels or keywords, update both the script constants and the plan doc
- `data/downloads/` contains 6.7GB of files — do not read or index these directories
- All async operations use `telethon` patterns — `async for`, `await client.method()`
- When optimizing, preserve resume capability — state must be saved after each download
- For new features, follow existing patterns: argparse flags, print-based logging, pathlib paths

## Planned Improvements

- Extract hardcoded config (channels, keywords, extensions) to `args/config.json`
- Add download progress bars per file (tqdm integration)
- Add deduplication across channels (same file from different channels)
- Add file integrity checks (size validation after download)
- Add retry logic for failed downloads with exponential backoff
- Consider parallel downloads across channels (async tasks)
