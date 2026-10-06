# Architecture — BoardVault (apple-all-schematic)

## Overview

Async Python engine that scrapes Apple device schematics from Telegram channels, with file
organization and categorization, exposed through a **CLI**, the existing **PySide6 desktop app**, and the **native SwiftUI app candidate**.
They reuse the same downloader/classifier. Installed desktop apps share Application Support paths;
the CLI and Qt development mode use repo `data/` unless deliberately configured otherwise.

## Desktop app (`src/gui/`)

The GUI reuses the CLI modules in-process — no IPC, no sidecar. `qasync` provides a single event
loop shared by Qt and Telethon's asyncio.

```
src/gui/
├── app.py            ← entry: QApplication + qasync loop; bootstraps paths + theme
├── core/
│   ├── settings.py   ← user prefs (theme, folders, channel overrides) as JSON
│   ├── paths.py      ← writable data-root resolution; overrides CLI path globals at startup
│   ├── config.py     ← merges args/config.json with the user's channel override
│   ├── auth.py       ← non-interactive Telegram login (phone/code/2FA via the UI)
│   ├── backend.py    ← DownloadController: cancellable task loop → Qt signals
│   └── organizer.py  ← async bridge to organize_downloads
└── ui/               ← main_window, download/organize views, dialogs, theme, icons
```

Key idea: instead of editing the CLI modules, `paths.apply()` reassigns their path globals
(`DOWNLOAD_DIR`, `STATE_FILE`, `SESSION_FILE`, …) once at startup, so a frozen `.app` writes to
user-writable locations while the CLI stays untouched. Packaging: PyInstaller spec → `.app`,
dmgbuild → unsigned `.dmg`.

## Module Map (engine)

```
src/
├── tg_schematic_downloader.py  ← Main Telegram download logic
└── organize_downloads.py       ← File categorization by brand/product

args/
└── config.json                 ← Channels, keywords, extensions, settings

data/
├── state.json                  ← Download state (channel:message_id tracking)
├── downloads/<channel>/        ← Raw files (empty after organization)
├── organized/<category>/       ← Categorized files (~10GB)
└── tg_scraper_session.session  ← Telethon auth session

context/
└── APPLE_PRODUCT_REFERENCE.md  ← Apple product/board number reference

goals/
└── APPLE_ALL_SCHEMATIC_PLAN.md ← Project plan, channel list, keywords
```

## Data Flow

1. Load config from `args/config.json` (with hardcoded fallbacks)
2. Connect to Telegram via Telethon async client
3. Iterate channels → filter by keywords/extensions → download
4. State saved after each download (crash resilience)
5. Resume tracking by channel/message ID, with filename collision handling within each channel
6. Organize: categorize files by brand/product into `data/organized/`

## Key Design Decisions

- State saved after every download for crash resilience
- Sequential channel processing; native channel order controls download priority
- Download failures surface through print/callback events; native events use redacted error text
- Telethon supplies Telegram transport and request-level handling
- Native file integrity checks against Telegram metadata before safe publication

## Native frontend (`native/BoardVault/`)

SwiftPM builds a SwiftUI executable and a dependency-free `BoardVaultCore` library. SwiftUI
view models use `ObservableObject`/`@Published` because `@Observable` requires macOS 14. The
app still targets macOS 13. AppKit supplies folder pickers, Dock integration and Quick Look.

```
SwiftUI views → MainActor AppModel → EngineClient actor → Process / stdin / stdout
                                                            ↓
                                             native_engine.py (--json)
                                             ├─ Telethon + process_channel
                                             └─ native_organizer → existing classifier
```

`EngineClient` decodes newline-delimited Codable events into an AsyncStream, drains stdout and
stderr independently, and closes the stream only after process termination and stdout EOF.
Malformed output, missing `done`, or nonzero exit generates a UI error. Stderr is discarded to
avoid exposing sensitive third-party diagnostics. Stop sends `cancel`, waits two seconds, sends
SIGTERM, then SIGKILL after another two seconds if necessary. Quitting waits for teardown.

Python JSON mode never invokes interactive terminal prompts or implicitly loads dotenv.
`login_required` prompts identify `phone`, `code`, or `password`; `login_response` supplies one
value for the outstanding field. Commands are bounded and validated. EOF cancels. Error messages
are fixed text, not exception strings. Download events reuse existing callbacks and throttle byte
progress to ten updates/second (plus file completion). `progress.done`, `total`, and `bytes` refer
to the current file in bytes. Run `done.status` is `ok`, `cancelled`, or `error`.

Additional local operations are `config`, `scan`, `organize`, and `undo`. Scan stores a preview ID
and file signatures, then sends `plan` events in bounded batches. Organize requires `--plan-id`
and unchanged sources/destinations. Files move via exclusive durable copies before removal of
the original; a per-file journal supports undo. Undo only remaps affected state paths, preserving
new download records. Ambiguous crash states/conflicting files fail closed for manual recovery.
Native snapshots/journals are separate from legacy GUI manifests.

A state-root advisory lock prevents concurrent native operations. It cannot coordinate with
older CLI/Qt clients; close those before using shared state. Native downloads use temporary files,
expected-size checks, exclusive hard-link publication and atomic JSON state replacement.
These protections are explicitly enabled by the native adapter; existing CLI/Qt behavior remains.

Credentials are one Keychain generic-password item under `com.subkoks.boardvault.native`,
read only on an explicit Telegram action. The child receives only an allowlisted environment plus
TG_API_ID/TG_API_HASH. Credentials are never process arguments. Legacy import is an explicit
user-selected file; no automatic session or credential migration occurs at launch.

Dev mode locates `.venv/bin/python` in the repository. Release mode runs
`Contents/Resources/engine/boardvault-engine` from a PyInstaller onedir bundle; it contains its
own Python and classifier reference document. Packaging uses a separate managed Python because
the workstation Python library requires macOS 26.2. Optional host OpenSSL acceleration is omitted;
Telethon retains its supported pyaes fallback. The build verifies each bundled Mach-O's architecture,
minimum OS and non-system dylib references before ad-hoc signing and reusing the existing DMG layout.

`native/release.json` supplies the native version and build number for bundle metadata and
About & Help. Release packaging verifies archive integrity and the extracted app signature,
then writes versioned assets, checksums and a source manifest under `dist/releases/`. Native
GitHub workflows test Python and Intel Swift; the manual packaging workflow creates artifacts
without tags or release publication. See [RELEASING_NATIVE.md](RELEASING_NATIVE.md).

Publication helpers are separate from building. They verify uploaded asset digests, wait for CI,
and publish only the prepared prerelease through the authenticated GitHub CLI. Documentation and
acceptance notes can be updated after a binary build; the archive manifest retains its original
source commit. See the [focused release review](native-release-review.md) for the current scope.

`--ui-smoke` only runs when `BOARDVAULT_FIXTURE_ROOT` is explicitly provided. It bypasses normal
preferences and uses fixture files for scan/organize/undo. Window captures, logs and a JSON report
stay under that fixture root. It never performs a Telegram or Keychain operation.
