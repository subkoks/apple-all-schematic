# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository community-health files: `SECURITY.md`, `CONTRIBUTING.md`,
  this `CHANGELOG.md`, `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/*`,
  `.github/pull_request_template.md`, and `.github/dependabot.yml`.

## 2.1.0-rc.1 — Native release candidate

### Added

- Native SwiftUI macOS app for Intel/macOS 13+, with Download, Organize, Library, Settings,
  in-app Telegram login, Keychain credentials, theme selection, keyboard commands, Dock progress,
  and optional notifications. The existing Qt GUI and CLI remain available.
- Prominent search with Any/All/Phrase matching, filename/caption scope, and format filters.
  Whole-term boundaries reject M50 for M5 and preserve board IDs across separators.
- Compact single-row progress, persistent channel ordering, approximate public subscriber counts,
  and a sidebar Activity log that starts collapsed and renders entries only while open.
- Ten optional channel additions, offered once unchecked; documented source evidence and
  migration preserve existing choices, custom channels, and removals.
- Previewed organization with journaled undo, collision checks, safe file publication,
  incomplete-download checks, atomic state writes, and redacted JSON sidecar events.
- Native circuit-vault icon, a dedicated user guide, and About version/build details.
- Versioned release ZIP/DMG assets, checksums and source manifest, portable pinned Python
  packaging, signature/architecture checks, Python and Swift CI tests, and a manual build workflow.

### Fixed

- Native progress columns fit the minimum window size; idle speed resets after completion.
- Unavailable channels show a terminal failure state, and native resume counts include only
  files matching the active search. Legacy CLI/Qt matching remains unchanged.

### Known limits

- Desktop fixture acceptance and Python/Intel Swift CI passed. Fresh-login, Keychain, Quick Look,
  notifications, and actual Ventura execution remain unverified. See [release preparation](docs/RELEASING_NATIVE.md).
- Intel only; ad-hoc signed without Developer ID notarization. Universal binaries are deferred.

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
