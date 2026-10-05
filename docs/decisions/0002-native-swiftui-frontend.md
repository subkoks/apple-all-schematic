# 2. Native SwiftUI frontend with a Python sidecar

Date: 2026-10-04
Status: Accepted; implementation and acceptance tracked below.

## Decisions

- Preserve `src/gui/` and all existing CLI behavior. Add `--json` opt-in only.
- SwiftPM package in `native/BoardVault`, no third-party Swift dependencies.
- macOS 13 minimum, Intel first. Build architecture is one script setting; universal
  additionally requires universal Python and compatible binary dependencies.
- [DECISION: macOS 13 compatibility] Use `ObservableObject`/`@Published` view models.
  SwiftUI Observation integration (`@Observable`) requires macOS 14. Do not raise
  the agreed deployment target or duplicate the entire UI to use that macro.
- Reuse Telethon and the Python classifier. Never implement Telegram in Swift.
- `EngineClient` actor owns Process/Pipe, Codable messages and AsyncStream.
  Version 1 JSONL events include channel_start, progress (current-file byte units),
  file_start, file_done, channel_done, error, login_required, done. Additional
  config and plan events support local configuration and organization.
- Commands are `{"command":"login_response","field":"phone|code|password","value":"…"}`
  and `{"command":"cancel"}`. EOF cancels. Error text is fixed and never includes
  exception details or authentication input. Stdout contains JSONL only.
- Cancellation: stdin command, bounded grace period, SIGTERM fallback; unexpected
  process exit, malformed output and missing terminal event surface as errors.
- Dev Python is repo `.venv` (uv); release engine is a PyInstaller onedir bundle.
  [DECISION: portable release Python] The host Python dylib requires macOS 26.2.
  Use `.venv-native-build` with a managed Python runtime and pinned requirements.
  Exclude the builder's optional Homebrew OpenSSL libraries; retain Telethon's pyaes
  fallback. Verify every bundled Mach-O has a macOS minimum <=13 and no external
  non-system dylib references. Build caches and retained artifacts are repo-local.
- Native state/session root in both modes:
  `~/Library/Application Support/subkoks/BoardVault/`; downloads default to
  `~/Downloads/BoardVault/`; library defaults to state-root/organized.
  Existing CLI remains on repo `data/`. Explicit `--data-dir` supports fixtures
  and deliberate legacy reuse. No automatic copying or reading of sessions.
- Keychain stores API ID/hash; child environment carries TG_API_ID/TG_API_HASH.
  Explicit file-picker migration reads a user-selected legacy .env. No implicit
  credential access at app launch. No credential values in preferences/logs.
- Native runs use a state-root process lock. Close the Qt app/CLI before native
  operations because those older clients do not participate in this lock.
- [DECISION: protect existing data] Native organizer adds collision checks,
  exact-preview execution, incremental undo journal and path confinement instead
  of inheriting the legacy organizer's overwrite/whole-state-restore behavior.
- Use system controls/materials, sidebar navigation, system accent, keyboard
  commands, accessible labels and explicit account actions.
- Preserve unrelated staged policy/config changes. Commit only milestone paths.

## Sources

- https://developer.apple.com/macos/get-started/
- https://developer.apple.com/design/human-interface-guidelines/designing-for-macos
- https://developer.apple.com/documentation/swiftui/migrating-from-the-observable-object-protocol-to-the-observable-macro

## Acceptance

Run Python tests with `PYTHON_DOTENV_DISABLED=1`, isolated temporary roots and fake
clients; Swift tests with mock sidecars. Real Telegram credentials/session access
requires separate approval. Build, launch and DMG checks do not imply a successful
real-channel download. Final verified results belong in the implementation report.

## Verification and remaining acceptance

- Python fixture tests cover event redaction, command validation, phone/code/2FA sequencing,
  cancellation, real downloader callbacks with a fake client, resume/collisions/incomplete files,
  preview changes, symlinks, organize/undo, and preservation of newer state entries.
- Swift tests cover pipe framing, malformed output, stderr backpressure, missing terminal events,
  login commands, cancellation fallback, view-model state, credential parsing and library indexing.
- The packaged app has launched on this Intel Tahoe Mac and completed fixture scan/organize/undo.
  Mach-O checks verify deployment metadata; they are not an actual Ventura runtime test.
- Real Telegram login/download, Keychain access, Quick Look interaction, delivered notifications,
  and macOS 13 runtime acceptance remain manual checks. Credential access is prohibited in the
  current agent permission profile; no attempt is made to bypass it.
- Native organization retains journals on errors. A crash leaving conflicting copies requires
  manual recovery; files are not overwritten to make an undo appear successful.

[DECISION: finish the final two local milestone commits with a per-command unsigned override,
as authorized by the user, because the configured SSH signing key is inaccessible. Preserve
persistent Git settings and do not access the key.]

See [native-verification.md](../native-verification.md) for final build, desktop smoke-test and
DMG evidence, plus the remaining real-account and platform acceptance checks.
