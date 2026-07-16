"""Tests for helper functions: is_apple, has_allowed_ext, get_filename, normalize_filename."""

# Import from the script by manipulating sys.path
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tg_schematic_downloader import (
    has_allowed_ext,
    is_apple,
    normalize_filename,
)

# ── is_apple ──────────────────────────────────────────────────────────────────


class TestIsApple:
    """Test Apple keyword and regex matching."""

    @pytest.mark.parametrize(
        "filename,caption",
        [
            ("MacBook_Pro_820-02457.pdf", ""),
            ("something.pdf", "iPhone 15 schematic"),
            ("A2141_schematic.pdf", ""),
            ("051-0001_board.pdf", ""),
            ("random.pdf", "macbook air M2"),
            ("EMC3178_board.pdf", ""),
            ("emc 2835 board.pdf", ""),
            ("n61_schematic.pdf", ""),
            ("d10_board.pdf", ""),
            ("j137_MLB.pdf", ""),
            ("boardview.brd", "apple watch s4"),
            ("test.pdf", "t8301 chip diagram"),
            ("imac_repair.pdf", ""),
            ("random.zip", "820-12345 archive"),
        ],
    )
    def test_matches_apple_files(self, filename: str, caption: str) -> None:
        assert is_apple(filename, caption) is True

    @pytest.mark.parametrize(
        "filename,caption",
        [
            ("Dell_Latitude_5520.pdf", ""),
            ("HP_ProBook_schematic.pdf", "laptop repair guide"),
            ("Lenovo_ThinkPad.rar", "bios dump"),
            ("random_file.pdf", "no relevant keywords here"),
            ("samsung_galaxy.pdf", "phone repair"),
            ("ASUS_ROG.zip", "gaming laptop"),
        ],
    )
    def test_rejects_non_apple_files(self, filename: str, caption: str) -> None:
        assert is_apple(filename, caption) is False

    def test_case_insensitive(self) -> None:
        assert is_apple("IPHONE_15.PDF", "") is True
        assert is_apple("macBOOK.pdf", "") is True
        assert is_apple("a2141_board.pdf", "") is True

    def test_regex_model_numbers(self) -> None:
        assert is_apple("A1278_schematic.pdf", "") is True
        assert is_apple("A2141.pdf", "") is True
        assert is_apple("A3113_board.brd", "") is True

    def test_regex_does_not_match_partial(self) -> None:
        # "ba1278" should not match — has leading letter
        assert is_apple("ba1278_file.pdf", "") is False
        # "a12789" — 5 digits, not 4
        assert is_apple("a12789_file.pdf", "") is False


# ── has_allowed_ext ───────────────────────────────────────────────────────────


class TestHasAllowedExt:
    @pytest.mark.parametrize(
        "filename",
        [
            "schematic.pdf", "archive.zip", "archive.rar", "archive.7z",
            "board.brd", "board.bvr", "board.bdv", "board.bv",
            "board.cad", "board.fz", "board.asc", "board.tvw",
            "board.pcb", "board.ddb", "board.cst", "board.f2b", "board.gr",
            "firmware.bin", "firmware.rom",
        ],
    )
    def test_allowed_extensions(self, filename: str) -> None:
        assert has_allowed_ext(filename) is True

    @pytest.mark.parametrize(
        "filename",
        [
            "readme.txt", "image.jpg", "photo.png", "document.docx",
            "script.py", "data.csv", "page.html", "movie.mp4",
        ],
    )
    def test_rejected_extensions(self, filename: str) -> None:
        assert has_allowed_ext(filename) is False

    def test_case_insensitive_ext(self) -> None:
        assert has_allowed_ext("SCHEMATIC.PDF") is True
        assert has_allowed_ext("Board.BRD") is True


# ── normalize_filename ────────────────────────────────────────────────────────


class TestNormalizeFilename:
    def test_strips_whitespace(self) -> None:
        assert normalize_filename("  file.pdf  ") == "file.pdf"

    def test_lowercases(self) -> None:
        assert normalize_filename("MacBook_Pro.PDF") == "macbook_pro.pdf"

    def test_already_normalized(self) -> None:
        assert normalize_filename("simple.pdf") == "simple.pdf"
