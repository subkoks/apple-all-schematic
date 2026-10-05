# Native frontend verification — updated 2026-10-06

## Release candidate 2.1.0-rc.1

Prepared locally from release-source commit `53701fc`, bundle build **20101**. No GitHub push,
tag, PR, workflow dispatch, or release publication was performed. A local source/diff review
fixed channel failure/no-match states, search-specific resume counts, idle speed, repeated count
refreshes, and the default/minimum-width progress layout. This was a local review, not an
independent security audit.

- **PASS:** 160 Python tests plus 56 subtests; 15 Swift tests; Ruff on the changed/native Python
  code; shellcheck; actionlint on both new GitHub workflows; whitespace/diff checks.
- **PASS:** signed x86_64 release app with macOS <=13 binary metadata at `dist/native/BoardVault.app`.
- **PASS:** versioned ZIP integrity, signature of the extracted app, and SHA256SUMS verification.
  Assets/notes/manifest: `dist/releases/2.1.0-rc.1-x86_64/`. The manifest records source commit,
  build/version, architecture, ad-hoc signing, no notarization, and clean release build inputs.
- **PASS:** packaged-engine config/scan/organize/undo and restored fixture state;
  `build/native-engine-smoke-8tx5sh4y/report.json`.
- **FAIL / desktop gate pending:** fixture app launch exited -6 (SIGABRT), with no UI report
  produced, in the managed runtime. Evidence: `build/native-smoke-rs0ony_v/ui-smoke.json`.
  The latest candidate needs a normal desktop Terminal run; no current visual acceptance is claimed.
- **BLOCKED:** fresh DMG creation failed with `hdiutil: create failed - Device not configured`.
  Only the verified ZIP is included in the candidate directory. An unversioned older DMG in
  `dist/` is not a candidate asset.
- **PENDING:** GitHub jobs have not run. Fresh login, actual Ventura execution, Keychain,
  Quick Look and notification acceptance remain manual checks. Earlier user download screenshots
  establish earlier app behavior, not final-candidate acceptance.

See [RELEASING_NATIVE.md](RELEASING_NATIVE.md) for the exact gates and publication boundary.

## Earlier implementation evidence

Implementation is complete locally; **full acceptance is not complete**. The existing PySide6
GUI sources and build scripts have no task changes. No real Telegram credentials or sessions
were read by the agent, and the agent performed no real Telegram account operation.
The user subsequently confirmed a real download in the installed app on 2026-10-05: screenshots
show live progress, then completion with 3 downloaded, 41 skipped and 0 errors. This verifies an
authorized session download; it does not establish that fresh phone/code/2FA prompts were tested.

## Compact download layout — 2026-10-05

Build 20006 starts the sidebar Activity log collapsed; its joined log text and ScrollView are
created only while expanded. Swift tests and release bundle checks cover this update; desktop
visual acceptance remains pending.

Build 20005 adds a prominent top search field and selectable Any/All/Phrase matching, field scope,
and file-format filters. The default is now Any word to recover broader results while retaining
whole-term boundaries. Progress is one row per channel; the activity log is in the sidebar.
Channel menus persist up/down ordering. Approximate subscriber counts are fetched from public
Telegram previews without using the account session; channels without a readable public count
show no number. Python: 158 tests plus 56 subtests; Swift: 14 tests. Ruff, shellcheck, x86_64
release bundle validation, signature verification, and packaged-engine fixture smoke pass. The
latest app is `dist/native/BoardVault.app`; DMG creation failed here with `hdiutil: Device not
configured`, so `dist/BoardVault-native.dmg` is older. The new UI has not had a desktop visual
smoke check or a real-account download in this build.

### Earlier compact layout

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

- **PASS:** 158 Python tests, plus 56 subtests. Run from `tests/` with dotenv disabled to avoid
  pytest traversing the denied repo `.env` during collection.
- **PASS:** 14 Swift XCTest tests, including malformed engine output, stderr draining, login
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
