# Bugbot — apple-all-schematic review rules

## Security (blocking)

- Never commit `TG_API_ID`, `TG_API_HASH`, session files (`*.session`), or `.env`.
- Flag `print()` of credentials, phone numbers, or session strings — use `logging` with redaction.
- Flag disabling Telethon flood-wait handling or removing rate-limit backoff.

## Python (`src/**`, `tests/**`)

- Use `pathlib.Path` rooted at `BASE_DIR`; flag `os.path` in new code.
- State file (`data/state.json`): flag writes without lock; flag schema changes without migration note.
- Downloader: flag missing retry on transient Telegram errors; flag parallel channel downloads exceeding configured limits.
- Organizer: flag destructive deletes without dry-run or backup note in PR description.

## Config (`args/config.json`)

- New channels/keywords should update `goals/APPLE_ALL_SCHEMATIC_PLAN.md` when behavior changes.

## Tests

- Helper and state logic changes need tests in `tests/`.

## Docs-only PRs

- Non-blocking for plan doc typos unless they contradict `context/APPLE_PRODUCT_REFERENCE.md`.

## Before merge

- `pytest` passes for changed modules.
