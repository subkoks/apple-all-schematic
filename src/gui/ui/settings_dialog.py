"""Settings dialog: Telegram API credentials and read-only paths/tuning."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import config


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel("Telegram API credentials")
        title.setObjectName("SectionTitle")
        hint = QLabel(
            "Create an app at <b>my.telegram.org</b> to get these. They are stored in "
            "your local <code>.env</code> file and never leave this machine."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(hint)

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
        root.addLayout(form)

        paths = QLabel(
            f"<b>Downloads:</b> {config.DOWNLOAD_DIR}<br>"
            f"<b>State:</b> {config.STATE_FILE}<br>"
            f"<b>Session:</b> {config.SESSION_FILE}"
        )
        paths.setObjectName("Muted")
        paths.setWordWrap(True)
        root.addWidget(paths)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #ff8a93;")
        self._error.hide()
        root.addWidget(self._error)

        save = QPushButton("Save")
        save.setObjectName("Primary")
        save.clicked.connect(self._on_save)
        root.addWidget(save)

    def _on_save(self) -> None:
        api_id = self._api_id.text().strip()
        api_hash = self._api_hash.text().strip()
        if not api_id.isdigit():
            self._show_error("API ID must be a number.")
            return
        if len(api_hash) < 8:
            self._show_error("API Hash looks too short.")
            return
        config.save_credentials(api_id, api_hash)
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()
