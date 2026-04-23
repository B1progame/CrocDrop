from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.components.common import Card, PageHeader


class DebugPage(QWidget):
    def __init__(self, context):
        super().__init__()
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Debug", "Run self-tests, inspect backend health, and export diagnostics."))

        tools_row = QHBoxLayout()
        tools_row.setContentsMargins(0, 0, 0, 0)
        tools_row.setSpacing(12)

        self_test_card = Card("Transfer Self-Test")
        self_test_note = QLabel("Starts a local send/receive loop with the standard 5 MB fixture.")
        self_test_note.setWordWrap(True)
        self_test_note.setProperty("role", "muted")
        self.selftest_btn = QPushButton("Run Self-Test")
        self.selftest_btn.setObjectName("PrimaryButton")
        self_test_card.layout.addWidget(self_test_note)
        self_test_card.layout.addWidget(self.selftest_btn)
        self_test_card.layout.addStretch(1)

        dummy_card = Card("Dummy File Generator")
        dummy_note = QLabel("Create a sparse test file for manual transfer checks.")
        dummy_note.setWordWrap(True)
        dummy_note.setProperty("role", "muted")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 102400)
        self.size_spin.setValue(5)
        self.size_gb_preview = QLabel()
        self.size_gb_preview.setProperty("role", "muted")
        self._update_size_preview(self.size_spin.value())

        self.generate_dummy_btn = QPushButton("Generate Dummy File")
        self.dummy_options_btn = QPushButton("+ Options")
        self.dummy_options_btn.setObjectName("SectionToggleButton")
        self.dummy_options_btn.setCheckable(True)

        dummy_action_row = QHBoxLayout()
        dummy_action_row.setContentsMargins(0, 0, 0, 0)
        dummy_action_row.setSpacing(8)
        dummy_action_row.addWidget(self.generate_dummy_btn)
        dummy_action_row.addWidget(self.dummy_options_btn)
        dummy_action_row.addStretch(1)

        self.dummy_options = QWidget()
        self.dummy_options.setObjectName("DebugInlineOptions")
        options_row = QHBoxLayout(self.dummy_options)
        options_row.setContentsMargins(0, 4, 0, 0)
        options_row.setSpacing(8)
        options_row.addWidget(QLabel("Size (MB):"))
        options_row.addWidget(self.size_spin)
        options_row.addWidget(self.size_gb_preview)
        options_row.addStretch(1)
        self.dummy_options.hide()

        dummy_card.layout.addWidget(dummy_note)
        dummy_card.layout.addLayout(dummy_action_row)
        dummy_card.layout.addWidget(self.dummy_options)
        dummy_card.layout.addStretch(1)

        tools_row.addWidget(self_test_card, 1)
        tools_row.addWidget(dummy_card, 1)

        diagnostics = Card("Diagnostics")
        self.launch_dual_btn = QPushButton("Launch Second Instance")
        self.health_btn = QPushButton("Backend Health Check")
        self.bundle_btn = QPushButton("Save Diagnostic Bundle")

        diag_note = QLabel("Tools for multi-peer testing, backend inspection, and portable support bundles.")
        diag_note.setWordWrap(True)
        diag_note.setProperty("role", "muted")
        diag_grid = QGridLayout()
        diag_grid.setContentsMargins(0, 0, 0, 0)
        diag_grid.setHorizontalSpacing(8)
        diag_grid.setVerticalSpacing(8)
        diag_grid.addWidget(self.launch_dual_btn, 0, 0)
        diag_grid.addWidget(self.health_btn, 0, 1)
        diag_grid.addWidget(self.bundle_btn, 0, 2)
        diagnostics.layout.addWidget(diag_note)
        diagnostics.layout.addLayout(diag_grid)

        logs = Card("Debug Output")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(1500)
        logs.layout.addWidget(self.output)

        root.addLayout(tools_row)
        root.addWidget(diagnostics)
        root.addWidget(logs, 1)

        self.selftest_btn.clicked.connect(self.run_self_test)
        self.generate_dummy_btn.clicked.connect(self.generate_dummy_file)
        self.dummy_options_btn.clicked.connect(self._toggle_dummy_options)
        self.launch_dual_btn.clicked.connect(self.launch_second)
        self.health_btn.clicked.connect(self.health_check)
        self.bundle_btn.clicked.connect(self.save_bundle)
        self.size_spin.valueChanged.connect(self._update_size_preview)

        self.context.debug_service.self_test_progress.connect(self.on_self_test_progress)
        self.context.debug_service.self_test_finished.connect(self.on_self_test_finished)

    def run_self_test(self):
        self.output.appendPlainText("Starting self-test with standard 5 MB fixture...")
        self.context.debug_service.run_self_test()

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

    def _toggle_dummy_options(self, expanded: bool):
        self.dummy_options.setVisible(expanded)
        self.dummy_options_btn.setText("- Options" if expanded else "+ Options")
