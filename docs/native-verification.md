# Native frontend verification — 2026-10-05

Implementation is complete locally; **full acceptance is not complete**. The existing PySide6
GUI sources and build scripts have no task changes. No real Telegram credentials or sessions
were read by the agent, and the agent performed no Telegram network operation.
The user subsequently confirmed a real download in the installed app on 2026-10-05: screenshots
show live progress, then completion with 3 downloaded, 41 skipped and 0 errors. This verifies an
authorized session download; it does not establish that fresh phone/code/2FA prompts were tested.

## Compact download layout — 2026-10-05

Build 20004 replaces tall per-channel progress cards with compact rows (channel, truncated
filename, new/skipped/error counts, thin progress bar). Hover shows full channel/filename.
The fixture-only UI smoke mode now renders every configured channel in Download captures.
Swift build and 13 tests pass; the packaged app passes signature and x86_64/macOS 13 binary
checks. A new desktop screenshot and DMG refresh are still needed from a normal terminal.
`dist/BoardVault-native.dmg` remains an earlier artifact.

## Channel catalogue expansion — 2026-10-05

Build 20003 at `dist/native/BoardVault.app` embeds 22 channels, including 10 optional additions.
Five have directly observed public attachments; five have archived attachment evidence only.
See [channel-sources.md](channel-sources.md) for links and limits. The update preserves saved
selections/custom channels and offers additions once, unchecked. Regression tests cover duplicate
handles and removals. Test view models no longer load real preferences. Python: 155 tests plus
56 subtests; Swift: 13 tests. Release signature/architecture checks pass. No real Telegram operation
was performed. Desktop acceptance of this catalogue update remains user-run. The DMG is older;
rebuild it from normal Terminal to include build 20003.

## Search and icon refinement — 2026-10-05

- User-supplied screenshots confirm actual channel downloading and completion in the earlier build.
- Native download and Library search now require all whole tokens; regression cases reject M50
  for M5 and reject MacBook Air/M4 for MacBook Pro M5. Common joined names are normalized.
  These are filename/caption matches, not verified hardware metadata; numeric board IDs alone
  cannot establish a processor generation. CLI/Qt keyword behavior is preserved.
- The new circuit-vault icon is native-only. AppKit source and PNG/ICNS assets are checked in.
- Updated release app: `dist/native/BoardVault.app` (bundle build 20002). Signature and bundled
  engine fixture checks pass. The updated app has not yet had a desktop visual smoke test.
- **Current DMG is older:** rebuilding the refined app succeeded, but dmgbuild failed in this
  managed execution environment. `dist/BoardVault-native.dmg` still contains build 20001.
  Run `./scripts/build_native_app.sh` from the normal desktop Terminal to refresh the DMG.

## Verified

- **PASS:** 155 Python tests, plus 56 subtests. Run from `tests/` with dotenv disabled to avoid
  pytest traversing the denied repo `.env` during collection.
- **PASS:** 13 Swift XCTest tests, including malformed engine output, stderr draining, login
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
- **Earlier build PASS:** `dist/BoardVault-native.dmg` built from the M1–M8 sources in the
  user's desktop Terminal on 2026-10-04 at 22:04. The app signature and binary checks passed again.
- **PASS:** M1–M8 have separate local milestone commits on `feat/native-swiftui`. M7 and M8 use
  the user-authorized per-command `commit.gpgsign=false` override because the configured SSH
  signing key is prohibited. Persistent Git settings were not changed; no signing key was read.

## Not exercised and environment limitations

- The managed execution environment could not launch AppKit (`_RegisterApplication` abort) or
  create disk images (`Device not configured`). The subsequent normal desktop Terminal run
  succeeded for both. Earlier failed reports remain historical evidence, not current build blockers.
- **Fresh-login acceptance pending:** fake clients and mock processes cover login prompts.
  Real channel download was confirmed by the user; fresh account login was not separately confirmed. `.env` and Keychain reads are explicitly
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
