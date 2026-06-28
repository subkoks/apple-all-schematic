"""Application entry point.

Boot order matters: QApplication and its applicationName must exist before we read
QStandardPaths (settings/data dirs), and the data-root override must run before the
window touches any path. So: app -> settings -> paths.apply -> theme -> window, all on a
single qasync event loop shared by Qt and Telethon.

    PYTHONPATH=src python -m gui.app
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the project's ``src`` importable so the GUI can reuse the CLI modules whether
# launched via ``-m gui.app`` or from a frozen bundle.
_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import qasync  # noqa: E402
from PySide6.QtGui import QFontDatabase, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.core import paths  # noqa: E402
from gui.core.settings import APP_NAME, Settings  # noqa: E402
from gui.ui.main_window import MainWindow  # noqa: E402
from gui.ui.theme import ThemeManager  # noqa: E402

_ICON_FILE = Path(__file__).resolve().parent / "resources" / "app.icns"


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("subkoks")

    # Use the real OS UI font (avoids a missing -apple-system family lookup).
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    if _ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(_ICON_FILE)))

    # Migrate pre-rebrand data first so the loaded settings reflect the old install.
    paths.migrate_legacy()
    settings = Settings.load()
    paths.apply(settings)

    theme = ThemeManager(app, settings.theme)
    theme.apply()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow(settings=settings, theme=theme)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
