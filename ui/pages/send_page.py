from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ui.components.common import Card, DropList, PageHeader


class SendPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.current_transfer_id = ""
        self.pending_output_lines: list[str] = []
        self.output_flush_timer = QTimer(self)
        self.output_flush_timer.setInterval(50)
        self.output_flush_timer.timeout.connect(self.flush_output)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Send", "Drag files/folders, share code, and stream transfer output in real time."))

        picker = Card("Files and Folders")
        self.drop = DropList()
        picker.layout.addWidget(self.drop)

        actions = QHBoxLayout()
        btn_file = QPushButton("Add Files")
        btn_folder = QPushButton("Add Folder")
        btn_remove = QPushButton("Remove Selected")
        actions.addWidget(btn_file)
        actions.addWidget(btn_folder)
        actions.addWidget(btn_remove)
        actions.addStretch(1)
        picker.layout.addLayout(actions)

        code_card = Card("Generated Code")
        self.code = QLineEdit()
        self.code.setReadOnly(True)
        self.code.setPlaceholderText("Code phrase will appear after start")
        self.next_code = QLineEdit()
        self.next_code.setReadOnly(True)
        self.next_code.setPlaceholderText("Next 30-min session code will appear after start")
        self.next_code_expiry = QLabel("")
        self.next_code_expiry.setProperty("role", "muted")
        code_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Send")
        self.start_btn.setObjectName("PrimaryButton")
        copy_btn = QPushButton("Copy Code")
        copy_next_btn = QPushButton("Copy Next Code")
        code_row.addWidget(self.start_btn)
        code_row.addWidget(copy_btn)
        code_row.addWidget(copy_next_btn)
        code_row.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Progress: %p%")
        code_card.layout.addWidget(self.code)
        code_card.layout.addWidget(self.next_code)
        code_card.layout.addWidget(self.next_code_expiry)
        code_card.layout.addLayout(code_row)
        code_card.layout.addWidget(self.progress)

        runtime = Card("Live Output")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1200)
        runtime.layout.addWidget(self.output)

        root.addWidget(picker)
        root.addWidget(code_card)
        root.addWidget(runtime, 1)

        btn_file.clicked.connect(self.pick_files)
        btn_folder.clicked.connect(self.pick_folder)
        btn_remove.clicked.connect(self.drop.remove_selected)
        self.start_btn.clicked.connect(self.start_send)
        copy_btn.clicked.connect(self.copy_code)
        copy_next_btn.clicked.connect(self.copy_next_code)

        self.context.transfer_service.transfer_output.connect(self.on_transfer_output)
        self.context.transfer_service.transfer_updated.connect(self.on_transfer_updated)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)
        self.context.transfer_service.next_code_ready.connect(self.on_next_code_ready)

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        for file in files:
            self.drop.add_path(file)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.drop.add_path(folder)

    def start_send(self):
        paths = self.drop.paths()
        if not paths:
            QMessageBox.warning(self, "No files", "Add at least one file or folder")
            return
        record = self.context.transfer_service.start_send(paths)
        self.current_transfer_id = record.transfer_id
        self.pending_output_lines.clear()
        self.output.clear()
        self.progress.setValue(0)
        self.next_code.clear()
        self.next_code_expiry.clear()
        self.output.appendPlainText(f"Started transfer {record.transfer_id}")

    def copy_code(self):
        if not self.code.text().strip():
            return
        QGuiApplication.clipboard().setText(self.code.text().strip())

    def copy_next_code(self):
        if not self.next_code.text().strip():
            return
        QGuiApplication.clipboard().setText(self.next_code.text().strip())

    def on_transfer_output(self, transfer_id: str, line: str):
        if transfer_id != self.current_transfer_id:
            return
        self.pending_output_lines.extend(part for part in line.splitlines() if part)
        if self.pending_output_lines and not self.output_flush_timer.isActive():
            self.output_flush_timer.start()

    def on_transfer_updated(self, transfer_id: str):
        if transfer_id != self.current_transfer_id:
            return
        records = self.context.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record:
            return
        if record.code_phrase:
            self.code.setText(record.code_phrase)
        self.progress.setValue(max(0, min(100, int(record.bytes_done))))

    def flush_output(self):
        if not self.pending_output_lines:
            self.output_flush_timer.stop()
            return
        chunk = "\n".join(self.pending_output_lines)
        self.pending_output_lines.clear()
        self.output.appendPlainText(chunk)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def on_transfer_finished(self, transfer_id: str, status: str):
        if transfer_id != self.current_transfer_id:
            return
        if status == "completed":
            self.progress.setValue(100)

    def on_next_code_ready(self, transfer_id: str, code_phrase: str, expires_at_iso: str):
        if transfer_id != self.current_transfer_id:
            return
        self.next_code.setText(code_phrase)
        self.next_code_expiry.setText(f"Next code expires at: {expires_at_iso} (UTC)")
        self.output.appendPlainText(
            f"[system] Next session code (valid 30 min): {code_phrase}"
        )
