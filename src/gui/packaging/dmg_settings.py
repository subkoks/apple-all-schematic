"""dmgbuild settings — drag-to-Applications installer layout.

Invoked by scripts/build_dmg.sh:

    dmgbuild -s src/gui/packaging/dmg_settings.py \
        -D app="dist/Apple Schematic Downloader.app" \
        "Apple Schematic Downloader" "dist/Apple Schematic Downloader.dmg"

``defines`` is injected by dmgbuild from the -D flags.
"""

import os.path

# -D app=… (path to the built .app)
application = defines.get("app", "dist/Apple Schematic Downloader.app")  # noqa: F821
appname = os.path.basename(application)

# Contents of the disk image: the app plus a symlink to /Applications.
files = [application]
symlinks = {"Applications": "/Applications"}

# Window + icon layout.
icon_size = 128
window_rect = ((200, 200), (640, 360))
default_view = "icon-view"
icon_locations = {
    appname: (160, 170),
    "Applications": (480, 170),
}

# Use the app's own icon as the volume badge if present.
_icns = os.path.join(os.path.dirname(application), "..", "src", "gui", "resources", "app.icns")
if os.path.exists(_icns):
    badge_icon = _icns

format = "UDZO"  # compressed
