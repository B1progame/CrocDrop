from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.version import APP_VERSION
from ui.components.common import Card, PageHeader
from ui.theme import apply_theme


class UpdateWorker(QObject):
    progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, update_service):
        super().__init__()
        self.update_service = update_service

    @Slot()
    def run(self):
        try:
            result = self.update_service.download_latest_update(
                progress_callback=lambda done, total: self.progress.emit(done, total),
                status_callback=lambda text: self.status.emit(text),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating CrocDrop")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.status_label = QLabel("Preparing update ...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(downloaded, total))
            percent = int((downloaded / total) * 100)
            self.status_label.setText(f"Downloading update ... {percent}%")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Downloading update ...")


class SettingsPage(QWidget):
    settings_changed = Signal()

    def __init__(self, context, app):
        super().__init__()
        self.context = context
        self.app = app
        self.update_thread: QThread | None = None
        self.update_worker: UpdateWorker | None = None
        self.update_dialog: UpdateProgressDialog | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Settings", "Customize folders, appearance, relay behavior, and account preferences."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        root.addWidget(scroll, 1)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)
        scroll.setWidget(container)

        settings = self.context.settings_service.get()

        self.download_folder = QLineEdit(settings.default_download_folder)
        browse_btn = QPushButton("Browse")
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(0, 0, 0, 0)
        folder_row.setSpacing(8)
        folder_row.addWidget(self.download_folder, 1)
        folder_row.addWidget(browse_btn)
        folder_widget = QWidget()
        folder_widget.setLayout(folder_row)

        self.ask_before = QCheckBox("Enabled")
        self.ask_before.setChecked(settings.ask_before_receiving)
        self.auto_open = QCheckBox("Enabled")
        self.auto_open.setChecked(settings.auto_open_received_folder)
        self.remember_last = QCheckBox("Enabled")
        self.remember_last.setChecked(settings.remember_last_folders)
        self.dark_mode = QCheckBox("Enabled")
        self.dark_mode.setChecked(settings.dark_mode)

        self.accent = QComboBox()
        self.accent.addItems(["#8f5cff", "#b06cff", "#ff7cc5", "#35c9a5"])
        self.accent.setCurrentText(settings.accent_color)

        self.relay_mode = QComboBox()
        self.relay_mode.addItems(["public", "custom"])
        self.relay_mode.setCurrentText(settings.relay_mode)
        self.custom_relay = QLineEdit(settings.custom_relay)

        self.binary_path = QLineEdit(settings.croc_binary_path)
        binary_btn = QPushButton("Browse Binary")
        delete_binary_btn = QPushButton("Delete Croc Binary")
        binary_row = QHBoxLayout()
        binary_row.setContentsMargins(0, 0, 0, 0)
        binary_row.setSpacing(8)
        binary_row.addWidget(self.binary_path, 1)
        binary_row.addWidget(binary_btn)
        binary_row.addWidget(delete_binary_btn)
        binary_widget = QWidget()
        binary_widget.setLayout(binary_row)

        self.log_retention = QSpinBox()
        self.log_retention.setRange(1, 120)
        self.log_retention.setValue(settings.log_retention_days)

        self.auto_download = QCheckBox("Enabled")
        self.auto_download.setChecked(settings.auto_download_croc)

        self.upload_limit_widget, self.upload_unlimited, self.upload_limit = self._create_bandwidth_control(settings.upload_limit_kbps)
        self.download_limit_widget, self.download_unlimited, self.download_limit = self._create_bandwidth_control(settings.download_limit_kbps)

        general_card, general_form = self._make_settings_card(
            "Appearance and App Behavior",
            "Visual defaults and app-wide memory behavior.",
        )
        row = 0
        row = self._add_setting_row(general_form, row, "Dark mode", "Use the premium dark appearance for the whole app shell.", self.dark_mode)
        row = self._add_setting_row(general_form, row, "Accent color", "Primary accent for focus rings and highlights.", self.accent)
        row = self._add_setting_row(general_form, row, "Remember last folders", "Keep the most recent send/receive directories for faster reuse.", self.remember_last)
        row = self._add_setting_row(general_form, row, "Log retention", "Automatically prune old logs older than this window.", self.log_retention)
        container_layout.addWidget(general_card)

        transfers_card, transfers_form = self._make_settings_card(
            "Receive Defaults",
            "Control how incoming files are accepted and where they are written.",
        )
        row = 0
        row = self._add_setting_row(transfers_form, row, "Default download folder", "Where incoming files are saved by default.", folder_widget)
        row = self._add_setting_row(transfers_form, row, "Ask before receiving", "Prompt confirmation before accepting incoming transfer data.", self.ask_before)
        row = self._add_setting_row(transfers_form, row, "Auto-open received folder", "Open the destination folder after a successful receive.", self.auto_open)
        container_layout.addWidget(transfers_card)

        bandwidth_card, bandwidth_form = self._make_settings_card(
            "Bandwidth Limits",
            "Set transfer speed caps in Mbit/s. Turn off Unlimited to enter a custom value.",
        )
        row = 0
        row = self._add_setting_row(
            bandwidth_form,
            row,
            "Upload speed limit",
            "Applies while this device is sending files.",
            self.upload_limit_widget,
        )
        row = self._add_setting_row(
            bandwidth_form,
            row,
            "Download speed limit",
            "Applies while this device is receiving files (if supported by installed croc version).",
            self.download_limit_widget,
        )
        container_layout.addWidget(bandwidth_card)

        connection_card, connection_form = self._make_settings_card(
            "Croc Binary and Relay",
            "Manage the croc executable and relay routing used by the transfer backend.",
        )
        row = 0
        row = self._add_setting_row(connection_form, row, "Relay mode", "Use official public relay now, custom relay is ready for future self-hosting.", self.relay_mode)
        row = self._add_setting_row(connection_form, row, "Custom relay", "Optional custom relay endpoint (used when relay mode is custom).", self.custom_relay)
        row = self._add_setting_row(connection_form, row, "Croc binary path", "Managed croc executable location used by CrocDrop.", binary_widget)
        row = self._add_setting_row(connection_form, row, "Auto-download croc", "Automatically fetch official croc release when binary is missing.", self.auto_download)
        container_layout.addWidget(connection_card)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")

        account_card = Card("Profile")
        account_hint = QLabel("Profiles are local-only labels for this installation. Guest mode keeps CrocDrop account-free.")
        account_hint.setObjectName("SettingDescription")
        account_hint.setWordWrap(True)
        self.current_profile_label = QLabel()
        self.current_profile_label.setObjectName("ProfileCurrentLabel")
        self.profile_combo = QComboBox()
        self.switch_profile_btn = QPushButton("Switch Profile")
        self.remove_profile_btn = QPushButton("Remove Current Profile")
        self.guest_mode_btn = QPushButton("Use Guest Mode")
        profile_actions = QHBoxLayout()
        profile_actions.setContentsMargins(0, 0, 0, 0)
        profile_actions.setSpacing(8)
        profile_actions.addWidget(self.switch_profile_btn)
        profile_actions.addWidget(self.remove_profile_btn)
        profile_actions.addWidget(self.guest_mode_btn)
        profile_actions.addStretch(1)
        account_card.layout.addWidget(account_hint)
        account_card.layout.addWidget(self.current_profile_label)
        account_card.layout.addWidget(self.profile_combo)
        account_card.layout.addLayout(profile_actions)
        container_layout.addWidget(account_card)

        debug_card = Card("Advanced and Debug Features")
        debug_hint = QLabel("Debug controls are intentionally restart-aware so the main navigation stays predictable.")
        debug_hint.setObjectName("SettingDescription")
        debug_hint.setWordWrap(True)
        self.debug_status_label = QLabel()
        self.debug_status_label.setObjectName("SettingDescription")
        self.enable_debug_btn = QPushButton("Enable Debug Features")
        self.disable_debug_btn = QPushButton("Disable Debug Features")
        debug_actions = QHBoxLayout()
        debug_actions.setContentsMargins(0, 0, 0, 0)
        debug_actions.setSpacing(8)
        debug_actions.addWidget(self.enable_debug_btn)
        debug_actions.addWidget(self.disable_debug_btn)
        debug_actions.addStretch(1)
        debug_card.layout.addWidget(debug_hint)
        debug_card.layout.addWidget(self.debug_status_label)
        debug_card.layout.addLayout(debug_actions)
        container_layout.addWidget(debug_card)

        updates_card = Card("App Updates")
        update_hint = QLabel("Check GitHub releases and apply downloaded CrocDrop updates with the built-in updater.")
        update_hint.setObjectName("SettingDescription")
        update_hint.setWordWrap(True)
        self.current_version_label = QLabel(f"Current version: {APP_VERSION}")
        self.current_version_label.setObjectName("SettingDescription")
        self.update_btn = QPushButton("Update App")
        self.update_btn.setObjectName("PrimaryButton")
        updates_card.layout.addWidget(update_hint)
        updates_card.layout.addWidget(self.current_version_label)
        updates_card.layout.addWidget(self.update_btn)
        container_layout.addWidget(updates_card)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 2, 0, 0)
        action_row.addStretch(1)
        action_row.addWidget(save_btn)
        container_layout.addLayout(action_row)
        container_layout.addStretch(1)

        browse_btn.clicked.connect(self.pick_folder)
        binary_btn.clicked.connect(self.pick_binary)
        delete_binary_btn.clicked.connect(self.delete_binary)
        save_btn.clicked.connect(self.save)
        self.switch_profile_btn.clicked.connect(self.switch_profile)
        self.remove_profile_btn.clicked.connect(self.remove_current_profile)
        self.guest_mode_btn.clicked.connect(self.set_guest_mode)
        self.enable_debug_btn.clicked.connect(self.enable_debug_features)
        self.disable_debug_btn.clicked.connect(self.disable_debug_features)
        self.update_btn.clicked.connect(self.update_app)
        self.refresh_account_section()
        self.refresh_debug_controls()

    def _create_bandwidth_control(self, limit_kbps: int) -> tuple[QWidget, QCheckBox, QLineEdit]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        unlimited = QCheckBox("Unlimited")
        unlimited.setChecked(limit_kbps <= 0)

        value_input = QLineEdit()
        value_input.setPlaceholderText("Enter Mbit/s")
        value_input.setValidator(QDoubleValidator(0.01, 1_000_000.0, 2, value_input))
        value_input.setText(self._format_limit_mbit(limit_kbps))
        value_input.setClearButtonEnabled(True)
        value_input.setMaximumWidth(180)

        unit_label = QLabel("Mbit/s")
        unit_label.setObjectName("SettingDescription")

        layout.addWidget(unlimited)
        layout.addWidget(value_input)
        layout.addWidget(unit_label)
        layout.addStretch(1)

        def sync_state(checked: bool) -> None:
            value_input.setVisible(not checked)
            unit_label.setVisible(not checked)

        unlimited.toggled.connect(sync_state)
        sync_state(unlimited.isChecked())
        return widget, unlimited, value_input

    def _format_limit_mbit(self, limit_kbps: int) -> str:
        if limit_kbps <= 0:
            return ""
        value = limit_kbps / 125.0
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _read_bandwidth_limit_kbps(self, unlimited: QCheckBox, value_input: QLineEdit) -> int:
        if unlimited.isChecked():
            return 0
        text = value_input.text().strip().replace(",", ".")
        if not text:
            return 0
        try:
            value_mbit = float(text)
        except ValueError:
            return 0
        if value_mbit <= 0:
            return 0
        return max(1, int(round(value_mbit * 125.0)))

    def _make_settings_card(self, title: str, description: str) -> tuple[Card, QGridLayout]:
        card = Card(title)
        if description:
            desc = QLabel(description)
            desc.setObjectName("SettingDescription")
            desc.setWordWrap(True)
            card.layout.addWidget(desc)
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(14)
        grid.setColumnMinimumWidth(0, 280)
        grid.setColumnStretch(1, 1)
        card.layout.addLayout(grid)
        return card, grid

    def _add_setting_row(self, grid: QGridLayout, row: int, label_text: str, description: str, widget: QWidget) -> int:
        left = QWidget()
        left.setObjectName("SettingInfo")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        label = QLabel(label_text)
        label.setObjectName("SettingLabel")
        desc = QLabel(description)
        desc.setObjectName("SettingDescription")
        desc.setWordWrap(True)
        left_layout.addWidget(label)
        left_layout.addWidget(desc)
        grid.addWidget(left, row, 0)
        grid.addWidget(widget, row, 1)
        return row + 1

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose default download folder", self.download_folder.text())
        if folder:
            self.download_folder.setText(folder)

    def pick_binary(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select croc binary", self.binary_path.text() or "", "Executable (*.exe);;All Files (*)")
        if path:
            self.binary_path.setText(path)

    def save(self):
        s = self.context.settings_service.get()
        s.default_download_folder = self.download_folder.text().strip()
        s.ask_before_receiving = self.ask_before.isChecked()
        s.auto_open_received_folder = self.auto_open.isChecked()
        s.remember_last_folders = self.remember_last.isChecked()
        s.dark_mode = self.dark_mode.isChecked()
        s.accent_color = self.accent.currentText()
        s.relay_mode = self.relay_mode.currentText()
        s.custom_relay = self.custom_relay.text().strip()
        s.croc_binary_path = self.binary_path.text().strip()
        s.auto_download_croc = self.auto_download.isChecked()
        s.upload_limit_kbps = self._read_bandwidth_limit_kbps(self.upload_unlimited, self.upload_limit)
        s.download_limit_kbps = self._read_bandwidth_limit_kbps(self.download_unlimited, self.download_limit)
        s.log_retention_days = self.log_retention.value()
        self.context.settings_service.save(s)
        self.context.log_service.prune_old_logs(s.log_retention_days)
        apply_theme(self.app, s)
        self.refresh_account_section()
        self.refresh_debug_controls()
        self.settings_changed.emit()

    def delete_binary(self):
        path_text = self.binary_path.text().strip()
        display_target = path_text or "(auto-detected current croc)"
        answer = QMessageBox.question(
            self,
            "Delete Croc Binary",
            f"Delete croc binary at:\n{display_target}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        ok, message = self.context.croc_manager.delete_binary(path_text or None)
        if ok:
            self.binary_path.setText("")
            settings = self.context.settings_service.get()
            settings.croc_binary_path = ""
            self.context.settings_service.save(settings)
            QMessageBox.information(self, "Delete Croc Binary", message)
            self.settings_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Croc Binary", message)

    def refresh_account_section(self):
        settings = self.context.settings_service.get()
        current = settings.current_profile.strip()
        self.current_profile_label.setText(f"Current profile: {current if current else 'Guest'}")
        self.profile_combo.clear()
        self.profile_combo.addItems(settings.profiles)
        self.remove_profile_btn.setEnabled(bool(current))
        self.switch_profile_btn.setEnabled(self.profile_combo.count() > 0)

    def switch_profile(self):
        selected = self.profile_combo.currentText().strip()
        if not selected:
            return
        self.context.settings_service.set_current_profile(selected)
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", f"Switched profile to '{selected}'.")

    def remove_current_profile(self):
        settings = self.context.settings_service.get()
        current = settings.current_profile.strip()
        if not current:
            QMessageBox.information(self, "Profile", "You are already in guest mode.")
            return
        answer = QMessageBox.question(
            self,
            "Remove Profile",
            f"Remove account profile '{current}'?\n\nYou will return to guest mode.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.context.settings_service.remove_profile(current)
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", f"Removed '{current}'.")

    def set_guest_mode(self):
        self.context.settings_service.use_guest_mode()
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", "Guest mode enabled. You will be asked at startup next launch.")

    def enable_debug_features(self):
        password, ok = QInputDialog.getText(self, "Enable Debug", "Enter admin password:", QLineEdit.Password)
        if not ok:
            return
        if password != "admin":
            QMessageBox.warning(self, "Enable Debug", "Wrong password.")
            return

        settings = self.context.settings_service.get()
        settings.debug_mode = True
        self.context.settings_service.save(settings)
        self.refresh_debug_controls()
        self.settings_changed.emit()
        QMessageBox.information(self, "Enable Debug", "Debug features enabled. Restart CrocDrop to show the Debug page.")

    def disable_debug_features(self):
        settings = self.context.settings_service.get()
        if not settings.debug_mode:
            self.refresh_debug_controls()
            return
        settings.debug_mode = False
        self.context.settings_service.save(settings)
        self.refresh_debug_controls()
        self.settings_changed.emit()
        QMessageBox.information(self, "Disable Debug", "Debug features disabled. Restart CrocDrop to hide the Debug page.")

    def refresh_debug_controls(self):
        enabled = self.context.settings_service.get().debug_mode
        self.debug_status_label.setText(f"Debug features are currently {'enabled' if enabled else 'disabled'}.")
        self.enable_debug_btn.setEnabled(not enabled)
        self.disable_debug_btn.setEnabled(enabled)

    def update_app(self):
        if self.update_thread is not None:
            QMessageBox.information(self, "Update App", "An update check is already running.")
            return

        self.update_btn.setEnabled(False)
        self.update_dialog = UpdateProgressDialog(self)
        self.update_dialog.set_status("Checking GitHub releases ...")
        self.update_dialog.show()

        self.update_thread = QThread(self)
        self.update_worker = UpdateWorker(self.context.update_service)
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.progress.connect(self._on_update_progress)
        self.update_worker.status.connect(self._on_update_status)
        self.update_worker.finished.connect(self._on_update_finished)
        self.update_worker.failed.connect(self._on_update_failed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self._cleanup_update_thread)
        self.update_thread.start()

    def _cleanup_update_thread(self):
        if self.update_worker is not None:
            self.update_worker.deleteLater()
            self.update_worker = None
        if self.update_thread is not None:
            self.update_thread.deleteLater()
            self.update_thread = None
        self.update_btn.setEnabled(True)

    def _on_update_progress(self, downloaded: int, total: int):
        if self.update_dialog is not None:
            self.update_dialog.set_progress(downloaded, total)

    def _on_update_status(self, text: str):
        if self.update_dialog is not None:
            self.update_dialog.set_status(text)

    def _on_update_failed(self, message: str):
        if self.update_dialog is not None:
            self.update_dialog.close()
            self.update_dialog.deleteLater()
            self.update_dialog = None
        QMessageBox.warning(self, "Update App", f"Update failed:\n{message}")

    def _on_update_finished(self, result):
        if self.update_dialog is not None:
            self.update_dialog.close()
            self.update_dialog.deleteLater()
            self.update_dialog = None

        if result.status == "up-to-date":
            QMessageBox.information(self, "Update App", result.message)
            return

        if result.status != "downloaded" or not result.archive_path:
            QMessageBox.warning(self, "Update App", "Update completed with an unexpected result.")
            return

        answer = QMessageBox.information(
            self,
            "Update Ready",
            (
                f"Update {result.latest_version} downloaded.\n\n"
                "CrocDrop will now close, apply the update, and start again automatically."
            ),
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok,
        )
        if answer != QMessageBox.Ok:
            return

        try:
            self.context.update_service.apply_update_and_restart(result.archive_path)
        except Exception as exc:
            QMessageBox.warning(self, "Update App", f"Could not start updater:\n{exc}")
            return
        QApplication.quit()
