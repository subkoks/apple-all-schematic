# BoardVault — User Guide

BoardVault downloads Apple device schematics and boardviews from public Telegram channels and
organizes them into a clean library. This guide covers the macOS app; the CLI is documented in the
[README](../README.md#cli).

## 1. Install

1. Open `BoardVault.dmg` and drag **BoardVault** to **Applications**.
2. First launch (unsigned app): **right-click → Open → Open**, or run
   `xattr -dr com.apple.quarantine "/Applications/BoardVault.app"`.

## 2. Get Telegram API credentials

1. Visit **<https://my.telegram.org>** and log in with your Telegram phone number.
2. Open **API development tools**, create an app (any name), and copy the **API ID** and **API Hash**.
3. In BoardVault, open **Settings → Account**, paste both, and **Save credentials**. They are stored
   locally in a `.env` file and never leave your machine.

## 3. Download

1. On the **Download** tab, tick the channels you want. Use **+ Add** to add a channel by `@name`, or
   **right-click** a channel to remove it. Your channel edits are remembered.
2. Choose a filter:
   - **Apple only** — keep just Apple-matching files (by name/caption/board number).
   - **All files** — keep every allowed file type.
3. Optional: add space-separated **Keywords**, or set a **Scan limit** for a quick test.
4. Press **Start**. The first time, you'll be prompted for your **phone number**, the **login code**
   Telegram sends you, and your **2FA password** if you use one.
5. Watch **Live progress** per channel and the **Activity** log. Press **Stop** any time — progress is
   saved, and **Resume** skips what you already have.

Files download to your **Download folder** (shown on the Download tab; change it with **Change…**, or
reveal it with **Open**).

## 4. Organize

1. On the **Organize** tab, press **Scan (dry-run)** to preview how files will be classified
   (`Apple/Computers/MacBook_Pro`, `Apple/Phones/iPhone`, brand folders, etc.).
2. Press **Organize** to move files into the library. A manifest is written so the move is reversible.
3. Press **Undo** to reverse the last organize run.
4. Browse the result in the **Organized library** panel.

## 5. Settings

- **Account** — credentials, session status, **Log out** (clears the saved Telegram session).
- **Appearance** — **System** (follows macOS), **Dark**, or **Light**.
- **Locations** — download and organized-library folders; state/session paths.
- **Behavior** — default filter, scan limit, resume, and reveal-on-complete.
- **About & Help** — quick-start, links, version.

## Troubleshooting

- **Gatekeeper blocks the app:** it's unsigned — use the right-click → Open step above.
- **Wrong login code / stuck login:** **Settings → Account → Log out**, then Start again.
- **Channel won't resolve:** confirm the exact `@name` and that the channel is public or that you've
  joined it.
