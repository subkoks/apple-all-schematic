# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Refined native search: all whole words must match, with joined MacBook/chip name support;
  `M5` no longer matches `M50`. Existing CLI/Qt matching is preserved.
- New native-only graphite/teal circuit-vault icon with reproducible AppKit source.

- Native SwiftUI macOS frontend in `native/BoardVault/` (macOS 13+, Intel first), preserving
  the existing Qt GUI: Download, Organize, Library, Settings, login sheets, keyboard commands,
  Dock progress, opt-in completion notifications, and Keychain credential storage.
- Opt-in Python `--json` sidecar protocol with validated stdin commands, redacted events,
  cancellable login/downloads, exact organization previews, and journaled undo.
- Native-only safe file publishing, incomplete-download checks, and atomic state writes.
- Isolated portable Python packaging, pinned build dependencies, architecture/minimum-OS checks,
  and `scripts/build_native_app.sh` producing `dist/BoardVault-native.dmg` without replacing Qt output.
- Python protocol/organizer tests, Swift mock-process tests, and a credential-free UI smoke check.
  Real Telegram and Keychain acceptance remain pending manual verification.

- Repository community-health files: `SECURITY.md`, `CONTRIBUTING.md`,
  this `CHANGELOG.md`, `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/*`,
  `.github/pull_request_template.md`, and `.github/dependabot.yml`.

## [2.0.0] - 2026-06-28

### Added

- **BoardVault desktop app (macOS):** a PySide6 + qasync GUI over the existing scraper —
  Download and Organize tabs, guided in-app Telegram login (phone/code/2FA), live per-channel
  progress, and an organized-library browser.
- **Theming:** System / Dark / Light with live macOS-appearance following.
- **Channel management:** add/remove Telegram channels from the UI, persisted per user.
- **Configurable locations:** change download/organized folders (native picker), reveal in Finder;
  a frozen app stores data under `~/Library/Application Support` and downloads to `~/Downloads`.
- **Settings:** tabbed Account / Appearance / Locations / Behavior / About & Help (instructions,
  links, version).
- **Packaging:** generated app icon and an unsigned drag-to-Applications `.dmg`
  (`scripts/make_icon.sh`, `scripts/build_dmg.sh`).
- One-time migration of pre-rebrand session/settings so existing users keep their login.

### Changed

- **Rebranded to BoardVault** (display name, app bundle `com.subkoks.boardvault`, `.dmg`). The
  GitHub repository slug and Python distribution name are unchanged.
- `process_channel` gained an optional, backward-compatible `progress` callback used by the GUI.

[Unreleased]: https://github.com/subkoks/apple-all-schematic/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/subkoks/apple-all-schematic/releases/tag/v2.0.0
