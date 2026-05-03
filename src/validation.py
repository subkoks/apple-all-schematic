#!/usr/bin/env python3
"""
validation.py — Input validation for the Telegram schematic scraper.

Centralises defensive validators for all untrusted inputs used by the
downloader: CLI-supplied channel names, keyword filters, file extensions,
and filenames returned by the Telegram API.

The goals are:

1. Refuse obviously malformed input early with a clear error message
   instead of crashing deep inside Telethon, shutil, or pathlib.
2. Prevent path-traversal, null-byte and control-character injection
   that could cause files to be written outside the intended download
   directory (e.g. a message advertising a filename like
   ``../../etc/passwd`` or ``foo\x00.pdf``).
3. Keep the validators pure and dependency-free so they can be unit
   tested without network or Telegram credentials.
"""

from __future__ import annotations

import os
import re
from pathlib import PurePosixPath, PureWindowsPath

# ── Limits ────────────────────────────────────────────────────────────────────

# Telegram public username rules: 5–32 chars, start with a letter, and contain
# only ASCII letters, digits, and underscores. We accept a single optional "@"
# prefix which we strip before validation.
_CHANNEL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")

# File extensions as they appear in ALLOWED_EXTENSIONS: a leading dot followed
# by 1–10 lowercase ASCII alphanumerics. Kept intentionally strict — our
# allow-list never contains anything exotic.
_EXTENSION_RE = re.compile(r"^\.[a-z0-9]{1,10}$")

# Upper bounds to keep memory / log output sane and to refuse obviously abusive
# inputs without hard-coding business logic.
MAX_KEYWORD_LENGTH = 200
MAX_FILENAME_LENGTH = 255  # matches typical filesystem NAME_MAX


class ValidationError(ValueError):
    """Raised when an input fails validation.

    Subclass of ``ValueError`` so callers can choose to catch either. The
    message is always safe to surface to the user — we never echo back raw
    untrusted bytes, only a short description plus a bounded preview.
    """


# ── Helpers ───────────────────────────────────────────────────────────────────

def _preview(value: object, limit: int = 40) -> str:
    """Return a short ``repr`` of *value* suitable for error messages."""
    text = repr(value)
    if len(text) > limit:
        text = text[: limit - 1] + "…'"
    return text


def _has_control_chars(text: str) -> bool:
    """Return True if *text* contains NUL, newline, tab, or other control chars.

    Rejecting these prevents log-injection and filesystem surprises — neither
    channel names, keywords, nor filenames should ever contain them.
    """
    return any(ord(c) < 0x20 or ord(c) == 0x7F for c in text)


# ── Channel names ─────────────────────────────────────────────────────────────

def validate_channel_name(name: object) -> str:
    """Validate and normalise a Telegram channel/username.

    Accepts strings that look like Telegram public usernames (``5–32`` chars,
    start with a letter, ASCII alphanumerics and underscores). A single
    leading ``@`` is stripped. Surrounding whitespace is stripped before
    validation.

    Returns the normalised name without the ``@`` prefix.

    Raises:
        ValidationError: if *name* is not a non-empty string, contains
            disallowed characters, or does not match the Telegram username
            format. Disallowed characters include path separators (``/``,
            ``\\``), ``..`` segments, null bytes, and other control chars —
            any of which would be dangerous when the name is later used as a
            filesystem path component (``DOWNLOAD_DIR / channel``).
    """
    if not isinstance(name, str):
        raise ValidationError(
            f"channel name must be a string, got {type(name).__name__}"
        )

    stripped = name.strip().lstrip("@")
    if not stripped:
        raise ValidationError("channel name is empty")

    if _has_control_chars(stripped):
        raise ValidationError(
            f"channel name contains control characters: {_preview(name)}"
        )

    # Explicit path-traversal guard in addition to the regex below — gives a
    # clearer error and double-checks against subtle regex mistakes.
    if "/" in stripped or "\\" in stripped or ".." in stripped:
        raise ValidationError(
            f"channel name must not contain path separators or '..': {_preview(name)}"
        )

    if not _CHANNEL_NAME_RE.match(stripped):
        raise ValidationError(
            "channel name must be 5–32 chars, start with a letter, and contain "
            f"only letters, digits, and underscores: {_preview(name)}"
        )

    return stripped


def validate_channel_names(names: object) -> list[str]:
    """Validate a sequence of channel names, returning the normalised list.

    Duplicates are preserved in the order they first appear so the caller's
    intent is respected. Raises :class:`ValidationError` on the first
    invalid entry.
    """
    if not isinstance(names, (list, tuple)):
        raise ValidationError(
            f"channel list must be a list or tuple, got {type(names).__name__}"
        )

    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        normalised = validate_channel_name(name)
        if normalised not in seen:
            seen.add(normalised)
            result.append(normalised)
    return result


# ── Extensions ────────────────────────────────────────────────────────────────

def validate_extension(ext: object) -> str:
    """Validate a file-extension token and return its normalised form.

    The canonical form is lowercase, starts with ``.``, and contains only
    ASCII alphanumerics (1–10 chars after the dot). This matches the shape
    of entries in ``ALLOWED_EXTENSIONS``.

    Raises:
        ValidationError: if *ext* is not a string, is empty, contains
            disallowed characters (including ``/`` or null bytes), or
            doesn't match the expected pattern.
    """
    if not isinstance(ext, str):
        raise ValidationError(
            f"extension must be a string, got {type(ext).__name__}"
        )

    candidate = ext.strip().lower()
    if not candidate:
        raise ValidationError("extension is empty")

    # Allow callers to pass either ".pdf" or "pdf" — normalise to leading dot.
    if not candidate.startswith("."):
        candidate = "." + candidate

    if _has_control_chars(candidate):
        raise ValidationError(
            f"extension contains control characters: {_preview(ext)}"
        )

    if not _EXTENSION_RE.match(candidate):
        raise ValidationError(
            "extension must be a dot followed by 1–10 lowercase alphanumerics "
            f"(e.g. '.pdf'): {_preview(ext)}"
        )

    return candidate


def validate_extensions(exts: object) -> set[str]:
    """Validate a collection of extensions and return a normalised set."""
    if not isinstance(exts, (list, tuple, set, frozenset)):
        raise ValidationError(
            f"extensions must be a list/tuple/set, got {type(exts).__name__}"
        )
    return {validate_extension(e) for e in exts}


# ── Keywords ──────────────────────────────────────────────────────────────────

def validate_keyword(keyword: object) -> str:
    """Validate a keyword used for filename/caption filtering.

    Keywords are used as case-insensitive substring matches, so we don't
    need to escape regex metacharacters — but we still reject empty,
    excessively long, or control-character-bearing inputs that almost
    certainly indicate a mistake or an attempted injection.

    Returns the keyword stripped of leading/trailing whitespace (case is
    preserved so display output stays readable; callers lower-case as
    needed when matching).

    Raises:
        ValidationError: on empty/whitespace-only input, null bytes or
            other control chars, inputs longer than
            :data:`MAX_KEYWORD_LENGTH`, or non-string inputs.
    """
    if not isinstance(keyword, str):
        raise ValidationError(
            f"keyword must be a string, got {type(keyword).__name__}"
        )

    stripped = keyword.strip()
    if not stripped:
        raise ValidationError("keyword is empty or whitespace only")

    if len(stripped) > MAX_KEYWORD_LENGTH:
        raise ValidationError(
            f"keyword exceeds {MAX_KEYWORD_LENGTH} characters "
            f"(got {len(stripped)}): {_preview(keyword)}"
        )

    if _has_control_chars(stripped):
        raise ValidationError(
            f"keyword contains control characters: {_preview(keyword)}"
        )

    return stripped


def validate_keywords(keywords: object) -> list[str]:
    """Validate a sequence of keywords, returning the normalised list.

    Duplicates are preserved in input order so the caller's filter intent is
    unchanged. Raises :class:`ValidationError` on the first bad entry.
    """
    if not isinstance(keywords, (list, tuple)):
        raise ValidationError(
            f"keyword list must be a list or tuple, got {type(keywords).__name__}"
        )
    return [validate_keyword(k) for k in keywords]


# ── Filenames (from Telegram media attributes) ────────────────────────────────

def sanitize_filename(filename: object) -> str | None:
    """Return a safe basename for *filename* or ``None`` if it is unusable.

    Unlike the other validators this function is *lenient*: the filename
    comes from the Telegram server and a single bad entry shouldn't abort
    the whole run. The caller should treat ``None`` as "skip this message".

    Safety guarantees for the returned value:

    * It is a pure basename — any directory components supplied by the
      sender (``../../etc/passwd``, ``C:\\Windows\\x.dll``) are stripped.
    * It contains no NUL bytes or other ASCII control characters.
    * Its length is capped at :data:`MAX_FILENAME_LENGTH` characters
      (truncated from the stem, preserving the extension).
    * It is not ``.``, ``..``, or empty after sanitisation.
    """
    if not isinstance(filename, str):
        return None

    # Telegram shouldn't send NULs, but if it does we refuse rather than
    # silently truncating at the null byte.
    if "\x00" in filename:
        return None

    # Strip both POSIX and Windows directory components so a sender can't
    # smuggle path segments through either separator.
    basename = PurePosixPath(filename).name
    basename = PureWindowsPath(basename).name
    basename = os.path.basename(basename).strip()

    if not basename or basename in {".", ".."}:
        return None

    if _has_control_chars(basename):
        return None

    # Cap length while preserving the extension so `has_allowed_ext` still
    # works after truncation.
    if len(basename) > MAX_FILENAME_LENGTH:
        stem, dot, ext = basename.rpartition(".")
        if dot and len(ext) < MAX_FILENAME_LENGTH:
            keep = MAX_FILENAME_LENGTH - len(ext) - 1
            basename = f"{stem[:keep]}.{ext}"
        else:
            basename = basename[:MAX_FILENAME_LENGTH]

    return basename
