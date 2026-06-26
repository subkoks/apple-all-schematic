"""Download tab: channel selection, filters, run controls, live progress + log."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.config import AppConfig
from .widgets import Card, ChannelProgress, StatChip


class DownloadView(QWidget):
    """Emits intent via callbacks set by MainWindow; renders live progress."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._rows: dict[str, ChannelProgress] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addWidget(self._build_left(), 0)
        root.addWidget(self._build_right(), 1)

    # ── Left column: controls ───────────────────────────────────────────────────

    def _build_left(self) -> QWidget:
        col = QWidget()
        col.setFixedWidth(320)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Channels card
        channels_card = Card("Channels")
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        for category, names in self.config.channels.items():
            top = QTreeWidgetItem([f"{category}  ({len(names)})"])
            top.setFlags(
                top.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable
            )
            top.setCheckState(0, Qt.CheckState.Checked)
            for name in names:
                child = QTreeWidgetItem([name])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, name)
                top.addChild(child)
            self._tree.addTopLevelItem(top)
        self._tree.expandAll()
        channels_card.body().addWidget(self._tree)
        layout.addWidget(channels_card, 1)

        # Filters card
        filters_card = Card("Filters")
        mode_row = QHBoxLayout()
        self._apple_radio = QRadioButton("Apple only")
        self._all_radio = QRadioButton("All files")
        self._apple_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._apple_radio)
        group.addButton(self._all_radio)
        mode_row.addWidget(self._apple_radio)
        mode_row.addWidget(self._all_radio)
        filters_card.body().addLayout(mode_row)

        self._resume = QCheckBox("Resume (skip already-downloaded)")
        self._resume.setChecked(True)
        filters_card.body().addWidget(self._resume)

        kw_row = QHBoxLayout()
        kw_row.addWidget(QLabel("Keywords"))
        self._keywords = QLineEdit()
        self._keywords.setPlaceholderText("optional, space-separated")
        kw_row.addWidget(self._keywords, 1)
        filters_card.body().addLayout(kw_row)

        limit_row = QHBoxLayout()
        limit_row.addWidget(QLabel("Scan limit / channel"))
        self._limit = QSpinBox()
        self._limit.setRange(0, 1_000_000)
        self._limit.setValue(0)
        self._limit.setSpecialValueText("All")
        limit_row.addStretch(1)
        limit_row.addWidget(self._limit)
        filters_card.body().addLayout(limit_row)
        layout.addWidget(filters_card)

        # Run controls
        controls = QHBoxLayout()
        self.start_button = QPushButton("▶  Start")
        self.start_button.setObjectName("Primary")
        self.stop_button = QPushButton("■  Stop")
        self.stop_button.setObjectName("Danger")
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button, 1)
        controls.addWidget(self.stop_button, 1)
        layout.addLayout(controls)

        return col

    # ── Right column: live status ───────────────────────────────────────────────

    def _build_right(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        stats_row = QHBoxLayout()
        self._stat_downloaded = StatChip("Downloaded")
        self._stat_skipped = StatChip("Skipped")
        self._stat_errors = StatChip("Errors")
        for chip in (self._stat_downloaded, self._stat_skipped, self._stat_errors):
            stats_row.addWidget(chip)
        stats_row.addStretch(1)
        layout.addLayout(stats_row)

        progress_card = Card("Live progress")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._rows_host = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        self._rows_layout.addStretch(1)
        scroll.setWidget(self._rows_host)
        progress_card.body().addWidget(scroll)
        layout.addWidget(progress_card, 2)

        log_card = Card("Activity")
        self._log = QPlainTextEdit()
        self._log.setObjectName("LogView")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        log_card.body().addWidget(self._log)
        layout.addWidget(log_card, 1)

        return col

    # ── Public API used by MainWindow ───────────────────────────────────────────

    def selected_channels(self) -> list[str]:
        names: list[str] = []
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    names.append(child.data(0, Qt.ItemDataRole.UserRole))
        return names

    def run_options(self) -> dict:
        kw_text = self._keywords.text().strip()
        keywords = kw_text.split() if kw_text else None
        limit = self._limit.value() or None
        return {
            "apple_only": self._apple_radio.isChecked(),
            "keyword_filter": keywords,
            "limit": limit,
            "resume": self._resume.isChecked(),
        }

    def prepare_run(self, channels: list[str]) -> None:
        """Reset progress rows for the channels about to be scraped."""
        self._totals = {"downloaded": 0, "skipped": 0, "errors": 0}
        for row in self._rows.values():
            row.setParent(None)
        self._rows.clear()
        for channel in channels:
            row = ChannelProgress(channel)
            self._rows[channel] = row
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._update_stats()

    def set_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self._tree.setEnabled(not running)

    def append_log(self, message: str) -> None:
        self._log.appendPlainText(message)

    def on_event(self, ev: dict) -> None:
        channel = ev.get("channel")
        row = self._rows.get(channel)
        if row is not None:
            row.on_event(ev)
        kind = ev.get("type")
        if kind == "file_done":
            self._log.appendPlainText(f"@{channel}  ↓ {ev.get('filename', '')}")
        elif kind == "file_error":
            self._log.appendPlainText(
                f"@{channel}  ✗ {ev.get('filename', '')}: {ev.get('error', '')}"
            )
        elif kind == "resolve_error":
            self._log.appendPlainText(f"@{channel}  ✗ could not resolve: {ev.get('error', '')}")
        elif kind == "channel_done":
            self._log.appendPlainText(
                f"@{channel}  done — {ev.get('count', 0)} downloaded, "
                f"{ev.get('skipped', 0)} skipped, {ev.get('errors', 0)} errors"
            )
        self._recompute_totals()

    def _recompute_totals(self) -> None:
        downloaded = sum(r.downloaded for r in self._rows.values())
        skipped = sum(r.skipped for r in self._rows.values())
        errors = sum(r.errors for r in self._rows.values())
        self._stat_downloaded.set_value(downloaded)
        self._stat_skipped.set_value(skipped)
        self._stat_errors.set_value(errors)

    def _update_stats(self) -> None:
        self._stat_downloaded.set_value(0)
        self._stat_skipped.set_value(0)
        self._stat_errors.set_value(0)
