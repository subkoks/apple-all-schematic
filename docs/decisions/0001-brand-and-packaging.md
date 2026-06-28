# 1. Brand name "BoardVault" and unsigned macOS distribution

Date: 2026-06-28

## Status

Accepted

## Context

The project shipped under the descriptive working title "Apple Schematic Downloader" (repo
`apple-all-schematic`). It needed a real product brand for the desktop app, and a distribution format
for macOS. Using "Apple" in the product name carries trademark risk; code-signing/notarization
requires a paid Apple Developer ID the project does not have.

## Decision

- **Brand: BoardVault** — distinctive and trademark-safer than putting "Apple" in the name, while the
  tagline ("Apple schematic & boardview downloader") and keywords preserve discoverability. Bundle id
  `com.subkoks.boardvault`; data dir `~/Library/Application Support/subkoks/BoardVault/`.
- **GitHub slug stays `apple-all-schematic`** (preserves stars, links, and SEO); only the
  description, topics, homepage, and README are rebranded. The Python distribution name is unchanged.
- **Distribute an unsigned `.dmg`.** First-launch is gated by Gatekeeper; users open it once via
  right-click → Open (or strip the quarantine attribute). Documented in the README and the build
  script output.

## Consequences

- Renaming the app moved the per-user data dir; a one-time `paths.migrate_legacy()` copies the
  pre-rebrand session/settings so users are not forced to re-log-in.
- Distribution is free and reproducible, at the cost of the first-launch Gatekeeper friction. If a
  Developer ID becomes available, codesign + notarytool steps can be added to `build_dmg.sh` without
  other changes.
- The brand is hard to reverse once published (URLs, user installs), which is why it was chosen
  explicitly rather than defaulted.
