from __future__ import annotations

import platform
import socket

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.version import APP_VERSION
from ui.components.common import Card, PageHeader


class ProfilePage(QWidget):
    navigate_requested = Signal(str)
    settings_category_requested = Signal(str)

    def __init__(self, context):
        super().__init__()
        self.context = context

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("Profile", "Local identity and device context for this CrocDrop install."))

        hero = QFrame()
        hero.setObjectName("ProfileHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(14)

        self.avatar = QLabel("G")
        self.avatar.setObjectName("ProfileAvatar")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFixedSize(58, 58)

        identity = QVBoxLayout()
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(4)
        self.display_name = QLabel("Guest")
        self.display_name.setObjectName("ProfileName")
        self.profile_caption = QLabel("Local guest profile")
        self.profile_caption.setProperty("role", "muted")
        identity.addWidget(self.display_name)
        identity.addWidget(self.profile_caption)

        hero_layout.addWidget(self.avatar)
        hero_layout.addLayout(identity, 1)

        manage_btn = QPushButton("Manage Profile")
        manage_btn.setObjectName("PrimaryButton")
        manage_btn.clicked.connect(lambda: self.settings_category_requested.emit("profiles"))
        hero_layout.addWidget(manage_btn)

        details = Card("Local Profile Details")
        details_grid = QGridLayout()
        details_grid.setContentsMargins(0, 2, 0, 0)
        details_grid.setHorizontalSpacing(18)
        details_grid.setVerticalSpacing(10)
        self.profile_mode = QLabel()
        self.saved_profiles = QLabel()
        self.download_folder = QLabel()
        self.engine_status = QLabel()
        self.device_name = QLabel()
        self.platform_label = QLabel()
        self.app_version = QLabel(f"CrocDrop {APP_VERSION}")
        rows = [
            ("Profile mode", self.profile_mode),
            ("Saved profiles", self.saved_profiles),
            ("Default download folder", self.download_folder),
            ("Croc engine", self.engine_status),
            ("Device", self.device_name),
            ("Platform", self.platform_label),
            ("App version", self.app_version),
        ]
        for row, (label_text, value_label) in enumerate(rows):
            label = QLabel(label_text)
            label.setObjectName("SettingLabel")
            value_label.setObjectName("SettingDescription")
            value_label.setWordWrap(True)
            details_grid.addWidget(label, row, 0)
            details_grid.addWidget(value_label, row, 1)
        details_grid.setColumnMinimumWidth(0, 170)
        details_grid.setColumnStretch(1, 1)
        details.layout.addLayout(details_grid)

        shortcuts = Card("Profile Shortcuts")
        shortcut_row = QHBoxLayout()
        shortcut_row.setContentsMargins(0, 0, 0, 0)
        shortcut_row.setSpacing(10)
        settings_btn = QPushButton("Settings")
        devices_btn = QPushButton("Trusted Devices")
        about_btn = QPushButton("About CrocDrop")
        settings_btn.clicked.connect(lambda: self.navigate_requested.emit("Settings"))
        devices_btn.clicked.connect(lambda: self.navigate_requested.emit("Devices"))
        about_btn.clicked.connect(lambda: self.navigate_requested.emit("About"))
        shortcut_row.addWidget(settings_btn)
        shortcut_row.addWidget(devices_btn)
        shortcut_row.addWidget(about_btn)
        shortcut_row.addStretch(1)
        shortcuts.layout.addLayout(shortcut_row)

        root.addWidget(hero)
        root.addWidget(details)
        root.addWidget(shortcuts)
        root.addStretch(1)

    def refresh(self) -> None:
        settings = self.context.settings_service.get()
        profile = settings.current_profile.strip()
        display = profile or "Guest"
        self.display_name.setText(display)
        self.avatar.setText(display[:1].upper())
        self.profile_caption.setText("Saved local profile" if profile else "Local guest profile")
        self.profile_mode.setText("Saved profile" if profile else "Guest mode")
        self.saved_profiles.setText(str(len(settings.profiles)))
        self.download_folder.setText(settings.default_download_folder or "Not configured")

        info = self.context.croc_manager.detect_binary()
        self.engine_status.setText(f"{info.source} | {info.version or 'missing'}")
        self.device_name.setText(socket.gethostname() or "Unknown device")
        self.platform_label.setText(platform.platform())
