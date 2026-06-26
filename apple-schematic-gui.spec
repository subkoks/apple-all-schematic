# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds the desktop app.

macOS:    pyinstaller apple-schematic-gui.spec        ->  dist/Apple Schematic Downloader.app
Windows:  pyinstaller apple-schematic-gui.spec        ->  dist/Apple Schematic Downloader/...

The GUI reuses the sibling CLI modules under ``src/``, so that directory is added to
the analysis path and the theme/config data files are bundled.
"""

from pathlib import Path

PROJECT_DIR = Path(SPECPATH)
SRC = PROJECT_DIR / "src"

datas = [
    (str(SRC / "gui" / "ui" / "theme.qss"), "gui/ui"),
    (str(PROJECT_DIR / "args" / "config.json"), "args"),
    (str(PROJECT_DIR / "context" / "APPLE_PRODUCT_REFERENCE.md"), "context"),
]

icon_icns = PROJECT_DIR / "src" / "gui" / "resources" / "app.icns"
icon_path = str(icon_icns) if icon_icns.exists() else None

a = Analysis(
    [str(SRC / "gui" / "app.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=["tg_schematic_downloader", "organize_downloads", "validation"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="apple-schematic-gui",
    console=False,
    disable_windowed_traceback=False,
    icon=icon_path,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="apple-schematic-gui",
)
app = BUNDLE(
    coll,
    name="Apple Schematic Downloader.app",
    icon=icon_path,
    bundle_identifier="com.subkoks.apple-all-schematic",
)
