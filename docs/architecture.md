# Architecture — BoardVault (apple-all-schematic)

## Overview

Async Python engine that scrapes Apple device schematics from Telegram channels, with file
organization and categorization, exposed through two front-ends: a **CLI** and the **BoardVault**
desktop app (PySide6). Both share the same engine, `state.json`, and Telegram session.

## Desktop app (`src/gui/`)

The GUI reuses the CLI modules in-process — no IPC, no sidecar. `qasync` provides a single event
loop shared by Qt and Telethon's asyncio.

```
src/gui/
├── app.py            ← entry: QApplication + qasync loop; bootstraps paths + theme
├── core/
│   ├── settings.py   ← user prefs (theme, folders, channel overrides) as JSON
│   ├── paths.py      ← writable data-root resolution; overrides CLI path globals at startup
│   ├── config.py     ← merges args/config.json with the user's channel override
│   ├── auth.py       ← non-interactive Telegram login (phone/code/2FA via the UI)
│   ├── backend.py    ← DownloadController: cancellable task loop → Qt signals
│   └── organizer.py  ← async bridge to organize_downloads
└── ui/               ← main_window, download/organize views, dialogs, theme, icons
```

Key idea: instead of editing the CLI modules, `paths.apply()` reassigns their path globals
(`DOWNLOAD_DIR`, `STATE_FILE`, `SESSION_FILE`, …) once at startup, so a frozen `.app` writes to
user-writable locations while the CLI stays untouched. Packaging: PyInstaller spec → `.app`,
dmgbuild → unsigned `.dmg`.

## Module Map (engine)

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
