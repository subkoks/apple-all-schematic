"""Native-only query matching and file-format selection."""

import re
from pathlib import Path

TOKENS = re.compile(r"[^\W_]+", re.UNICODE)
MACBOOK = re.compile(r"mac[\W_]*book", re.IGNORECASE)
MACBOOK_MODEL = re.compile(r"macbook(pro|air)\b", re.IGNORECASE)
CHIP_VARIANT = re.compile(r"\b(m\d+)(pro|max|ultra)\b", re.IGNORECASE)
BOARD_NUMBER = re.compile(r"\b(820)[-_ ]?(\d{4,5})\b", re.IGNORECASE)
FILE_TYPES = {
    "pdf": frozenset({".pdf"}),
    "boardview": frozenset(
        {
            ".brd",
            ".bvr",
            ".bdv",
            ".bv",
            ".cad",
            ".fz",
            ".asc",
            ".tvw",
            ".pcb",
            ".ddb",
            ".cst",
            ".f2b",
            ".gr",
        }
    ),
    "archive": frozenset({".zip", ".rar", ".7z"}),
    "firmware": frozenset({".bin", ".rom"}),
}
SEARCH_MODES = frozenset({"any", "all", "phrase"})
SEARCH_SCOPES = frozenset({"both", "filename", "caption"})


def words(text: str) -> list[str]:
    text = MACBOOK.sub("macbook", text.casefold())
    text = MACBOOK_MODEL.sub(r"macbook \1", text)
    text = CHIP_VARIANT.sub(r"\1 \2", text)
    text = BOARD_NUMBER.sub(r"board\1\2", text)
    return TOKENS.findall(text)


def tokens(text: str) -> set[str]:
    return set(words(text))


def matches(text: str, query: str, mode: str = "all") -> bool:
    """Match normalized whole tokens; board numbers remain atomic across separators."""
    if not query.strip():
        return True
    wanted = words(query)
    if not wanted:
        return False
    found = words(text)
    if mode == "any":
        return bool(set(wanted) & set(found))
    if mode == "all":
        return set(wanted) <= set(found)
    if mode == "phrase":
        return any(
            found[index : index + len(wanted)] == wanted
            for index in range(len(found) - len(wanted) + 1)
        )
    raise ValueError("Invalid search mode")


def matching_fields(filename: str, caption: str, query: str, mode: str, scope: str) -> bool:
    if scope not in SEARCH_SCOPES:
        raise ValueError("Invalid search scope")
    if scope == "both" and mode == "phrase":
        return matches(filename, query, mode) or matches(caption, query, mode)
    text = {"both": f"{filename} {caption}", "filename": filename, "caption": caption}[scope]
    return matches(text, query, mode)


def matching_type(filename: str, selected: list[str] | None) -> bool:
    if selected is None:
        return True
    if any(item not in FILE_TYPES for item in selected):
        raise ValueError("Invalid file type")
    return Path(filename).suffix.lower() in set().union(*(FILE_TYPES[item] for item in selected))
