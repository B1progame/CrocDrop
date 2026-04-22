from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.components.common import Card, PageHeader
from ui.theme import apply_theme


class SettingsPage(QWidget):
    def __init__(self, context, app):
        super().__init__()
        self.context = context
        self.app = app

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

        card = Card("General")
        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)

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

        row = 0
        row = self._add_setting_row(form, row, "Default download folder", "Where incoming files are saved by default.", folder_widget)
        row = self._add_setting_row(form, row, "Ask before receiving", "Prompt confirmation before accepting incoming transfer data.", self.ask_before)
        row = self._add_setting_row(form, row, "Auto-open received folder", "Open the destination folder after a successful receive.", self.auto_open)
        row = self._add_setting_row(form, row, "Remember last folders", "Keep the most recent send/receive directories for faster reuse.", self.remember_last)
        row = self._add_setting_row(form, row, "Dark mode", "Use the premium dark appearance for the whole app shell.", self.dark_mode)
        row = self._add_setting_row(form, row, "Accent color", "Primary accent for focus rings and highlights.", self.accent)
        row = self._add_setting_row(form, row, "Relay mode", "Use official public relay now, custom relay is ready for future self-hosting.", self.relay_mode)
        row = self._add_setting_row(form, row, "Custom relay", "Optional custom relay endpoint (used when relay mode is custom).", self.custom_relay)
        row = self._add_setting_row(form, row, "Croc binary path", "Managed croc executable location used by CrocDrop.", binary_widget)
        row = self._add_setting_row(form, row, "Auto-download croc", "Automatically fetch official croc release when binary is missing.", self.auto_download)
        row = self._add_setting_row(form, row, "Log retention (days)", "Automatically prune old logs older than this window.", self.log_retention)
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        card.layout.addLayout(form)
        card.layout.addWidget(save_btn)
        container_layout.addWidget(card)

        account_card = Card("Account")
        self.current_profile_label = QLabel()
        self.current_profile_label.setObjectName("SettingDescription")
        self.profile_combo = QComboBox()
        self.switch_profile_btn = QPushButton("Switch Profile")
        self.remove_profile_btn = QPushButton("Remove Current Account")
        self.guest_mode_btn = QPushButton("Use Guest Mode")
        account_card.layout.addWidget(self.current_profile_label)
        account_card.layout.addWidget(self.profile_combo)
        account_card.layout.addWidget(self.switch_profile_btn)
        account_card.layout.addWidget(self.remove_profile_btn)
        account_card.layout.addWidget(self.guest_mode_btn)
        container_layout.addWidget(account_card)

        debug_card = Card("Developer Features")
        self.debug_status_label = QLabel()
        self.debug_status_label.setObjectName("SettingDescription")
        self.enable_debug_btn = QPushButton("Enable Debug Features")
        self.disable_debug_btn = QPushButton("Disable Debug Features")
        debug_card.layout.addWidget(self.debug_status_label)
        debug_card.layout.addWidget(self.enable_debug_btn)
        debug_card.layout.addWidget(self.disable_debug_btn)
        container_layout.addWidget(debug_card)
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
        self.refresh_account_section()
        self.refresh_debug_controls()

    def _add_setting_row(self, grid: QGridLayout, row: int, label_text: str, description: str, widget: QWidget) -> int:
        left = QWidget()
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
        s.log_retention_days = self.log_retention.value()
        self.context.settings_service.save(s)
        self.context.log_service.prune_old_logs(s.log_retention_days)
        apply_theme(self.app, s)
        self.refresh_account_section()
        self.refresh_debug_controls()

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
        QMessageBox.information(self, "Account", f"Switched profile to '{selected}'.")

    def remove_current_profile(self):
        settings = self.context.settings_service.get()
        current = settings.current_profile.strip()
        if not current:
            QMessageBox.information(self, "Account", "You are already in guest mode.")
            return
        answer = QMessageBox.question(
            self,
            "Remove Account",
            f"Remove account profile '{current}'?\n\nYou will return to guest mode.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.context.settings_service.remove_profile(current)
        self.refresh_account_section()
        QMessageBox.information(self, "Account", f"Removed '{current}'.")

    def set_guest_mode(self):
        self.context.settings_service.use_guest_mode()
        self.refresh_account_section()
        QMessageBox.information(self, "Account", "Guest mode enabled. You will be asked at startup next launch.")

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
        QMessageBox.information(self, "Enable Debug", "Debug features enabled. Restart CrocDrop to show the Debug page.")

    def disable_debug_features(self):
        settings = self.context.settings_service.get()
        if not settings.debug_mode:
            self.refresh_debug_controls()
            return
        settings.debug_mode = False
        self.context.settings_service.save(settings)
        self.refresh_debug_controls()
        QMessageBox.information(self, "Disable Debug", "Debug features disabled. Restart CrocDrop to hide the Debug page.")

    def refresh_debug_controls(self):
        enabled = self.context.settings_service.get().debug_mode
        self.debug_status_label.setText(f"Debug features are currently {'enabled' if enabled else 'disabled'}.")
        self.enable_debug_btn.setEnabled(not enabled)
        self.disable_debug_btn.setEnabled(enabled)
