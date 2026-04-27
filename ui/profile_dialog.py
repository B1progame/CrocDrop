from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QComboBox,
    QVBoxLayout,
)


class ProfileDialog(QDialog):
    def __init__(self, profiles: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("CrocDrop Profile")
        self.setModal(True)
        self.resize(460, 220)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self.selected_profile: str = ""
        self.use_guest: bool = False

        root = QVBoxLayout(self)
        title = QLabel("Choose your profile")
        title.setStyleSheet("font-size:18px;font-weight:700;")
        sub = QLabel("Create an account profile for auto-login, or continue as guest.")
        root.addWidget(title)
        root.addWidget(sub)

        self.combo = QComboBox()
        self.combo.addItems(profiles)
        login_btn = QPushButton("Login With Selected Profile")

        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText("New profile name")
        create_btn = QPushButton("Create Profile and Login")

        guest_btn = QPushButton("Login as Guest")

        row1 = QHBoxLayout()
        row1.addWidget(self.combo)
        row1.addWidget(login_btn)

        row2 = QHBoxLayout()
        row2.addWidget(self.new_name)
        row2.addWidget(create_btn)

        root.addLayout(row1)
        root.addLayout(row2)
        root.addWidget(guest_btn)

        login_btn.clicked.connect(self.login_existing)
        create_btn.clicked.connect(self.create_profile)
        guest_btn.clicked.connect(self.login_guest)

    def login_existing(self):
        profile = self.combo.currentText().strip()
        if not profile:
            QMessageBox.warning(self, "Profile", "No saved profile available.")
            return
        self.selected_profile = profile
        self.use_guest = False
        self.accept()

    def create_profile(self):
        profile = self.new_name.text().strip()
        if not profile:
            QMessageBox.warning(self, "Profile", "Enter a profile name.")
            return
        self.selected_profile = profile
        self.use_guest = False
        self.accept()

    def login_guest(self):
        self.selected_profile = ""
        self.use_guest = True
        self.accept()
