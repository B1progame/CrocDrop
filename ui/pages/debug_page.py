from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ui.components.common import Card, PageHeader


class DebugPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Debug", "Run self-tests, inspect backend health, and export diagnostics."))

        controls = Card("Self-Test and Tools")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 102400)
        self.size_spin.setValue(5)
        self.size_gb_preview = QLabel()
        self.size_gb_preview.setProperty("role", "muted")
        self._update_size_preview(self.size_spin.value())

        row = QHBoxLayout()
        row.addWidget(QLabel("Dummy size (MB):"))
        row.addWidget(self.size_spin)
        row.addWidget(self.size_gb_preview)
        row.addStretch(1)

        self.selftest_btn = QPushButton("Run Self-Test")
        self.selftest_btn.setObjectName("PrimaryButton")
        self.generate_dummy_btn = QPushButton("Generate Dummy File")
        self.launch_dual_btn = QPushButton("Launch Second Instance")
        self.health_btn = QPushButton("Backend Health Check")
        self.bundle_btn = QPushButton("Save Diagnostic Bundle")

        controls.layout.addLayout(row)
        controls.layout.addWidget(self.selftest_btn)
        controls.layout.addWidget(self.generate_dummy_btn)
        controls.layout.addWidget(self.launch_dual_btn)
        controls.layout.addWidget(self.health_btn)
        controls.layout.addWidget(self.bundle_btn)

        logs = Card("Debug Output")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1500)
        logs.layout.addWidget(self.output)

        root.addWidget(controls)
        root.addWidget(logs, 1)

        self.selftest_btn.clicked.connect(self.run_self_test)
        self.generate_dummy_btn.clicked.connect(self.generate_dummy_file)
        self.launch_dual_btn.clicked.connect(self.launch_second)
        self.health_btn.clicked.connect(self.health_check)
        self.bundle_btn.clicked.connect(self.save_bundle)
        self.size_spin.valueChanged.connect(self._update_size_preview)

        self.context.debug_service.self_test_progress.connect(self.on_self_test_progress)
        self.context.debug_service.self_test_finished.connect(self.on_self_test_finished)

    def run_self_test(self):
        self.output.appendPlainText("Starting self-test...")
        self.context.debug_service.run_self_test(size_mb=self.size_spin.value())

    def generate_dummy_file(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose folder for generated dummy file")
        if not folder:
            return
        try:
            path = self.context.debug_service.generate_dummy_file(Path(folder), size_mb=self.size_spin.value())
            self.output.appendPlainText(f"Generated: {path}")
        except Exception as exc:
            self.output.appendPlainText(f"Failed to generate file: {exc}")

    def launch_second(self):
        self.context.debug_service.launch_second_instance()
        self.output.appendPlainText("Second instance launched with --debug-peer")

    def health_check(self):
        diag = self.context.debug_service.backend_health()
        self.output.appendPlainText(str(diag))

    def save_bundle(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save diagnostics", "crocdrop_diagnostics.txt", "Text Files (*.txt)")
        if not path:
            return
        records = self.context.history_service.list_records()[:20]
        diag = self.context.debug_service.backend_health()
        lines = ["CrocDrop Diagnostic Bundle", "", "Backend:", str(diag), "", "Recent transfers:"]
        for r in records:
            lines.append(str(r.to_dict()))
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        self.output.appendPlainText(f"Diagnostics saved to {path}")

    def on_self_test_progress(self, msg: str):
        self.output.appendPlainText(msg)

    def on_self_test_finished(self, ok: bool, msg: str):
        self.output.appendPlainText(("PASS" if ok else "FAIL") + " | " + msg)

    def _update_size_preview(self, size_mb: int):
        size_gb = size_mb / 1024.0
        self.size_gb_preview.setText(f"~ {size_gb:.3f} GB")
