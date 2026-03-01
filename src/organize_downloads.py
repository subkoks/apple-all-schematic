#!/usr/bin/env python3
"""
organize_downloads.py — Categorize downloaded schematic files by brand and product.

Usage:
    python src/organize_downloads.py --dry-run    # Preview moves without executing
    python src/organize_downloads.py --report     # Show classification stats only
    python src/organize_downloads.py              # Execute moves
    python src/organize_downloads.py --undo       # Reverse organization using manifest
"""

import argparse
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = BASE_DIR / "data" / "downloads"
ORGANIZED_DIR = BASE_DIR / "data" / "organized"
STATE_FILE = BASE_DIR / "data" / "state.json"
STATE_BACKUP = BASE_DIR / "data" / "state.json.bak"
MANIFEST_FILE = BASE_DIR / "data" / "organize_manifest.json"
REFERENCE_FILE = BASE_DIR / "context" / "APPLE_PRODUCT_REFERENCE.md"

BOARD_NUMBER_RE = re.compile(r"820[_-](\d{4,5})")
MODEL_NUMBER_RE = re.compile(r"(?<![a-z0-9])a([123]\d{3})(?![a-z0-9])", re.IGNORECASE)

# ── Section-to-Category Mapping ───────────────────────────────────────────────

SECTION_TO_CATEGORY = {
    "macbook air":          "Apple/Computers/MacBook_Air",
    "macbook pro 13":       "Apple/Computers/MacBook_Pro",
    "macbook pro 14":       "Apple/Computers/MacBook_Pro",
    "macbook pro 15":       "Apple/Computers/MacBook_Pro",
    "macbook pro 16":       "Apple/Computers/MacBook_Pro",
    "macbook pro 17":       "Apple/Computers/MacBook_Pro",
    "macbook 12":           "Apple/Computers/MacBook",
    "macbook (white":       "Apple/Computers/MacBook",
    "imac":                 "Apple/Computers/iMac",
    "mac mini":             "Apple/Computers/Mac_Mini",
    "mac studio":           "Apple/Computers/Mac_Studio",
    "mac pro":              "Apple/Computers/Mac_Pro",
    "legacy":               "Apple/Computers/Other_Mac",
    "powerbook":            "Apple/Computers/Other_Mac",
    "ibook":                "Apple/Computers/Other_Mac",
    "emac":                 "Apple/Computers/Other_Mac",
    "xserve":               "Apple/Computers/Other_Mac",
    "iphone":               "Apple/Phones/iPhone",
    "ipad":                 "Apple/Tablets/iPad",
    "apple watch":          "Apple/Wearables/Apple_Watch",
    "airpods":              "Apple/Wearables/AirPods",
    "apple tv":             "Apple/Other_Apple",
    "homepod":              "Apple/Other_Apple",
    "ipod":                 "Apple/Other_Apple",
    "accessories":          "Apple/Other_Apple",
}

# ── Apple Product Keywords ────────────────────────────────────────────────────

APPLE_PRODUCT_KEYWORDS: dict[str, list[str]] = {
    "Apple/Computers/MacBook_Pro": [
        "macbook pro", "macbook_pro", "mackbook pro", "macbookpro", "mbp",
    ],
    "Apple/Computers/MacBook_Air": [
        "macbook air", "macbook_air", "mackbook air", "macbookair", "mba",
    ],
    "Apple/Computers/MacBook": [
        "macbook 12", "macbook_12", "macbook retina 12",
    ],
    "Apple/Computers/iMac": [
        "imac", "i-mac",
    ],
    "Apple/Computers/Mac_Mini": [
        "mac mini", "mac_mini", "macmini",
    ],
    "Apple/Computers/Mac_Pro": [
        "mac pro", "mac_pro", "macpro",
    ],
    "Apple/Computers/Mac_Studio": [
        "mac studio", "mac_studio", "macstudio",
    ],
    "Apple/Computers/Other_Mac": [
        "powerbook", "ibook", "xserve",
        # "emac" handled via regex to avoid matching "emachines"
    ],
    "Apple/Phones/iPhone": [
        "iphone", "i-phone",
    ],
    "Apple/Tablets/iPad": [
        "ipad", "i-pad",
    ],
    "Apple/Wearables/Apple_Watch": [
        "apple watch", "apple_watch", "applewatch",
    ],
    "Apple/Wearables/AirPods": [
        "airpod",
    ],
    "Apple/Other_Apple": [
        "apple tv", "apple_tv", "appletv", "homepod", "ipod touch", "ipod nano",
        "ipod shuffle", "ipod classic",
    ],
}

# ── Non-Apple Brand Keywords ─────────────────────────────────────────────────

BRAND_KEYWORDS: dict[str, list[str]] = {
    "Dell": [
        "dell", "alienware", "latitude", "inspiron", "xps ", "vostro", "precision",
    ],
    "Lenovo": [
        "lenovo", "thinkpad", "ideapad", "yoga ", "legion", "lcfc",
        "nm-c", "nm-b", "nm-d", "nm-a",  # Lenovo ODM board codes (NM-C121, NM-B601)
        "nm_c", "nm_b", "nm_d", "nm_a",  # Underscore variant
        "ns-c",  # Lenovo NS-Cxxx boards
    ],
    "Asus": [
        "asus", " rog ", "zenbook", "vivobook", "tuf ",
    ],
    "Toshiba": [
        "toshiba", "satellite", "tecra", "portege",
    ],
    "Sony": [
        "sony", "vaio", "vgn-", "svf-", "sve-", "mbx-",
    ],
    "Acer": [
        "acer", "aspire", "predator", "nitro ", "swift ", "emachines",
    ],
    "Samsung": [
        "samsung", "galaxy", "sm-j", "sm-g", "sm-a", "sm-n", "sm-t",
    ],
    "MSI": [
        "megabook",
    ],
    "Other_Brands": [
        "huawei", "xiaomi", "mipad", "vivo ", "oppo", "nokia",
        "motorola", "oneplus", "meizu", "zte ", "realme", "clevo",
        "quanta", "compal", "wistron", "pegatron", "foxconn",
        "gigabyte", "asrock", "fujitsu", "benq", "nec ",
        "la-d", "la-e", "la-f", "la-g", "la-h", "la-j", "la-k",  # Compal/Wistron LA-xxxx
        "da0",  # Quanta DA0xxx boards
        "6050a",  # Inventec/Quanta 6050Axxxxxx boards
        "ga-",  # Gigabyte GA- motherboards
    ],
}

# Short brand keywords that need word-boundary regex
BRAND_REGEX_PATTERNS: dict[str, re.Pattern[str]] = {
    "HP": re.compile(r"(?<![a-z])hp(?![a-z])|hewlett|compaq|pavilion|elitebook|probook|envy|spectre", re.IGNORECASE),
    "MSI": re.compile(r"(?<![a-z])msi(?![a-z])|(?<![a-z])ms-1[67]\d{2}(?![a-z0-9])|(?<![a-z])ms7[0-9]{3}", re.IGNORECASE),
    "LG": re.compile(r"(?<![a-z])lg(?![a-z])", re.IGNORECASE),
    "Other_Brands": re.compile(r"(?<![a-z])ecs(?![a-z])|(?<![a-z])esc(?![a-z])", re.IGNORECASE),
}

# Apple non-820 patterns (flex cables, interface boards, doc numbers)
APPLE_AUX_RE = re.compile(r"(?:821-|051-|920-)\d{4}")  # 821-xxxx flex, 051-xxxx docs, 920-xxxx interface


# ── Lookup Table Builders ─────────────────────────────────────────────────────

def build_board_lookup(reference_path: Path) -> dict[str, str]:
    """Parse APPLE_PRODUCT_REFERENCE.md to build board-number → category mapping."""
    board_map: dict[str, str] = {}
    current_category: str | None = None

    for line in reference_path.read_text().splitlines():
        # Detect section headers like "## 1. Mac — MacBook Air"
        if line.startswith("## ") or line.startswith("### "):
            header_lower = line.lower()
            for key, category in SECTION_TO_CATEGORY.items():
                if key in header_lower:
                    current_category = category
                    break

        # Extract board numbers from table rows
        if current_category and "|" in line and "820-" in line:
            for match in BOARD_NUMBER_RE.finditer(line):
                board = f"820-{match.group(1)}"
                if board not in board_map:
                    board_map[board] = current_category

    return board_map


def build_model_lookup(reference_path: Path) -> dict[str, str]:
    """Parse APPLE_PRODUCT_REFERENCE.md to build A-number → category mapping."""
    model_map: dict[str, str] = {}
    current_category: str | None = None

    for line in reference_path.read_text().splitlines():
        if line.startswith("## ") or line.startswith("### "):
            header_lower = line.lower()
            for key, category in SECTION_TO_CATEGORY.items():
                if key in header_lower:
                    current_category = category
                    break

        # Extract A-numbers from table rows
        if current_category and "|" in line:
            for match in re.finditer(r"A([123]\d{3})", line):
                a_number = f"A{match.group(1)}"
                if a_number not in model_map:
                    model_map[a_number] = current_category

    return model_map


# ── Classification ────────────────────────────────────────────────────────────

def classify(
    filename: str,
    board_map: dict[str, str],
    model_map: dict[str, str],
) -> tuple[str, str]:
    """Classify a file into a category.

    Returns (category_path, confidence) where confidence is one of:
    board_match, model_match, keyword_match, brand_match, fallback.
    """
    name_lower = f" {filename} ".lower()  # pad with spaces for boundary matching

    # Step 1: Board number lookup (highest confidence)
    board_match = BOARD_NUMBER_RE.search(name_lower)
    if board_match:
        board = f"820-{board_match.group(1)}"
        if board in board_map:
            return board_map[board], "board_match"
        # 820- prefix but not in our lookup — still Apple
        return "Apple/Other_Apple", "board_match"

    # Step 1b: Apple auxiliary numbers (821- flex, 051- docs, 920- interface)
    if APPLE_AUX_RE.search(name_lower):
        return "Apple/Other_Apple", "board_match"

    # Step 2: Apple model number lookup
    model_match = MODEL_NUMBER_RE.search(filename)
    if model_match:
        a_number = f"A{model_match.group(1)}"
        if a_number in model_map:
            return model_map[a_number], "model_match"

    # Step 3: Apple product name keywords
    for category, keywords in APPLE_PRODUCT_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category, "keyword_match"

    # Apple eMac (word boundary to avoid matching "eMachines")
    if re.search(r"(?<![a-z])emac(?![a-z])", name_lower):
        return "Apple/Computers/Other_Mac", "keyword_match"

    # Generic "apple" or "mac" keyword (without matching "macbook" which is caught above)
    if "apple" in name_lower:
        return "Apple/Other_Apple", "keyword_match"

    # Apple MLB/codename patterns (J80G_MLB, K16_MLB, M57-DVT-MLB, Boardview_J80G_MLB)
    if re.search(r"(?<![a-z0-9])(?:j\d{2,3}[a-z]?|k\d{2}[a-z]?|m\d{2}[a-z]?)[_ -]?(?:mlb|dvt|evt|pvt)", name_lower):
        return "Apple/Other_Apple", "keyword_match"
    if re.search(r"(?:mlb|boardview)[_ -]?(?:j\d{2,3}|k\d{2}|m\d{2})", name_lower):
        return "Apple/Other_Apple", "keyword_match"
    if " mlb " in name_lower or "_mlb" in name_lower or "mlb_" in name_lower:
        # "MLB" alone is ambiguous but combined with other hints
        if "820" in name_lower or "051" in name_lower:
            return "Apple/Other_Apple", "keyword_match"

    # Step 4: Non-Apple brand detection (substring keywords)
    for brand, keywords in BRAND_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return brand, "brand_match"

    # Short brand keywords with regex boundaries
    for brand, pattern in BRAND_REGEX_PATTERNS.items():
        if pattern.search(name_lower):
            if brand == "LG":
                return "Other_Brands", "brand_match"
            return brand, "brand_match"

    # Step 5: Fallback
    return "Unsorted", "fallback"


# ── Core Operations ───────────────────────────────────────────────────────────

def scan_files(download_dir: Path) -> list[Path]:
    """Walk all channel subdirectories, return list of file paths."""
    files: list[Path] = []
    if not download_dir.exists():
        return files
    for channel_dir in sorted(download_dir.iterdir()):
        if not channel_dir.is_dir():
            continue
        for f in sorted(channel_dir.iterdir()):
            if f.is_file():
                files.append(f)
    return files


def plan_moves(
    files: list[Path],
    board_map: dict[str, str],
    model_map: dict[str, str],
    organized_dir: Path,
) -> list[dict]:
    """Plan all file moves. Returns list of {src, dest, category, confidence}."""
    moves: list[dict] = []
    # Track target filenames to handle duplicates
    used_targets: dict[str, int] = {}

    for f in files:
        category, confidence = classify(f.name, board_map, model_map)
        target_dir = organized_dir / category
        target_path = target_dir / f.name

        # Handle duplicate filenames in target directory
        target_key = str(target_path)
        if target_key in used_targets:
            used_targets[target_key] += 1
            channel = f.parent.name
            stem = f.stem
            suffix = f.suffix
            target_path = target_dir / f"{stem}_{channel}{suffix}"
            # Still duplicate? Add counter
            new_key = str(target_path)
            if new_key in used_targets:
                used_targets[new_key] += 1
                target_path = target_dir / f"{stem}_{channel}_{used_targets[new_key]}{suffix}"
        used_targets[target_key] = used_targets.get(target_key, 0)

        moves.append({
            "src": str(f),
            "dest": str(target_path),
            "category": category,
            "confidence": confidence,
        })

    return moves


def execute_moves(moves: list[dict], verbose: bool = False) -> int:
    """Move files to organized directories. Returns count of successful moves."""
    moved = 0
    errors = 0

    for m in moves:
        src = Path(m["src"])
        dest = Path(m["dest"])

        if not src.exists():
            if verbose:
                print(f"  SKIP (missing): {src.name}")
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(src), str(dest))
            moved += 1
            if verbose:
                print(f"  OK: {src.name} -> {m['category']}")
        except OSError as e:
            print(f"  ERROR: {src.name}: {e}")
            errors += 1

    return moved


def update_state(state_path: Path, moves: list[dict]) -> int:
    """Update state.json paths to reflect new file locations. Returns update count."""
    if not state_path.exists():
        return 0

    state = json.loads(state_path.read_text())
    path_map = {m["src"]: m["dest"] for m in moves}

    updated = 0
    for key, old_path in state.get("downloaded", {}).items():
        if old_path in path_map:
            state["downloaded"][key] = path_map[old_path]
            updated += 1

    state_path.write_text(json.dumps(state, indent=2))
    return updated


def save_manifest(manifest_path: Path, moves: list[dict]) -> None:
    """Save move manifest for undo capability."""
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "move_count": len(moves),
        "moves": [{"src": m["src"], "dest": m["dest"]} for m in moves],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))


def undo_moves(manifest_path: Path, state_path: Path, state_backup: Path) -> None:
    """Reverse all moves using the manifest."""
    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())
    moves = manifest["moves"]
    print(f"Undoing {len(moves)} moves from {manifest['timestamp']}...")

    restored = 0
    errors = 0
    for m in moves:
        src = Path(m["dest"])   # current location
        dest = Path(m["src"])   # original location

        if not src.exists():
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dest))
            restored += 1
        except OSError as e:
            print(f"  ERROR restoring {src.name}: {e}")
            errors += 1

    # Restore state.json from backup
    if state_backup.exists():
        shutil.copy2(str(state_backup), str(state_path))
        print(f"Restored state.json from backup")

    # Clean up empty organized directories
    organized_dir = Path(moves[0]["dest"]).parent if moves else ORGANIZED_DIR
    _cleanup_empty_dirs(ORGANIZED_DIR)

    print(f"Done: {restored} files restored, {errors} errors")


def _cleanup_empty_dirs(root: Path) -> None:
    """Remove empty directories under root (bottom-up)."""
    if not root.exists():
        return
    for dirpath in sorted(root.rglob("*"), reverse=True):
        if dirpath.is_dir() and not any(dirpath.iterdir()):
            dirpath.rmdir()
    if root.is_dir() and not any(root.iterdir()):
        root.rmdir()


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_report(moves: list[dict]) -> None:
    """Print classification statistics."""
    category_counts: Counter[str] = Counter()
    confidence_by_category: dict[str, Counter[str]] = {}

    for m in moves:
        cat = m["category"]
        conf = m["confidence"]
        category_counts[cat] += 1
        if cat not in confidence_by_category:
            confidence_by_category[cat] = Counter()
        confidence_by_category[cat][conf] += 1

    print(f"\n{'─' * 80}")
    print(f"{'Category':<45} {'Count':>6}  Confidence Breakdown")
    print(f"{'─' * 80}")

    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        conf = confidence_by_category[cat]
        conf_str = "  ".join(f"{k}:{v}" for k, v in sorted(conf.items(), key=lambda x: -x[1]))
        print(f"  {cat:<43} {count:>6}  {conf_str}")

    print(f"{'─' * 80}")
    print(f"  {'TOTAL':<43} {sum(category_counts.values()):>6}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Organize schematic downloads by brand/product")
    p.add_argument("--dry-run", action="store_true", help="Preview moves without executing")
    p.add_argument("--report", action="store_true", help="Show classification stats only")
    p.add_argument("--undo", action="store_true", help="Reverse organization using manifest")
    p.add_argument("--verbose", "-v", action="store_true", help="Show each file classification")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.undo:
        undo_moves(MANIFEST_FILE, STATE_FILE, STATE_BACKUP)
        return

    if not REFERENCE_FILE.exists():
        print(f"Reference file not found: {REFERENCE_FILE}")
        sys.exit(1)

    # Build lookup tables
    board_map = build_board_lookup(REFERENCE_FILE)
    model_map = build_model_lookup(REFERENCE_FILE)
    print(f"Loaded {len(board_map)} board numbers, {len(model_map)} model numbers")

    # Scan and classify
    files = scan_files(DOWNLOAD_DIR)
    if not files:
        print("No files found in download directory")
        return
    print(f"Found {len(files)} files to classify")

    moves = plan_moves(files, board_map, model_map, ORGANIZED_DIR)
    print_report(moves)

    if args.report:
        return

    if args.dry_run:
        for m in moves:
            src_name = Path(m["src"]).name
            print(f"  {src_name} -> {m['category']}  [{m['confidence']}]")
        return

    # Execute moves
    print("Backing up state.json...")
    if STATE_FILE.exists():
        shutil.copy2(str(STATE_FILE), str(STATE_BACKUP))

    print("Saving manifest...")
    save_manifest(MANIFEST_FILE, moves)

    print("Moving files...")
    moved = execute_moves(moves, verbose=args.verbose)

    print("Updating state.json...")
    updated = update_state(STATE_FILE, moves)

    print(f"\nDone: {moved} files moved, {updated} state entries updated")
    print(f"State backup: {STATE_BACKUP}")
    print(f"Undo manifest: {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
