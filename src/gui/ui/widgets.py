"""Small reusable Qt widgets: cards, stat chips, per-channel progress rows."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class Card(QFrame):
    """Rounded surface container with an optional title."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout


class StatChip(QLabel):
    """Compact labelled metric, e.g. ``Downloaded 312``."""

    def __init__(self, label: str, value: object = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatChip")
        self._label = label
        self.set_value(value)

    def set_value(self, value: object) -> None:
        self.setText(f"{self._label}  {value}")


class ChannelProgress(QWidget):
    """A single channel's live status: name, progress bar, current file, counts."""

    def __init__(self, channel: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.channel = channel
        self.downloaded = 0
        self.skipped = 0
        self.errors = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 6, 0, 6)
        root.setSpacing(4)

        header = QHBoxLayout()
        self._name = QLabel(f"@{channel}")
        self._name.setStyleSheet("font-weight: 600;")
        self._counts = QLabel("idle")
        self._counts.setObjectName("Muted")
        self._counts.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self._name)
        header.addStretch(1)
        header.addWidget(self._counts)
        root.addLayout(header)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        root.addWidget(self._bar)

        self._file = QLabel("")
        self._file.setObjectName("Muted")
        self._file.setTextFormat(Qt.TextFormat.PlainText)
        root.addWidget(self._file)

    def on_event(self, ev: dict) -> None:
        kind = ev.get("type")
        if kind == "channel_start":
            self._counts.setText("scanning…")
            self._bar.setRange(0, 0)  # indeterminate until a file lands
        elif kind == "file_start":
            self._file.setText(f"↓ {ev.get('filename', '')}")
        elif kind == "file_bytes":
            total = ev.get("total") or 0
            received = ev.get("received") or 0
            if total > 0:
                self._bar.setRange(0, 100)
                self._bar.setValue(int(received / total * 100))
        elif kind == "file_done":
            self.downloaded = ev.get("count", self.downloaded + 1)
            self._bar.setRange(0, 100)
            self._bar.setValue(100)
            self._refresh_counts()
        elif kind == "file_error":
            self.errors += 1
            self._refresh_counts()
        elif kind == "channel_done":
            self.downloaded = ev.get("count", self.downloaded)
            self.skipped = ev.get("skipped", self.skipped)
            self.errors = ev.get("errors", self.errors)
            self._bar.setRange(0, 100)
            self._bar.setValue(100)
            self._file.setText("✓ done")
            self._refresh_counts()

    def _refresh_counts(self) -> None:
        self._counts.setText(f"{self.downloaded} ✓   {self.skipped} skip   {self.errors} err")
