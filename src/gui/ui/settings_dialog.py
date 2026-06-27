"""Tabbed settings: Account · Appearance · Locations · Behavior."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import config, paths
from ..core.settings import Settings
from .theme import ThemeManager


class SettingsDialog(QDialog):
    def __init__(
        self, settings: Settings, theme: ThemeManager, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.theme = theme
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(520, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        tabs = QTabWidget()
        tabs.addTab(self._account_tab(), "Account")
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._locations_tab(), "Locations")
        tabs.addTab(self._behavior_tab(), "Behavior")
        root.addWidget(tabs)

        close = QPushButton("Done")
        close.setObjectName("Primary")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        root.addLayout(row)

    # ── Account ─────────────────────────────────────────────────────────────────

    def _account_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel(
            "Create an app at <b>my.telegram.org</b> to get these. Stored in your local "
            "<code>.env</code> file; never uploaded."
        )
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        layout.addWidget(hint)

        creds = config.get_credentials()
        form = QFormLayout()
        form.setSpacing(10)
        self._api_id = QLineEdit(creds.api_id or "")
        self._api_id.setPlaceholderText("e.g. 1234567")
        self._api_hash = QLineEdit(creds.api_hash or "")
        self._api_hash.setPlaceholderText("32-character hash")
        self._api_hash.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API ID", self._api_id)
        form.addRow("API Hash", self._api_hash)
        layout.addLayout(form)

        self._account_status = QLabel()
        self._account_status.setObjectName("Muted")
        layout.addWidget(self._account_status)
        self._refresh_account_status()

        buttons = QHBoxLayout()
        save = QPushButton("Save credentials")
        save.setObjectName("Primary")
        save.clicked.connect(self._on_save_credentials)
        logout = QPushButton("Log out")
        logout.setObjectName("Danger")
        logout.clicked.connect(self._on_logout)
        buttons.addWidget(save)
        buttons.addWidget(logout)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._account_error = QLabel("")
        self._account_error.setStyleSheet("color: #ff6b73;")
        self._account_error.hide()
        layout.addWidget(self._account_error)
        layout.addStretch(1)
        return w

    def _refresh_account_status(self) -> None:
        signed_in = paths.session_file().with_suffix(".session").exists() or any(
            paths.session_file().parent.glob(paths.session_file().name + "*")
        )
        self._account_status.setText(
            "Session: signed in" if signed_in else "Session: not signed in"
        )

    def _on_save_credentials(self) -> None:
        api_id = self._api_id.text().strip()
        api_hash = self._api_hash.text().strip()
        if not api_id.isdigit():
            self._show_account_error("API ID must be a number.")
            return
        if len(api_hash) < 8:
            self._show_account_error("API Hash looks too short.")
            return
        config.save_credentials(api_id, api_hash)
        self._account_error.hide()
        self._account_status.setText("Credentials saved.")

    def _on_logout(self) -> None:
        removed = 0
        session = paths.session_file()
        for f in session.parent.glob(session.name + "*"):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
        self._account_status.setText(
            f"Logged out ({removed} session file(s) removed)."
            if removed
            else "No session to remove."
        )

    def _show_account_error(self, message: str) -> None:
        self._account_error.setText(message)
        self._account_error.show()

    # ── Appearance ──────────────────────────────────────────────────────────────

    def _appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Theme"))
        self._theme_group = QButtonGroup(self)
        for key, label in (("system", "System (automatic)"), ("dark", "Dark"), ("light", "Light")):
            radio = QRadioButton(label)
            radio.setChecked(self.settings.theme == key)
            radio.toggled.connect(lambda on, k=key: self._on_theme(k) if on else None)
            self._theme_group.addButton(radio)
            layout.addWidget(radio)

        note = QLabel("System follows your macOS appearance and switches automatically.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return w

    def _on_theme(self, key: str) -> None:
        self.settings.theme = key
        self.settings.save()
        self.theme.set_mode(key)

    # ── Locations ───────────────────────────────────────────────────────────────

    def _locations_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._download_label = QLabel()
        layout.addLayout(
            self._folder_row("Download folder", self._download_label, self._change_download)
        )
        self._organized_label = QLabel()
        layout.addLayout(
            self._folder_row("Organized library", self._organized_label, self._change_organized)
        )

        paths_info = QLabel(
            f"<b>State:</b> {paths.state_file()}<br><b>Session:</b> {paths.session_file()}"
        )
        paths_info.setObjectName("Muted")
        paths_info.setWordWrap(True)
        paths_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(paths_info)
        layout.addStretch(1)
        self._refresh_location_labels()
        return w

    def _folder_row(self, title: str, label: QLabel, on_change) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        box.addWidget(QLabel(title))
        label.setObjectName("Muted")
        label.setWordWrap(True)
        box.addWidget(label)
        buttons = QHBoxLayout()
        change = QPushButton("Change…")
        change.clicked.connect(on_change)
        box.addLayout(buttons)
        buttons.addWidget(change)
        buttons.addStretch(1)
        return box

    def _refresh_location_labels(self) -> None:
        self._download_label.setText(str(paths.download_dir()))
        self._organized_label.setText(str(paths.organized_dir()))

    def _pick_dir(self, start) -> str:
        return QFileDialog.getExistingDirectory(
            self,
            "Choose folder",
            str(start),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontUseNativeDialog,
        )

    def _change_download(self) -> None:
        chosen = self._pick_dir(paths.download_dir())
        if not chosen:
            return
        paths.set_download_dir(chosen)
        self.settings.download_dir = chosen
        self.settings.save()
        self._refresh_location_labels()

    def _change_organized(self) -> None:
        chosen = self._pick_dir(paths.organized_dir())
        if not chosen:
            return
        paths.set_organized_dir(chosen)
        self.settings.organized_dir = chosen
        self.settings.save()
        self._refresh_location_labels()

    # ── Behavior ────────────────────────────────────────────────────────────────

    def _behavior_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._default_mode = QComboBox()
        self._default_mode.addItems(["Apple only", "All files"])
        self._default_mode.setCurrentIndex(0 if self.settings.default_apple_only else 1)
        self._default_mode.currentIndexChanged.connect(self._save_behavior)

        self._default_resume = QCheckBox("Resume by default (skip already-downloaded)")
        self._default_resume.setChecked(self.settings.default_resume)
        self._default_resume.toggled.connect(self._save_behavior)

        self._reveal = QCheckBox("Reveal download folder when a run finishes")
        self._reveal.setChecked(self.settings.reveal_on_complete)
        self._reveal.toggled.connect(self._save_behavior)

        self._default_limit = QSpinBox()
        self._default_limit.setRange(0, 1_000_000)
        self._default_limit.setValue(self.settings.default_limit)
        self._default_limit.setSpecialValueText("All")
        self._default_limit.valueChanged.connect(self._save_behavior)

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Default filter", self._default_mode)
        form.addRow("Default scan limit", self._default_limit)
        layout.addLayout(form)
        layout.addWidget(self._default_resume)
        layout.addWidget(self._reveal)

        note = QLabel("These pre-fill the Download tab. Restart or reopen the tab to see changes.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return w

    def _save_behavior(self) -> None:
        self.settings.default_apple_only = self._default_mode.currentIndex() == 0
        self.settings.default_resume = self._default_resume.isChecked()
        self.settings.reveal_on_complete = self._reveal.isChecked()
        self.settings.default_limit = self._default_limit.value()
        self.settings.save()
