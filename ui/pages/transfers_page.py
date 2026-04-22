from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ui.components.common import Card, PageHeader


class TransfersPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Transfers", "Review active, completed, failed, and canceled sessions."))

        card = Card("Transfer History")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Dir", "Status", "Code", "Speed", "Started", "Ended", "Error"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        card.layout.addWidget(self.table)

        controls = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        retry_btn = QPushButton("Retry")
        open_btn = QPushButton("Open Folder")
        copy_btn = QPushButton("Copy Details")
        clear_btn = QPushButton("Clear History")
        controls.addWidget(refresh_btn)
        controls.addWidget(retry_btn)
        controls.addWidget(open_btn)
        controls.addWidget(copy_btn)
        controls.addWidget(clear_btn)
        controls.addStretch(1)
        card.layout.addLayout(controls)

        root.addWidget(card, 1)

        refresh_btn.clicked.connect(self.refresh)
        retry_btn.clicked.connect(self.retry_selected)
        open_btn.clicked.connect(self.open_folder)
        copy_btn.clicked.connect(self.copy_details)
        clear_btn.clicked.connect(self.clear_history)
        self.context.history_service.history_changed.connect(self.refresh)

        self.refresh()

    def refresh(self):
        records = self.context.history_service.list_records()
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            values = [r.transfer_id, r.direction, r.status, r.code_phrase, r.speed_text, r.started_at, r.ended_at, r.error_message]
            for col, val in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(val or "")))

    def _selected_transfer_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return item.text() if item else ""

    def retry_selected(self):
        tid = self._selected_transfer_id()
        if not tid:
            return
        result = self.context.transfer_service.retry(tid)
        if not result:
            QMessageBox.information(self, "Retry", "Unable to retry selected transfer")

    def open_folder(self):
        tid = self._selected_transfer_id()
        if not tid:
            return
        records = self.context.history_service.list_records()
        rec = next((r for r in records if r.transfer_id == tid), None)
        if not rec:
            return
        folder = rec.destination_folder or (str(Path(rec.source_paths[0]).parent) if rec.source_paths else "")
        if folder and Path(folder).exists():
            import os

            os.startfile(folder)

    def copy_details(self):
        tid = self._selected_transfer_id()
        if not tid:
            return
        records = self.context.history_service.list_records()
        rec = next((r for r in records if r.transfer_id == tid), None)
        if not rec:
            return
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(json.dumps(rec.to_dict(), indent=2))

    def clear_history(self):
        answer = QMessageBox.question(
            self,
            "Clear History",
            "Remove all transfer history entries?\n\nThis does not delete transferred files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.context.history_service.clear()
