from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ui.components.common import Card, PageHeader


class ReceivePage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.current_transfer_id = ""
        self.attempted_codes: set[str] = set()
        self.pending_output_lines: list[str] = []
        self.output_flush_timer = QTimer(self)
        self.output_flush_timer.setInterval(50)
        self.output_flush_timer.timeout.connect(self.flush_output)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Receive", "Paste a code, choose destination, and monitor inbound transfer progress."))

        form = Card("Receive Setup")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Paste code phrase")
        self.dest_input = QLineEdit()
        self.dest_input.setText(self.context.settings_service.get().default_download_folder)
        self.collision = QComboBox()
        self.collision.addItems(["ask", "overwrite", "overwrite-disabled", "rename", "skip"])

        row1 = QHBoxLayout()
        paste_btn = QPushButton("Paste")
        row1.addWidget(self.code_input)
        row1.addWidget(paste_btn)

        row2 = QHBoxLayout()
        browse_btn = QPushButton("Browse")
        row2.addWidget(self.dest_input)
        row2.addWidget(browse_btn)

        action_row = QHBoxLayout()
        start_btn = QPushButton("Start Receive")
        start_btn.setObjectName("PrimaryButton")
        action_row.addWidget(start_btn)
        action_row.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Progress: %p%")

        form.layout.addWidget(QLabel("Code"))
        form.layout.addLayout(row1)
        form.layout.addWidget(QLabel("Destination"))
        form.layout.addLayout(row2)
        form.layout.addWidget(QLabel("Collision Handling"))
        form.layout.addWidget(self.collision)
        form.layout.addLayout(action_row)
        form.layout.addWidget(self.progress)

        logs = Card("Live Output")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1200)
        logs.layout.addWidget(self.output)

        root.addWidget(form)
        root.addWidget(logs, 1)

        browse_btn.clicked.connect(self.browse_destination)
        start_btn.clicked.connect(self.start_receive)
        paste_btn.clicked.connect(self.paste_code)

        self.context.transfer_service.transfer_output.connect(self.on_transfer_output)
        self.context.transfer_service.transfer_updated.connect(self.on_transfer_updated)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)

    def paste_code(self):
        from PySide6.QtGui import QGuiApplication

        self.code_input.setText(QGuiApplication.clipboard().text().strip())

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose destination", self.dest_input.text())
        if folder:
            self.dest_input.setText(folder)

    def start_receive(self):
        code = self.code_input.text().strip()
        destination = self.dest_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Missing code", "Enter a croc code phrase")
            return
        if not destination:
            QMessageBox.warning(self, "Missing destination", "Choose destination folder")
            return
        if code in self.attempted_codes:
            answer = QMessageBox.question(
                self,
                "Reuse Code?",
                "This code was already used in a previous attempt.\n"
                "Croc codes are usually one-session. Reusing often fails with 'room not ready'.\n\n"
                "Try anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        strategy = self.collision.currentText()
        overwrite = strategy == "overwrite"
        if strategy in {"ask", "rename", "skip"}:
            self.output.appendPlainText(
                f"Note: '{strategy}' is best-effort in croc CLI mode. Use 'overwrite' if destination already has the same filename."
            )

        record = self.context.transfer_service.start_receive(code_phrase=code, destination=destination, overwrite=overwrite)
        self.attempted_codes.add(code)
        self.current_transfer_id = record.transfer_id
        self.pending_output_lines.clear()
        self.output.clear()
        self.progress.setValue(0)
        self.output.appendPlainText(f"Started receive {record.transfer_id}")

    def on_transfer_output(self, transfer_id: str, line: str):
        if transfer_id != self.current_transfer_id:
            return
        self.pending_output_lines.extend(part for part in line.splitlines() if part)
        if self.pending_output_lines and not self.output_flush_timer.isActive():
            self.output_flush_timer.start()

    def on_transfer_finished(self, transfer_id: str, status: str):
        if transfer_id != self.current_transfer_id:
            return
        if status == "completed":
            self.progress.setValue(100)
            return
        if status != "failed":
            return
        records = self.context.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record:
            return
        joined = "\n".join(record.output_excerpt[-80:]).lower()
        if "no files transferred" in joined:
            self.output.appendPlainText(
                "Hint: Receiver connected but wrote no file. Choose an empty folder or collision='overwrite', then ask sender for a NEW code."
            )
        if "room (secure channel) not ready" in joined or "peer disconnected" in joined:
            self.output.appendPlainText(
                "Hint: This code/session is no longer active. Start a fresh send and use the newly generated code."
            )

    def on_transfer_updated(self, transfer_id: str):
        if transfer_id != self.current_transfer_id:
            return
        records = self.context.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record:
            return
        self.progress.setValue(max(0, min(100, int(record.bytes_done))))

    def flush_output(self):
        if not self.pending_output_lines:
            self.output_flush_timer.stop()
            return
        chunk = "\n".join(self.pending_output_lines)
        self.pending_output_lines.clear()
        self.output.appendPlainText(chunk)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
