from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ui.components.common import Card, PageHeader


class LogsPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.entries: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Logs", "Inspect app events and export diagnostics quickly."))

        card = Card("Live Logs")
        controls = QHBoxLayout()
        self.level_filter = QComboBox()
        self.level_filter.addItems(["all", "debug", "info", "warning", "error"])
        export_btn = QPushButton("Export")
        clear_btn = QPushButton("Clear")
        controls.addWidget(self.level_filter)
        controls.addWidget(export_btn)
        controls.addWidget(clear_btn)
        controls.addStretch(1)
        card.layout.addLayout(controls)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1500)
        card.layout.addWidget(self.output)
        root.addWidget(card, 1)

        self.context.log_service.log_emitted.connect(self.on_log)
        self.level_filter.currentTextChanged.connect(self.redraw)
        export_btn.clicked.connect(self.export_logs)
        clear_btn.clicked.connect(self.clear_logs)

    def on_log(self, entry: dict):
        self.entries.append(entry)
        if len(self.entries) > 5000:
            self.entries = self.entries[-5000:]

        level = self.level_filter.currentText()
        if level != "all" and entry["level"] != level:
            return
        line = f"{entry['timestamp']} | {entry['level'].upper()} | {entry['source']} | {entry['message']}"
        self.output.appendPlainText(line)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def redraw(self):
        level = self.level_filter.currentText()
        lines = []
        for e in self.entries[-1200:]:
            if level != "all" and e["level"] != level:
                continue
            lines.append(f"{e['timestamp']} | {e['level'].upper()} | {e['source']} | {e['message']}")
        self.output.setPlainText("\n".join(lines))
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export logs", "crocdrop_logs.txt", "Text Files (*.txt)")
        if path:
            self.context.log_service.export_logs(Path(path))

    def clear_logs(self):
        self.entries.clear()
        self.context.log_service.clear_logs()
        self.redraw()
