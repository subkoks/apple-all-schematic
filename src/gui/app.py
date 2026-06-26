"""Application entry point.

Sets up a single qasync event loop shared by Qt and Telethon's asyncio, loads the
dark theme, and shows the main window. Run with::

    PYTHONPATH=src python -m gui.app
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the project's ``src`` directory is importable so the GUI can reuse the
# existing CLI modules (tg_schematic_downloader, organize_downloads, validation)
# whether launched via ``-m gui.app`` or from a frozen bundle.
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import qasync  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.ui.main_window import MainWindow  # noqa: E402

THEME_FILE = Path(__file__).resolve().parent / "ui" / "theme.qss"


def _load_theme(app: QApplication) -> None:
    if THEME_FILE.exists():
        app.setStyleSheet(THEME_FILE.read_text())


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Apple Schematic Downloader")
    _load_theme(app)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
