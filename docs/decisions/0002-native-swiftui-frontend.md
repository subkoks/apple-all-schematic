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
