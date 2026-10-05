# Native frontend verification — 2026-10-05

Implementation is complete locally; **full acceptance is not complete**. The existing PySide6
GUI sources and build scripts have no task changes. No real Telegram credentials or sessions
were read, and no Telegram network operation was performed.

## Verified

- **PASS:** 142 Python tests, plus 56 subtests. Run from `tests/` with dotenv disabled to avoid
  pytest traversing the denied repo `.env` during collection.
- **PASS:** 11 Swift XCTest tests, including malformed engine output, stderr draining, login
  commands, crash handling, cancellation and force-stop of a SIGTERM-ignoring fixture.
- **PASS:** Ruff on changed Python files, shellcheck on the native build script, and diff checks.
- **PASS:** latest Intel release app built at `dist/native/BoardVault.app`.
- **PASS:** ad-hoc signature verification and three Mach-O binary checks: x86_64,
  minimum macOS <=13.0, no non-system absolute dylib dependencies.
- **PASS:** latest packaged engine config/scan/organize/undo from a temporary working directory,
  including original bytes and state-path restoration. Evidence:
  `build/native-engine-smoke-lf4zh34q/report.json`.
- **PASS:** latest packaged app launched from the user's normal desktop Terminal on this Intel
  Tahoe Mac, completed fixture scan/organize/undo, restored original bytes/state, and exited cleanly.
  All checks in `build/native-smoke-72f0lct5/ui-smoke.json` passed. Download, Settings, Organize and
  Library window captures were inspected; system materials and controls render correctly.
- **PASS:** refreshed `dist/BoardVault-native.dmg` built from the final application sources in the
  user's desktop Terminal on 2026-10-04 at 22:04. The app signature and binary checks passed again.
- **PASS:** M1–M8 have separate local milestone commits on `feat/native-swiftui`. M7 and M8 use
  the user-authorized per-command `commit.gpgsign=false` override because the configured SSH
  signing key is prohibited. Persistent Git settings were not changed; no signing key was read.

## Not exercised and environment limitations

- The managed execution environment could not launch AppKit (`_RegisterApplication` abort) or
  create disk images (`Device not configured`). The subsequent normal desktop Terminal run
  succeeded for both. Earlier failed reports remain historical evidence, not current build blockers.
- **Real Telegram acceptance pending:** fake clients and mock processes cover login and downloads;
  no real account login or channel download was attempted. `.env` and Keychain reads are explicitly
  prohibited in the current profile. The user must perform real-account acceptance in the app.
- **Manual platform checks pending:** real Keychain storage/access, Quick Look interaction,
  delivered notifications, keyboard/VoiceOver behavior, and execution on an actual macOS 13 Mac.
  Binary deployment metadata alone does not prove Ventura runtime compatibility.

## Complete the remaining acceptance

Open `dist/native/BoardVault.app` in the normal desktop session. Use Settings to save/import
credentials, log in, and download from one selected channel with a small message limit and resume
enabled. Verify progress, Stop, and a successful file. Confirm Quick Look and notifications manually.
These real-account steps are for the user; the agent has not accessed credentials or sessions.
Do not run Qt/CLI concurrently against the shared session/state. Native download publication
requires hard-link support (APFS supports it).

To repeat the fixture checks without Telegram access:

```bash
.venv/bin/python scripts/smoke_native_engine.py
.venv/bin/python scripts/smoke_native_app.py
```

The pre-existing staged `.codex/config.toml`, `.cursor/rules/project-overrides.mdc`, and `AGENTS.md`
changes were preserved and excluded from milestone commits. Nothing was pushed or published.
