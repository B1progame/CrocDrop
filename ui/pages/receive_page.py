from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ui.components.common import Card, CollapsibleOutputSection, PageHeader


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
        self.collision.addItems(["overwrite", "skip existing"])

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
        self.progress_status = QLabel("Ready")
        self.progress_status.setProperty("role", "muted")

        form.layout.addWidget(QLabel("Code"))
        form.layout.addLayout(row1)
        form.layout.addWidget(QLabel("Destination"))
        form.layout.addLayout(row2)
        form.layout.addWidget(QLabel("Collision Handling"))
        form.layout.addWidget(self.collision)
        form.layout.addLayout(action_row)
        form.layout.addWidget(self.progress)
        form.layout.addWidget(self.progress_status)

        self.output_section = CollapsibleOutputSection("Live Output", "Croc receive process stream", max_blocks=1200)
        self.output = self.output_section.output

        root.addWidget(form)
        root.addWidget(self.output_section, 1)
        root.addStretch(0)
        self._bottom_anchor_index = root.count() - 1
        self.output_section.expanded_changed.connect(
            lambda expanded: self._sync_output_layout_stretch(root, expanded)
        )

        browse_btn.clicked.connect(self.browse_destination)
        start_btn.clicked.connect(self.start_receive)
        paste_btn.clicked.connect(self.paste_code)

        self.context.transfer_service.transfer_output.connect(self.on_transfer_output)
        self.context.transfer_service.transfer_updated.connect(self.on_transfer_updated)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)

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
        if not overwrite:
            self.output.appendPlainText(
                "Note: existing files with the same name may be skipped by croc in non-overwrite mode."
            )

        try:
            record = self.context.transfer_service.start_receive(
                code_phrase=code,
                destination=destination,
                overwrite=overwrite,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Receive failed", str(exc))
            return
        self.attempted_codes.add(code)
        self.current_transfer_id = record.transfer_id
        self.pending_output_lines.clear()
        self.output.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress_status.setText("Receiving...")
        self.output.appendPlainText(f"Started receive {record.transfer_id}")
        if record.compression_mode == "7zip":
            self.output.appendPlainText(
                "[system] Receiving compressed archive..."
            )
        self.on_transfer_updated(record.transfer_id)

    def on_transfer_output(self, transfer_id: str, line: str):
        if transfer_id != self.current_transfer_id:
            return
        self.pending_output_lines.extend(part for part in line.splitlines() if part)
        if self.pending_output_lines and not self.output_flush_timer.isActive():
            self.output_flush_timer.start()

    def on_transfer_finished(self, transfer_id: str, status: str):
        if transfer_id != self.current_transfer_id:
            return
        self.flush_output()
        if status == "completed":
            self.progress.setValue(100)
            self.progress.setFormat("%p%")
            self.progress_status.setText("Completed")
        elif status == "failed":
            self.progress_status.setText("Failed")
            record = self.context.transfer_service.get_record(transfer_id)
            if record:
                joined = "\n".join(record.output_excerpt[-80:]).lower()
                if "no files transferred" in joined:
                    self.output.appendPlainText(
                        "Hint: Receiver connected but wrote no file. Choose an empty folder or collision='overwrite', then ask sender for a NEW code."
                    )
                if "room (secure channel) not ready" in joined or "peer disconnected" in joined:
                    self.output.appendPlainText(
                        "Hint: This code/session is no longer active. Start a fresh send and use the newly generated code."
                    )
        self.current_transfer_id = ""

    def on_transfer_updated(self, transfer_id: str):
        if transfer_id != self.current_transfer_id:
            return
        record = self.context.transfer_service.get_record(transfer_id)
        if not record:
            return
        if record.phase_message:
            self._apply_progress_display(
                message=record.phase_message,
                percent=record.phase_percent,
                eta_seconds=record.phase_eta_seconds,
                indeterminate=record.phase_indeterminate,
            )
            return

        self.progress.setRange(0, 100)
        self.progress.setValue(max(0, min(100, int(record.bytes_done))))
        self.progress.setFormat("%p%")
        if record.status == "running":
            self.progress_status.setText("Receiving...")
        elif record.status == "completed":
            self.progress_status.setText("Completed")
        elif record.status == "failed":
            self.progress_status.setText("Failed")
        else:
            self.progress_status.setText("Ready")

    def flush_output(self):
        if not self.pending_output_lines:
            self.output_flush_timer.stop()
            return
        chunk = "\n".join(self.pending_output_lines)
        self.pending_output_lines.clear()
        self.output.appendPlainText(chunk)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
