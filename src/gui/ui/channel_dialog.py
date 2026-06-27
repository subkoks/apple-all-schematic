"""Add-channel dialog: pick/enter a category and a validated @channel name."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from validation import ValidationError, validate_channel_name


class AddChannelDialog(QDialog):
    """Returns (category, channel_name) via :meth:`result_values` when accepted."""

    def __init__(self, categories: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add channel")
        self.setModal(True)
        self.setMinimumWidth(380)
        self._category = ""
        self._name = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(14)

        title = QLabel("Add a Telegram channel")
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        self._category_box = QComboBox()
        self._category_box.setEditable(True)
        self._category_box.addItems(categories or ["laptop", "mobile", "apple"])
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("channel username, e.g. schematicslaptop")
        form.addRow("Category", self._category_box)
        form.addRow("Channel", self._name_edit)
        root.addLayout(form)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #ff6b73;")
        self._error.setWordWrap(True)
        self._error.hide()
        root.addWidget(self._error)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        add = QPushButton("Add")
        add.setObjectName("Primary")
        add.clicked.connect(self._on_add)
        buttons.addWidget(cancel)
        buttons.addWidget(add)
        root.addLayout(buttons)

        self._name_edit.returnPressed.connect(self._on_add)

    def _on_add(self) -> None:
        category = self._category_box.currentText().strip().lower()
        raw = self._name_edit.text().strip().lstrip("@")
        if not category:
            self._show_error("Pick or type a category.")
            return
        try:
            name = validate_channel_name(raw)
        except ValidationError as e:
            self._show_error(f"Invalid channel: {e}")
            return
        self._category = category
        self._name = name
        self.accept()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()

    def result_values(self) -> tuple[str, str]:
        return self._category, self._name
