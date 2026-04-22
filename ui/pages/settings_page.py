from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QMessageBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from ui.components.common import Card
from ui.theme import apply_theme


class SettingsPage(QWidget):
    def __init__(self, context, app):
        super().__init__()
        self.context = context
        self.app = app

        root = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        root.addWidget(title)

        card = Card("General")
        form = QFormLayout()

        settings = self.context.settings_service.get()

        self.download_folder = QLineEdit(settings.default_download_folder)
        browse_btn = QPushButton("Browse")
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.download_folder)
        folder_row.addWidget(browse_btn)
        folder_widget = QWidget()
        folder_widget.setLayout(folder_row)

        self.ask_before = QCheckBox()
        self.ask_before.setChecked(settings.ask_before_receiving)
        self.auto_open = QCheckBox()
        self.auto_open.setChecked(settings.auto_open_received_folder)
        self.remember_last = QCheckBox()
        self.remember_last.setChecked(settings.remember_last_folders)
        self.dark_mode = QCheckBox()
        self.dark_mode.setChecked(settings.dark_mode)
        self.debug_mode = QCheckBox()
        self.debug_mode.setChecked(settings.debug_mode)

        self.accent = QComboBox()
        self.accent.addItems(["#35c9a5", "#4ca3ff", "#f3c14b", "#ff6e6e"])
        self.accent.setCurrentText(settings.accent_color)

        self.relay_mode = QComboBox()
        self.relay_mode.addItems(["public", "custom"])
        self.relay_mode.setCurrentText(settings.relay_mode)
        self.custom_relay = QLineEdit(settings.custom_relay)

        self.binary_path = QLineEdit(settings.croc_binary_path)
        binary_btn = QPushButton("Browse Binary")
        delete_binary_btn = QPushButton("Delete Croc Binary")
        binary_row = QHBoxLayout()
        binary_row.addWidget(self.binary_path)
        binary_row.addWidget(binary_btn)
        binary_row.addWidget(delete_binary_btn)
        binary_widget = QWidget()
        binary_widget.setLayout(binary_row)

        self.log_retention = QSpinBox()
        self.log_retention.setRange(1, 120)
        self.log_retention.setValue(settings.log_retention_days)

        self.auto_download = QCheckBox()
        self.auto_download.setChecked(settings.auto_download_croc)

        form.addRow("Default download folder", folder_widget)
        form.addRow("Ask before receiving", self.ask_before)
        form.addRow("Auto-open received folder", self.auto_open)
        form.addRow("Remember last folders", self.remember_last)
        form.addRow("Dark mode", self.dark_mode)
        form.addRow("Accent color", self.accent)
        form.addRow("Relay mode", self.relay_mode)
        form.addRow("Custom relay", self.custom_relay)
        form.addRow("Croc binary path", binary_widget)
        form.addRow("Auto-download croc", self.auto_download)
        form.addRow("Log retention (days)", self.log_retention)
        form.addRow("Debug mode", self.debug_mode)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        card.layout.addLayout(form)
        card.layout.addWidget(save_btn)
        root.addWidget(card)

        account_card = Card("Account")
        self.current_profile_label = QLabel()
        self.profile_combo = QComboBox()
        self.switch_profile_btn = QPushButton("Switch Profile")
        self.remove_profile_btn = QPushButton("Remove Current Account")
        self.guest_mode_btn = QPushButton("Use Guest Mode")
        account_card.layout.addWidget(self.current_profile_label)
        account_card.layout.addWidget(self.profile_combo)
        account_card.layout.addWidget(self.switch_profile_btn)
        account_card.layout.addWidget(self.remove_profile_btn)
        account_card.layout.addWidget(self.guest_mode_btn)
        root.addWidget(account_card)
        root.addStretch(1)

        browse_btn.clicked.connect(self.pick_folder)
        binary_btn.clicked.connect(self.pick_binary)
        delete_binary_btn.clicked.connect(self.delete_binary)
        save_btn.clicked.connect(self.save)
        self.switch_profile_btn.clicked.connect(self.switch_profile)
        self.remove_profile_btn.clicked.connect(self.remove_current_profile)
        self.guest_mode_btn.clicked.connect(self.set_guest_mode)
        self.refresh_account_section()

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
        s.debug_mode = self.debug_mode.isChecked()
        self.context.settings_service.save(s)
        self.context.log_service.prune_old_logs(s.log_retention_days)
        apply_theme(self.app, s)
        self.refresh_account_section()

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
