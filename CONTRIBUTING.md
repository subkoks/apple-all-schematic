# Contributing

Thanks for considering a contribution. This is a small Python tool for bulk
downloading Apple device schematics and boardview files from public Telegram
channels. Keep changes focused and reproducible.

## Quick start

```bash
git clone https://github.com/subkoks/apple-all-schematic.git
cd apple-all-schematic

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # fill in TELEGRAM_API_ID / TELEGRAM_API_HASH
```

Never commit a real `.env` or session file.

## Workflow

1. Open an issue first for non-trivial changes.
2. Branch from `main`:
   - `feat/...` new feature
   - `fix/...` bug fix
   - `chore/...` tooling, refactor, infra
   - `docs/...` documentation only
3. Keep PRs focused: one logical change per PR.
4. Update `README.md` if user-visible behavior changes.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

## Code style

- Python 3.11+; type hints on public functions.
- Prefer `pathlib.Path` over `os.path`.
- Use `ruff format` + `ruff check` if available locally.

## Reporting bugs and feature requests

Use the issue templates: `Bug report` or `Feature request`. Security issues
go through `SECURITY.md`, not the public tracker.

## License

By contributing you agree your work is licensed under the MIT License (see
`LICENSE`).
