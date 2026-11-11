# BoardVault — Native macOS guide

## Install and launch

The native app requires an Intel Mac and macOS 13 or later. Open the native DMG, or unzip the
native ZIP from [GitHub releases](https://github.com/subkoks/apple-all-schematic/releases),
and drag BoardVault.app into Applications. Choose the asset ending in `macos-x86_64.dmg` or
`macos-x86_64.zip`; the older `BoardVault.dmg` belongs to the Qt app. The Qt app has the same displayed name;
keep the apps in separate folders if retaining both.

This free build is ad-hoc signed, without Apple notarization. If macOS blocks a downloaded app,
open System Settings → Privacy & Security after attempting to launch it and use **Open Anyway**
for the trusted BoardVault download. Follow the system confirmation prompts. Do not disable
Gatekeeper globally. Verify the downloaded asset with its accompanying `SHA256SUMS`.
See [Apple's app security instructions](https://support.apple.com/en-us/102445) for the current
system prompts.

## Connect to Telegram

Get a free API ID and API hash at <https://my.telegram.org> → API development tools. In
Settings → Account, enter them and choose **Save to Keychain**. Choose **Log in**, then respond
to the phone, login-code, and optional two-step-password sheets. These responses are never logged.
Saved API credentials are read only for an explicit login, download, or logout operation.

**Import legacy .env…** imports the file you select into Keychain. There is no automatic
credential or session import. Log out invalidates the shared Telegram session after confirmation;
it retains the API credentials in Keychain.

## Find and download files

1. Tick the channels to scan. **+** adds a username; each channel's **…** menu moves it up/down
   or removes it. Order controls download priority. Public subscriber counts are approximate;
   use the refresh button to update them when available.
2. Enter search terms at the top. **Search options** chooses Any word for broader results,
   All words for narrower results, or Exact phrase for words in sequence. Choose filename,
   caption, or both, and the file formats to include. At least one format must remain selected.
3. **Apple only** restricts files to Apple-matching names/captions; **All files** removes this
   restriction. Searching a board number remains precise across hyphens, underscores, and spaces.
   A processor query needs that processor in the filename or caption.
4. Leave **Message limit** at 0 to scan all channel messages; set a smaller value for a quick
   check. **Resume previous downloads** skips matching files already recorded in state.
5. **Start** or **⌘R** begins. **Stop** or **⌘.** cancels. Each row shows channel, file/status,
   progress, new files, skipped files, and errors. Speed covers transferred bytes over elapsed
   time; ETA is for the current file. Expand **Activity log** below Settings when needed.

Archives often contain schematics or boardviews, so include Archives when looking for those
documents. File filters inspect extensions, not archive contents. More restrictive options can
produce no results even in a large channel. No channel is guaranteed to hold a specific board.

## Organize and browse

Choose **Scan (dry-run)** in Organize, review the file/category/destination table, then
**Organize**. If files changed after the scan, scan again. **Undo last batch** reverses the latest
native organization while preserving newer download records. Conflicting files are left for
manual recovery instead of being overwritten.

Library groups files by product or brand. Search uses all whole words in filenames. Select a
file for Quick Look (Space), Open, or Reveal in Finder. Refresh after external folder changes.

## Settings and stored data

Settings offers download/library folder pickers, appearance, reveal-on-completion, and opt-in
notifications. **⌘,** opens Settings. About & Help shows the candidate version and build number.

- State/session: `~/Library/Application Support/subkoks/BoardVault/`
- Downloads: `~/Downloads/BoardVault/` by default.
- Library: `organized/` under the state folder by default.
- API credentials: Keychain; preferences are separate from the Qt app's preferences.

Close the Qt app and CLI before native operations against shared state/session. Native and Qt
organization histories are separate. Files are never automatically copied between installations.

## If something fails

- Check Search options, Apple/all filtering, resume, and the message limit for missing results.
- For unavailable channels, check the exact username and whether your account has access.
- For login problems, check your API credentials and follow the current in-app prompt. Log out
  only when you intend to invalidate the shared session.
- If the engine cannot run, reinstall the complete app bundle; keep its embedded Resources.
- Report issues with the app version/build, macOS version, and reproduction steps. Omit API
  hashes, phone numbers, login codes, session files, and private document contents.
