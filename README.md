# apple-all-schematic

Bulk download Apple device schematics and boardview files from free Telegram channels. Clean originals, no watermarks.

## Overview

Download comprehensive Apple product schematics and boardviews (iPhone, iPad, MacBook, iMac, Mac Mini, Mac Pro, Mac Studio, Apple Watch, AirPods, Apple TV, HomePod) from curated Telegram channels using the Telethon library.

## Project Structure

```text
apple-all-schematic/
├── README.md              # This file
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── goals/                # Workflow definitions (markdown)
│   └── APPLE_ALL_SCHEMATIC_PLAN.md
├── tools/                # Deterministic scripts
├── context/              # Domain knowledge, references
├── args/                 # Config files (yaml/json)
├── data/                 # Databases, generated data
│   ├── downloads/        # Downloaded files (organized by channel)
│   ├── state.json        # Resume state (auto-generated)
│   └── tg_scraper_session.session  # Telegram session (auto-generated)
├── .tmp/                 # Scratch work (disposable)
└── src/                  # Application source code
    └── tg_schematic_downloader.py
```

## Quick Start

### 1. Get Telegram API credentials (free, 2 min)

1. Go to **<https://my.telegram.org>**
2. Log in with your phone number
3. Click **"API development tools"** → **"Create new application"**
4. Fill in any name/platform → Submit
5. Copy `api_id` (number) and `api_hash` (string)

### 2. Configure environment

```bash
# Copy template and edit with your credentials
cp .env.example .env

# Edit .env and add your credentials:
# TG_API_ID=12345678
# TG_API_HASH=abcdef1234567890abcdef1234567890
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the downloader

```bash
cd src

# Download all Apple products (recommended)
python tg_schematic_downloader.py --apple

# Resume after interruption (always use --resume on re-runs)
python tg_schematic_downloader.py --apple --resume

# Test run — only scan last 2000 messages per channel
python tg_schematic_downloader.py --apple --limit 2000

# Specific product only
python tg_schematic_downloader.py --filter iphone "820-02"

# See all available channels and Apple keywords
python tg_schematic_downloader.py --list-channels
```

**First run:** Telegram will ask for your phone number + verification code. After that, a session file is saved and future runs are fully automatic.

## Usage Examples

```bash
# All Apple products (iPhone, iPad, MacBook, Watch, AirPods, iMac...)
python tg_schematic_downloader.py --apple

# Apple only, resume after interruption
python tg_schematic_downloader.py --apple --resume

# Only iPhone 14/15 era (board numbers)
python tg_schematic_downloader.py --filter "820-02" iphone

# Only specific channels
python tg_schematic_downloader.py --channels SMART_PHONE_SCHEMATICS schematicslaptop --apple

# Scan only last 5000 messages per channel (faster test run)
python tg_schematic_downloader.py --apple --limit 5000
```

## Channels Being Scraped

### Laptop / Desktop (MacBook, iMac, Mac Mini)

- `@schematicslaptop` - Largest archive — 10,000+ posts, PDF + boardview files
- `@biosarchive` - Same admin, BIOS + schematics, Apple Mac Mini confirmed
- `@BIOSARCHIVE_PHOTOS` - Companion channel, occasional file attachments
- `@freeschematicdiagram` - Mixed laptops + phones

### Phone / Mobile (iPhone, iPad, Apple Watch)

- `@SMART_PHONE_SCHEMATICS` - Dedicated smartphone schematics, iPhone confirmed
- `@mobileshematic` - Mobile schematics archive
- `@schematicmobile` - Mixed mobile schematic files

## What Gets Downloaded

### File types

`.pdf` `.zip` `.rar` `.7z` `.brd` `.bvr` `.bdv` `.cad` `.fz` `.asc` `.tvw` `.pcb`

### Apple keyword filter (`--apple` flag)

Matches filenames **and** message captions against:

- **Product names:** `iphone`, `ipad`, `macbook`, `imac`, `mac mini`, `mac pro`, `mac studio`, `apple watch`, `airpods`, `apple tv`, `homepod`, `ipod`
- **Board number prefixes:** `820-0`, `051-` (Apple's internal doc numbering)
- **iPhone codenames:** `n61`, `n71`, `d10`, `d20`, `d22`, `n841`, `d321`, `d421`, `d52g`, `d16`, `d63`, `d73`, `d83`
- **iPad codenames:** `j72`, `j217`, `j120`
- **Mac codenames:** `j137`, `j680`, `j152`, `j314`, `j316`
- **Apple Watch SoCs:** `s4`–`s9`, `t8301`, `t8302`

## Output Structure

Files are organized by channel:

```text
data/downloads/
├── schematicslaptop/
│   ├── Apple_MacBook_Pro_820-02757.rar
│   ├── Apple_MacBook_Air_M1_820-02016.pdf
│   └── ...
├── SMART_PHONE_SCHEMATICS/
│   ├── iPhone_15_Pro_D73_Schematic.pdf
│   ├── iPhone_14_820-02778.rar
│   └── ...
└── biosarchive/
    └── ...
```

## Resume & State

The script saves progress to `data/state.json`. If interrupted:

```bash
# Just re-run with --resume — skips already downloaded files
python tg_schematic_downloader.py --apple --resume
```

## Expected Results

| Channel                   | Est. Total Messages | Est. Apple Files |
| ------------------------- | ------------------- | ---------------- |
| `@schematicslaptop`       | ~12,000             | ~200–400         |
| `@biosarchive`            | ~8,000              | ~100–200         |
| `@SMART_PHONE_SCHEMATICS` | ~5,000              | ~500–1000        |
| `@mobileshematic`         | ~3,000              | ~200–500         |

Full run without `--limit` may take **1–4 hours** depending on connection. All files are raw originals with **no watermarks**.

## Documentation

For comprehensive project planning, instructions, and supplementary sources, see:

- [goals/APPLE_ALL_SCHEMATIC_PLAN.md](goals/APPLE_ALL_SCHEMATIC_PLAN.md)

## Requirements

- Python 3.10+
- Telegram account
- Free Telegram API credentials from <https://my.telegram.org>

## License

Educational use only. Respect intellectual property rights and use responsibly.
