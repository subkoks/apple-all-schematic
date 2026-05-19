# Architecture — apple-all-schematic

## Overview

Async Python CLI tool that scrapes Apple device schematics from Telegram channels, with file organization and categorization.

## Module Map

```
src/
├── tg_schematic_downloader.py  ← Main Telegram download logic
└── organize_downloads.py       ← File categorization by brand/product

args/
└── config.json                 ← Channels, keywords, extensions, settings

data/
├── state.json                  ← Download state (channel:message_id tracking)
├── downloads/<channel>/        ← Raw files (empty after organization)
├── organized/<category>/       ← Categorized files (~10GB)
└── tg_scraper_session.session  ← Telethon auth session

context/
└── APPLE_PRODUCT_REFERENCE.md  ← Apple product/board number reference

goals/
└── APPLE_ALL_SCHEMATIC_PLAN.md ← Project plan, channel list, keywords
```

## Data Flow

1. Load config from `args/config.json` (with hardcoded fallbacks)
2. Connect to Telegram via Telethon async client
3. Iterate channels → filter by keywords/extensions → download
4. State saved after each download (crash resilience)
5. Cross-channel dedup by normalized filename
6. Organize: categorize files by brand/product into `data/organized/`

## Key Design Decisions

- State saved after every download for crash resilience
- Parallel channel processing via `asyncio.gather` + semaphore
- Retry with exponential backoff on download failures
- FloodWaitError handling for Telegram rate limiting
- File integrity checks against Telegram metadata
