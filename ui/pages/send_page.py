from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ui.components.common import Card, CollapsibleOutputSection, DropList, PageHeader


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
        self.compress_toggle = QCheckBox("Compress with temporary 7-Zip and auto-extract on receive")
        picker.layout.addWidget(self.compress_toggle)

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
        self.cancel_btn = QPushButton("Cancel Upload")
        self.cancel_btn.setEnabled(False)
        copy_btn = QPushButton("Copy Code")
        copy_next_btn = QPushButton("Copy Next Code")
        clear_btn = QPushButton("Clear")
        code_row.addWidget(self.start_btn)
        code_row.addWidget(self.cancel_btn)
        code_row.addWidget(copy_btn)
        code_row.addWidget(copy_next_btn)
        code_row.addWidget(clear_btn)
        code_row.addStretch(1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Progress: %p%")
        self.progress_status = QLabel("Ready")
        self.progress_status.setProperty("role", "muted")
        code_card.layout.addWidget(self.code)
        code_card.layout.addWidget(self.next_code)
        code_card.layout.addWidget(self.next_code_expiry)
        code_card.layout.addLayout(code_row)
        code_card.layout.addWidget(self.progress)
        code_card.layout.addWidget(self.progress_status)

        self.output_section = CollapsibleOutputSection("Live Output", "Croc send process stream", max_blocks=1200)
        self.output = self.output_section.output

        root.addWidget(picker)
        root.addWidget(code_card)
        root.addWidget(self.output_section, 1)
        root.addStretch(0)
        self._bottom_anchor_index = root.count() - 1
        self.output_section.expanded_changed.connect(
            lambda expanded: self._sync_output_layout_stretch(root, expanded)
        )

        btn_file.clicked.connect(self.pick_files)
        btn_folder.clicked.connect(self.pick_folder)
        btn_remove.clicked.connect(self.drop.remove_selected)
        self.start_btn.clicked.connect(self.start_send)
        self.cancel_btn.clicked.connect(self.cancel_send)
        copy_btn.clicked.connect(self.copy_code)
        copy_next_btn.clicked.connect(self.copy_next_code)
        clear_btn.clicked.connect(self.clear_send_page)

        self.context.transfer_service.transfer_output.connect(self.on_transfer_output)
        self.context.transfer_service.transfer_updated.connect(self.on_transfer_updated)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)
        self.context.transfer_service.next_code_ready.connect(self.on_next_code_ready)

    @staticmethod
    def _format_eta(seconds: float | None) -> str:
        if seconds is None or seconds < 1:
            return ""
        total_seconds = max(1, int(round(seconds)))
        minutes, secs = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _apply_progress_display(
        self,
        *,
        message: str,
        percent: float | None = None,
        eta_seconds: float | None = None,
        indeterminate: bool = False,
    ) -> None:
        eta_text = self._format_eta(eta_seconds)
        status_text = message
        if percent is not None and not indeterminate:
            status_text = f"{message} {int(round(percent))}%"
        if eta_text:
            status_text = f"{status_text} | ETA {eta_text}"
        self.progress_status.setText(status_text)
        if indeterminate:
            self.progress.setRange(0, 0)
            self.progress.setFormat(message)
            return
        self.progress.setRange(0, 100)
        self.progress.setValue(max(0, min(100, int(round(percent or 0)))))
        self.progress.setFormat("%p%")

    def _sync_output_layout_stretch(self, root: QVBoxLayout, expanded: bool) -> None:
        output_index = root.indexOf(self.output_section)
        if output_index < 0:
            return
        root.setStretch(output_index, 1 if expanded else 0)
        root.setStretch(self._bottom_anchor_index, 0 if expanded else 1)

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        for file in files:
            self.drop.add_path(file)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.drop.add_path(folder)

    def clear_send_page(self):
        if self.current_transfer_id:
            record = self.context.transfer_service.get_record(self.current_transfer_id)
            if record and record.status in {"preparing", "running"}:
                QMessageBox.information(
                    self,
                    "Upload In Progress",
                    "Cancel the current upload before clearing the send form.",
                )
                return
        self._reset_send_form()

    def start_send(self):
        paths = self.drop.paths()
        if not paths:
            QMessageBox.warning(self, "No files", "Add at least one file or folder")
            return
        compress_enabled = self.compress_toggle.isChecked()
        self.pending_output_lines.clear()
        self.output.clear()
        self.next_code.clear()
        self.next_code_expiry.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress_status.setText("Preparing send...")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        try:
            record = self.context.transfer_service.start_send(
                paths,
                compress_7zip=compress_enabled,
            )
        except Exception as exc:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setFormat("%p%")
            self.progress_status.setText("Ready")
            self.start_btn.setEnabled(True)
            QMessageBox.critical(self, "Send failed", str(exc))
            return
        self.current_transfer_id = record.transfer_id
        self.code.setText(record.code_phrase)
        QGuiApplication.clipboard().setText(record.code_phrase)
        self.output.appendPlainText(f"Started transfer {record.transfer_id}")
        self.output.appendPlainText("[system] CrocDrop share code copied to clipboard.")
        if record.compression_mode == "7zip":
            self.output.appendPlainText("[system] Compression enabled. Share this CrocDrop code with the receiver:")
            self.output.appendPlainText(f"[system] {record.code_phrase}")
        self.on_transfer_updated(record.transfer_id)

    def _reset_send_form(self):
        self.current_transfer_id = ""
        self.pending_output_lines.clear()
        self.output_flush_timer.stop()
        self.drop.clear()
        self.code.clear()
        self.next_code.clear()
        self.next_code_expiry.clear()
        self.output.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress_status.setText("Ready")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def cancel_send(self):
        if not self.current_transfer_id:
            return
        transfer_id = self.current_transfer_id
        self.cancel_btn.setEnabled(False)
        self.output.appendPlainText(f"[system] Canceling upload {transfer_id}...")
        self.context.transfer_service.cancel(transfer_id)

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
        record = self.context.transfer_service.get_record(transfer_id)
        if not record:
            return
        if record.code_phrase and self.code.text() != record.code_phrase:
            self.code.setText(record.code_phrase)
        if record.phase_message:
            self._apply_progress_display(
                message=record.phase_message,
                percent=record.phase_percent,
                eta_seconds=record.phase_eta_seconds,
                indeterminate=record.phase_indeterminate,
            )
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, int(record.bytes_done))))
            self.progress.setFormat("%p%")
            if record.status == "running":
                self.progress_status.setText("Sending...")
            elif record.status == "completed":
                self.progress_status.setText("Completed")
            elif record.status == "failed":
                self.progress_status.setText("Failed")
            else:
                self.progress_status.setText("Ready")
        self.cancel_btn.setEnabled(record.status == "running")

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
        self.flush_output()
        if status == "completed":
            self.progress.setValue(100)
            self.progress.setFormat("%p%")
            self.progress_status.setText("Completed")
        if status == "canceled":
            self.output.appendPlainText("[system] Upload canceled")
            self.progress_status.setText("Canceled")
        if status == "failed":
            self.progress_status.setText("Failed")
        self.current_transfer_id = ""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def on_next_code_ready(self, transfer_id: str, code_phrase: str, expires_at_iso: str):
        if transfer_id != self.current_transfer_id:
            return
        self.next_code.setText(code_phrase)
        self.next_code_expiry.setText(f"Next code expires at: {expires_at_iso} (UTC)")
        self.output.appendPlainText(
            f"[system] Next session code (valid 30 min): {code_phrase}"
        )
