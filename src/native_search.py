"""Whole-token, all-term matching for the native frontend only."""

import re

TOKENS = re.compile(r"[^\W_]+", re.UNICODE)
MACBOOK = re.compile(r"mac[\W_]*book", re.IGNORECASE)
MACBOOK_MODEL = re.compile(r"macbook(pro|air)\b", re.IGNORECASE)
CHIP_VARIANT = re.compile(r"\b(m\d+)(pro|max|ultra)\b", re.IGNORECASE)


def tokens(text: str) -> set[str]:
    text = MACBOOK.sub("macbook", text.casefold())
    text = MACBOOK_MODEL.sub(r"macbook \1", text)
    text = CHIP_VARIANT.sub(r"\1 \2", text)
    return set(TOKENS.findall(text))


def matches(text: str, query: str) -> bool:
    """An empty query matches all; punctuation alone matches nothing."""
    if not query.strip():
        return True
    wanted = tokens(query)
    return bool(wanted) and wanted <= tokens(text)
