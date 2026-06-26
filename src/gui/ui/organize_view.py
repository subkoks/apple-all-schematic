"""Organize tab: dry-run preview, classification report, execute/undo, file browser."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..core import organizer
from .widgets import Card, StatChip


class OrganizeView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addWidget(self._build_left(), 1)
        root.addWidget(self._build_right(), 1)

    def _build_left(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        controls = QHBoxLayout()
        self.scan_button = QPushButton("Scan (dry-run)")
        self.scan_button.setObjectName("Primary")
        self.execute_button = QPushButton("Organize files")
        self.execute_button.setEnabled(False)
        self.undo_button = QPushButton("Undo")
        self.undo_button.setObjectName("Danger")
        controls.addWidget(self.scan_button)
        controls.addWidget(self.execute_button)
        controls.addWidget(self.undo_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        stats = QHBoxLayout()
        self._stat_total = StatChip("Files")
        self._status = QLabel("Run a dry-run to preview classification.")
        self._status.setObjectName("Muted")
        stats.addWidget(self._stat_total)
        stats.addWidget(self._status, 1)
        layout.addLayout(stats)

        report_card = Card("Categories")
        self._report = QTableWidget(0, 2)
        self._report.setHorizontalHeaderLabels(["Category", "Count"])
        self._report.verticalHeader().setVisible(False)
        self._report.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._report.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._report.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        report_card.body().addWidget(self._report)
        layout.addWidget(report_card, 1)

        return col

    def _build_right(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        browser_card = Card("Organized library")
        self._model = QFileSystemModel()
        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(False)
        for column in (1, 2, 3):  # hide size/type/date, keep name
            self._tree.hideColumn(column)
        browser_card.body().addWidget(self._tree)
        self.refresh_browser()
        layout.addWidget(browser_card, 1)

        return col

    # ── Public API ──────────────────────────────────────────────────────────────

    def show_plan(self, plan: organizer.OrganizePlan) -> None:
        self._stat_total.set_value(plan.total)
        self._report.setRowCount(0)
        for category, count in plan.category_counts.items():
            row = self._report.rowCount()
            self._report.insertRow(row)
            self._report.setItem(row, 0, QTableWidgetItem(category))
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._report.setItem(row, 1, count_item)
        if plan.total:
            self._status.setText(f"{plan.total} files planned. Review, then Organize.")
            self.execute_button.setEnabled(True)
        else:
            self._status.setText("No files found in downloads to organize.")
            self.execute_button.setEnabled(False)

    def set_status(self, message: str) -> None:
        self._status.setText(message)

    def set_busy(self, busy: bool) -> None:
        self.scan_button.setEnabled(not busy)
        self.undo_button.setEnabled(not busy)
        if busy:
            self.execute_button.setEnabled(False)

    def refresh_browser(self) -> None:
        root = organizer.organized_root()
        if root.exists():
            self._model.setRootPath(str(root))
            self._tree.setRootIndex(self._model.index(str(root)))
            self._tree.setEnabled(True)
        else:
            self._tree.setEnabled(False)
