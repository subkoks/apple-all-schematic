"""Main window: sidebar navigation + Download / Organize views, wired to controllers."""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QSize, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import organizer, paths
from ..core.auth import AuthError
from ..core.backend import DownloadController
from ..core.config import get_credentials, load_config
from ..core.settings import Settings
from .download_view import DownloadView
from .icons import nav_icon
from .login_dialog import LoginCancelled, LoginDialog
from .organize_view import OrganizeView
from .settings_dialog import SettingsDialog
from .theme import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, theme: ThemeManager) -> None:
        super().__init__()
        self.setWindowTitle("BoardVault")
        self.resize(1080, 720)

        self.settings = settings
        self.theme = theme
        self.config = load_config()
        self.controller = DownloadController()

        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self.download_view = DownloadView(self.config, self.settings)
        self.organize_view = OrganizeView()
        self._stack.addWidget(self.download_view)
        self._stack.addWidget(self.organize_view)
        root.addWidget(self._stack, 1)

        self._wire_download()
        self._wire_organize()

    # ── Sidebar ─────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(210)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(6)

        title = QLabel("BoardVault")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Apple board schematics")
        subtitle.setObjectName("AppSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        nav_icon_size = QSize(18, 18)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for index, (label, glyph) in enumerate(
            (("Download", "download"), ("Organize", "organize"))
        ):
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.setIcon(nav_icon(glyph))
            btn.setIconSize(nav_icon_size)
            btn.clicked.connect(lambda _=False, i=index: self._stack.setCurrentIndex(i))
            self._nav_group.addButton(btn, index)
            layout.addWidget(btn)

        layout.addStretch(1)

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("NavButton")
        settings_btn.setIcon(nav_icon("settings"))
        settings_btn.setIconSize(nav_icon_size)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)
        return bar

    # ── Download wiring ─────────────────────────────────────────────────────────

    def _wire_download(self) -> None:
        self.download_view.start_button.clicked.connect(
            lambda: asyncio.ensure_future(self._on_start())
        )
        self.download_view.stop_button.clicked.connect(self.controller.stop)

        self.controller.event.connect(self.download_view.on_event)
        self.controller.log.connect(self.download_view.append_log)
        self.controller.running_changed.connect(self.download_view.set_running)
        self.controller.failed.connect(self._on_run_failed)
        self.controller.finished.connect(self._on_run_finished)

    async def _on_start(self) -> None:
        if self.controller.is_running:
            return
        if not get_credentials().is_complete:
            self._open_settings()
            if not get_credentials().is_complete:
                return

        channels = self.download_view.selected_channels()
        if not channels:
            self._warn("No channels selected", "Select at least one channel to download.")
            return

        dialog = LoginDialog(self)
        try:
            self.download_view.append_log("Connecting to Telegram…")
            await self.controller.ensure_ready(dialog)
        except LoginCancelled:
            self.download_view.append_log("Login cancelled.")
            return
        except AuthError as e:
            dialog.show_error(str(e))
            self._warn("Login failed", str(e))
            return
        finally:
            dialog.close()

        self.download_view.append_log(f"Starting {len(channels)} channel(s)…")
        self.download_view.prepare_run(channels)
        self.controller.start(channels, **self.download_view.run_options())

    def _on_run_failed(self, message: str) -> None:
        self.download_view.append_log(f"Error: {message}")
        self._warn("Download error", message)

    def _on_run_finished(self, _totals: dict) -> None:
        if self.settings.reveal_on_complete:
            target = paths.download_dir()
            target.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # ── Organize wiring ─────────────────────────────────────────────────────────

    def _wire_organize(self) -> None:
        self.organize_view.scan_button.clicked.connect(
            lambda: asyncio.ensure_future(self._on_scan())
        )
        self.organize_view.execute_button.clicked.connect(
            lambda: asyncio.ensure_future(self._on_execute())
        )
        self.organize_view.undo_button.clicked.connect(
            lambda: asyncio.ensure_future(self._on_undo())
        )

    async def _on_scan(self) -> None:
        self.organize_view.set_busy(True)
        self.organize_view.set_status("Scanning downloads…")
        try:
            plan = await organizer.build_plan()
            self._plan = plan
            self.organize_view.show_plan(plan)
        except FileNotFoundError as e:
            self.organize_view.set_status(str(e))
            self._warn("Cannot scan", str(e))
        except Exception as e:  # noqa: BLE001 — surface unexpected scan failures
            self.organize_view.set_status(f"Scan failed: {e}")
            self._warn("Scan failed", str(e))
        finally:
            self.organize_view.set_busy(False)

    async def _on_execute(self) -> None:
        plan = getattr(self, "_plan", None)
        if not plan or not plan.moves:
            return
        confirm = QMessageBox.question(
            self,
            "Organize files",
            f"Move {plan.total} files into the organized library?\n"
            "This writes an undo manifest so it can be reversed.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.organize_view.set_busy(True)
        self.organize_view.set_status("Moving files…")
        try:
            result = await organizer.execute(plan.moves)
            self.organize_view.set_status(
                f"Organized {result['moved']} files. "
                f"{result['state_updated']} state entries updated."
            )
            self.organize_view.refresh_browser()
            self._plan = None
        except Exception as e:  # noqa: BLE001
            self.organize_view.set_status(f"Organize failed: {e}")
            self._warn("Organize failed", str(e))
        finally:
            self.organize_view.set_busy(False)

    async def _on_undo(self) -> None:
        if not organizer.manifest_exists():
            self._warn("Nothing to undo", "No organize manifest was found.")
            return
        confirm = QMessageBox.question(
            self, "Undo organization", "Reverse the last organize run using the manifest?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.organize_view.set_busy(True)
        self.organize_view.set_status("Undoing…")
        try:
            result = await organizer.undo()
            self.organize_view.set_status(f"Restored {result['restored']} files.")
            self.organize_view.refresh_browser()
        except Exception as e:  # noqa: BLE001
            self.organize_view.set_status(f"Undo failed: {e}")
            self._warn("Undo failed", str(e))
        finally:
            self.organize_view.set_busy(False)

    # ── Misc ────────────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        SettingsDialog(self.settings, self.theme, self).exec()
        # Reflect any location/channel changes made in the dialog.
        self.download_view.refresh_location()
        self.download_view.reload_channels()
        self.organize_view.refresh_browser()

    def _warn(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt signature
        asyncio.ensure_future(self.controller.shutdown())
        super().closeEvent(event)
