"""Unit tests for src/validation.py.

Run with:

    python -m pytest tests/

or, without pytest installed:

    python -m unittest tests/test_validation.py
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Make ``src/`` importable when running via ``python -m unittest`` from the
# repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from validation import (  # noqa: E402  (import after sys.path manipulation)
    MAX_FILENAME_LENGTH,
    MAX_KEYWORD_LENGTH,
    ValidationError,
    sanitize_filename,
    validate_channel_name,
    validate_channel_names,
    validate_extension,
    validate_extensions,
    validate_keyword,
    validate_keywords,
)


class ValidateChannelNameTests(unittest.TestCase):
    def test_accepts_plain_username(self):
        self.assertEqual(validate_channel_name("schematicslaptop"), "schematicslaptop")

    def test_strips_leading_at_sign(self):
        self.assertEqual(validate_channel_name("@biosarchive"), "biosarchive")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(validate_channel_name("  hrtechno  "), "hrtechno")

    def test_preserves_case_and_underscores(self):
        self.assertEqual(
            validate_channel_name("SMART_PHONE_SCHEMATICS"),
            "SMART_PHONE_SCHEMATICS",
        )

    def test_rejects_empty(self):
        for value in ["", "   ", "@", " @ "]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_channel_name(value)

    def test_rejects_too_short(self):
        # Telegram usernames must be at least 5 chars.
        with self.assertRaises(ValidationError):
            validate_channel_name("abcd")

    def test_rejects_too_long(self):
        # 33 chars > 32 limit.
        with self.assertRaises(ValidationError):
            validate_channel_name("a" + "b" * 32)

    def test_rejects_leading_digit(self):
        with self.assertRaises(ValidationError):
            validate_channel_name("1channel")

    def test_rejects_path_traversal(self):
        for value in [
            "../etc/passwd",
            "..",
            "foo/bar",
            "foo\\bar",
            "chan/../../evil",
            "@../secret_admin",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_channel_name(value)

    def test_rejects_null_byte(self):
        with self.assertRaises(ValidationError):
            validate_channel_name("chan\x00nel")

    def test_rejects_newline_injection(self):
        with self.assertRaises(ValidationError):
            validate_channel_name("chan\nnel")

    def test_rejects_shell_metacharacters(self):
        for value in [
            "chan;rm -rf /",
            "chan`whoami`",
            "chan$(id)",
            "chan|ls",
            "chan&sleep",
            "chan name",
            "chan-name",
            "chan.name",
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_channel_name(value)

    def test_rejects_non_string(self):
        for value in [None, 42, b"bytes", ["list"]]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_channel_name(value)


class ValidateChannelNamesTests(unittest.TestCase):
    def test_deduplicates_preserving_order(self):
        result = validate_channel_names(["alpha_one", "@alpha_one", "beta_two"])
        self.assertEqual(result, ["alpha_one", "beta_two"])

    def test_raises_on_first_invalid(self):
        with self.assertRaises(ValidationError):
            validate_channel_names(["good_name", "bad/name"])

    def test_rejects_non_sequence(self):
        with self.assertRaises(ValidationError):
            validate_channel_names("not_a_list")


class ValidateExtensionTests(unittest.TestCase):
    def test_accepts_with_dot(self):
        self.assertEqual(validate_extension(".pdf"), ".pdf")

    def test_adds_missing_dot(self):
        self.assertEqual(validate_extension("pdf"), ".pdf")

    def test_lowercases_and_strips(self):
        self.assertEqual(validate_extension("  .PDF  "), ".pdf")

    def test_accepts_alphanumeric(self):
        self.assertEqual(validate_extension(".7z"), ".7z")

    def test_rejects_empty(self):
        for value in ["", "   ", "."]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_extension(value)

    def test_rejects_path_traversal(self):
        for value in ["./../etc", ".pdf/foo", ".pd\\f"]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_extension(value)

    def test_rejects_null_byte(self):
        with self.assertRaises(ValidationError):
            validate_extension(".pd\x00f")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            validate_extension("." + "a" * 11)

    def test_rejects_special_chars(self):
        for value in [".pd-f", ".pd f", ".pd.f", ".pd;rm"]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_extension(value)

    def test_rejects_non_string(self):
        with self.assertRaises(ValidationError):
            validate_extension(123)


class ValidateExtensionsTests(unittest.TestCase):
    def test_returns_normalised_set(self):
        self.assertEqual(validate_extensions([".PDF", "zip"]), {".pdf", ".zip"})

    def test_rejects_non_collection(self):
        with self.assertRaises(ValidationError):
            validate_extensions("pdf")


class ValidateKeywordTests(unittest.TestCase):
    def test_accepts_typical_keyword(self):
        self.assertEqual(validate_keyword("iphone"), "iphone")

    def test_strips_whitespace_preserves_case(self):
        self.assertEqual(validate_keyword("  MacBook Pro  "), "MacBook Pro")

    def test_accepts_regex_metacharacters(self):
        # Keywords are used for substring matching, so dots, parens, dashes,
        # brackets, etc. are legitimate filter tokens.
        for value in ["820-02", "a.b", "(n61)", "x[0-9]", "c++"]:
            with self.subTest(value=value):
                self.assertEqual(validate_keyword(value), value)

    def test_rejects_empty(self):
        for value in ["", "   ", "\t  \n"]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_keyword(value)

    def test_rejects_null_byte(self):
        with self.assertRaises(ValidationError):
            validate_keyword("iph\x00one")

    def test_rejects_control_characters(self):
        for value in ["iph\none", "iph\rone", "iph\x1bone"]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_keyword(value)

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            validate_keyword("x" * (MAX_KEYWORD_LENGTH + 1))

    def test_rejects_non_string(self):
        for value in [None, 42, [".pdf"], {"kw": 1}]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_keyword(value)


class ValidateKeywordsTests(unittest.TestCase):
    def test_preserves_duplicates_and_order(self):
        self.assertEqual(
            validate_keywords(["iphone", "ipad", "iphone"]),
            ["iphone", "ipad", "iphone"],
        )

    def test_raises_on_first_invalid(self):
        with self.assertRaises(ValidationError):
            validate_keywords(["good", ""])

    def test_rejects_non_sequence(self):
        with self.assertRaises(ValidationError):
            validate_keywords("iphone")


class SanitizeFilenameTests(unittest.TestCase):
    def test_accepts_plain_name(self):
        self.assertEqual(sanitize_filename("iPhone_15.pdf"), "iPhone_15.pdf")

    def test_preserves_unicode(self):
        self.assertEqual(sanitize_filename("Résumé.pdf"), "Résumé.pdf")

    def test_strips_posix_path(self):
        self.assertEqual(
            sanitize_filename("../../etc/passwd"),
            "passwd",
        )

    def test_strips_windows_path(self):
        self.assertEqual(
            sanitize_filename(r"C:\Windows\System32\evil.dll"),
            "evil.dll",
        )

    def test_strips_mixed_separators(self):
        self.assertEqual(
            sanitize_filename("foo/bar\\baz/file.pdf"),
            "file.pdf",
        )

    def test_rejects_null_byte(self):
        self.assertIsNone(sanitize_filename("file\x00.pdf"))

    def test_rejects_control_characters(self):
        for value in ["file\n.pdf", "file\r.pdf", "file\x1b.pdf"]:
            with self.subTest(value=value):
                self.assertIsNone(sanitize_filename(value))

    def test_rejects_dot_segments(self):
        self.assertIsNone(sanitize_filename("."))
        self.assertIsNone(sanitize_filename(".."))
        # A path that reduces to ".." after stripping separators must also be
        # rejected.
        self.assertIsNone(sanitize_filename("foo/.."))

    def test_rejects_empty_and_whitespace(self):
        for value in ["", "   ", "/"]:
            with self.subTest(value=value):
                self.assertIsNone(sanitize_filename(value))

    def test_rejects_non_string(self):
        for value in [None, 42, b"file.pdf"]:
            with self.subTest(value=value):
                self.assertIsNone(sanitize_filename(value))

    def test_truncates_long_names_preserving_extension(self):
        long_stem = "a" * 400
        result = sanitize_filename(f"{long_stem}.pdf")
        self.assertIsNotNone(result)
        assert result is not None  # for type-checker narrowing
        self.assertTrue(result.endswith(".pdf"))
        self.assertLessEqual(len(result), MAX_FILENAME_LENGTH)

    def test_truncates_long_names_without_extension(self):
        result = sanitize_filename("b" * 400)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(len(result), MAX_FILENAME_LENGTH)


class DownloaderIntegrationTests(unittest.TestCase):
    """Smoke test that the downloader module imports with validation wired in.

    The downloader pulls in ``telethon`` and ``tqdm``. We skip if they are
    unavailable in the test environment rather than forcing a heavy install
    for the validation test suite.
    """

    def test_module_imports(self):
        try:
            import telethon  # noqa: F401
            import tqdm  # noqa: F401
            from dotenv import load_dotenv  # noqa: F401
        except ImportError:
            self.skipTest("telethon/tqdm/python-dotenv not installed")

        # Ensure the downloader can be imported and that its ALLOWED_EXTENSIONS
        # and CHANNELS constants came out of the validators without raising.
        import importlib

        sys.path.insert(0, str(_REPO_ROOT / "src"))
        module = importlib.import_module("tg_schematic_downloader")
        self.assertIsInstance(module.ALLOWED_EXTENSIONS, set)
        self.assertIn(".pdf", module.ALLOWED_EXTENSIONS)
        self.assertTrue(module.CHANNELS["laptop"])
        for name in module.CHANNELS["laptop"]:
            # All post-validation channel names must match the strict pattern.
            self.assertTrue(name and "/" not in name and "\\" not in name)


if __name__ == "__main__":
    unittest.main()
