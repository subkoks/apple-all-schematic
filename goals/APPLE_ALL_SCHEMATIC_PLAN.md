# apple-all-schematic — Project Plan & Instructions

## Goal

Bulk-download **all available Apple product schematics and boardview files** (iPhone, iPad, MacBook, iMac, Apple Watch, AirPods, etc.) from free Telegram channels. Clean originals, no watermarks.

---

## Project Structure

```
apple-all-schematic/
├── src/
│   └── tg_schematic_downloader.py   ← main script
├── args/
│   └── config.json                  ← channel list, paths
├── data/
│   ├── downloads/                   ← all downloaded files (organized by channel)
│   └── state.json                   ← resume state (auto-generated)
├── tools/                           ← helper scripts (future)
├── context/                         ← notes, references
├── goals/                           ← workflow docs
├── .tmp/                            ← scratch
├── .env.example                     ← credential template
└── README.md
```

---

## Setup

### 1. Get Telegram API credentials (free, 2 min)

1. Go to **https://my.telegram.org**
2. Log in with your phone number
3. Click **"API development tools"** → **"Create new application"**
4. Fill in any name/platform → Submit
5. Copy `api_id` (number) and `api_hash` (string)

```bash
export TG_API_ID=12345678
export TG_API_HASH=abcdef1234567890abcdef1234567890
```

Or create a `.env` file:
```
TG_API_ID=12345678
TG_API_HASH=abcdef1234567890abcdef1234567890
```

### 2. Install dependencies

```bash
pip install telethon tqdm
```

### 3. Place the script

```bash
cp tg_schematic_downloader.py ~/Projects/apple-all-schematic/src/
```

---

## Usage

```bash
cd ~/Projects/apple-all-schematic/src

# All Apple products (recommended — uses 50+ keyword filter)
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

**First run:** Telegram will ask for your phone number + verification code. After that, a session file (`tg_scraper_session.session`) is saved and future runs are fully automatic.

---

## Channels Being Scraped

### Laptop / Desktop (MacBook, iMac, Mac Mini)
| Channel | Description |
|---|---|
| `@schematicslaptop` | Largest archive — 10,000+ posts, PDF + boardview files |
| `@biosarchive` | Same admin, BIOS + schematics, Apple Mac Mini confirmed |
| `@BIOSARCHIVE_PHOTOS` | Companion channel, occasional file attachments |
| `@freeschematicdiagram` | Mixed laptops + phones |

### Phone / Mobile (iPhone, iPad, Apple Watch)
| Channel | Description |
|---|---|
| `@SMART_PHONE_SCHEMATICS` | Dedicated smartphone schematics, iPhone confirmed |
| `@mobileshematic` | Mobile schematics archive |
| `@schematicmobile` | Mixed mobile schematic files |

---

## What Gets Downloaded

### File types
`.pdf` `.zip` `.rar` `.7z` `.brd` `.bvr` `.bdv` `.cad` `.fz` `.asc` `.tvw` `.pcb`

### Apple keyword filter (`--apple` flag)
Matches filenames **and** message captions against:

- **Product names:** `iphone`, `ipad`, `macbook`, `imac`, `mac mini`, `mac pro`, `mac studio`, `apple watch`, `airpods`, `apple tv`, `homepod`, `ipod`
- **Board number prefixes:** `820-0`, `051-` (Apple's internal doc numbering)
- **iPhone codenames:** `n61` (6), `n71` (6S), `d10` (7), `d20` (8), `d22` (X), `n841` (XR), `d321` (XS), `d421` (11), `d52g` (12), `d16` (13), `d63` (14), `d73` (15), `d83` (16)
- **iPad codenames:** `j72`, `j217`, `j120`
- **Mac codenames:** `j137`, `j680`, `j152`, `j314`, `j316`
- **Apple Watch SoCs:** `s4`–`s9`, `t8301`, `t8302`

---

## Output Structure

Files are organized by channel:

```
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

---

## Resume & State

The script saves progress to `data/state.json`. If interrupted:

```bash
# Just re-run with --resume — skips already downloaded files
python tg_schematic_downloader.py --apple --resume
```

State file format:
```json
{
  "downloaded": {
    "schematicslaptop:12345": "/path/to/file.rar",
    "SMART_PHONE_SCHEMATICS:67890": "/path/to/file.pdf"
  }
}
```

---

## Expected Results

| Channel | Est. Total Messages | Est. Apple Files |
|---|---|---|
| `@schematicslaptop` | ~12,000 | ~200–400 |
| `@biosarchive` | ~8,000 | ~100–200 |
| `@SMART_PHONE_SCHEMATICS` | ~5,000 | ~500–1000 |
| `@mobileshematic` | ~3,000 | ~200–500 |

Full run without `--limit` may take **1–4 hours** depending on connection. All files are raw originals with **no watermarks**.

---

## Supplementary Sources (manual / alternative)

If channels don't have what you need:

| Source | Coverage | Notes |
|---|---|---|
| `badcaps.net` forum | MacBook 2008–2015 | Free account needed, direct RAR attachments |
| `apple-schematic.se` | MacBook Air/Pro 2008–2015 | No auth, `wget -r` works |
| `oldergeeks.com` | Selective newer models | No auth, `download.php?id=XXXX` |
| `KiKiHUN1/Mega-Schematics-Downloader` | Mixed collection | Grep `mainwindow.cs` for Mega link → `megacmd` |
| `XinZhiZao` (xinzhizao.vip) | **Everything** incl. M3/latest | Paid ~$3/month, 1hr free trial |

---

## .env.example

```
TG_API_ID=your_api_id_here
TG_API_HASH=your_api_hash_here
```

---

## Quick Start (TL;DR)

```bash
# 1. Get API keys at https://my.telegram.org
export TG_API_ID=12345678
export TG_API_HASH=abcdef...

# 2. Install
pip install telethon tqdm

# 3. Run
cd ~/Projects/apple-all-schematic/src
python tg_schematic_downloader.py --apple --resume
```
