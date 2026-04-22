from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QStackedWidget, QVBoxLayout, QWidget, QMainWindow

from ui.pages.about_page import AboutPage
from ui.pages.debug_page import DebugPage
from ui.pages.devices_page import DevicesPage
from ui.pages.home_page import HomePage
from ui.pages.logs_page import LogsPage
from ui.pages.receive_page import ReceivePage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage
from ui.pages.transfers_page import TransfersPage
from ui.components.toast_popup import ToastPopup


class MainWindow(QMainWindow):
    def __init__(self, context, debug_peer: bool = False):
        super().__init__()
        self.context = context
        self.logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
        self.setWindowTitle("CrocDrop")
        self.resize(1320, 860)
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)

        brand_shell = QFrame()
        brand_shell.setObjectName("BrandShell")
        brand_layout = QHBoxLayout(brand_shell)
        brand_layout.setContentsMargins(8, 8, 8, 8)
        brand_layout.setSpacing(10)

        logo_widget = QSvgWidget(str(self.logo_path))
        logo_widget.setFixedSize(52, 52)

        brand_text = QVBoxLayout()
        brand_text.setContentsMargins(0, 0, 0, 0)
        brand_text.setSpacing(2)

        brand = QLabel("CrocDrop")
        brand.setObjectName("BrandTitle")
        tagline = QLabel("Lock. Send. Done.")
        tagline.setProperty("role", "muted")

        brand_text.addWidget(brand)
        brand_text.addWidget(tagline)
        brand_text.addStretch(1)

        brand_layout.addWidget(logo_widget)
        brand_layout.addLayout(brand_text, 1)

        mode = QLabel("Debug Peer Instance" if debug_peer else "Primary Instance")
        mode.setProperty("role", "muted")
        mode.setStyleSheet("padding-left:8px;padding-bottom:6px;")

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        for item in ["Home", "Send", "Receive", "Transfers", "Devices", "Logs", "Settings", "Debug", "About"]:
            self.nav.addItem(QListWidgetItem(item))

        side_layout.addWidget(brand_shell)
        side_layout.addWidget(mode)
        side_layout.addWidget(self.nav)
        side_layout.addStretch(1)

        panel = QFrame()
        panel.setObjectName("MainPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 14, 18, 14)

        header = QFrame()
        header.setObjectName("Card")
        header_layout = QHBoxLayout(header)
        title = QLabel("Context")
        title.setStyleSheet("font-size:16px;font-weight:700;")
        self.context_label = QLabel("Ready")
        self.context_label.setProperty("role", "muted")

        check_btn = QPushButton("Check Croc")
        check_btn.clicked.connect(self.check_croc)
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.context_label)
        header_layout.addWidget(check_btn)

        self.pages = QStackedWidget()
        self.home_page = HomePage(context)
        self.send_page = SendPage(context)
        self.receive_page = ReceivePage(context)
        self.transfers_page = TransfersPage(context)
        self.devices_page = DevicesPage(context)
        self.logs_page = LogsPage(context)
        self.settings_page = SettingsPage(context, QApplication.instance())
        self.debug_page = DebugPage(context)
        self.about_page = AboutPage()

        for page in [
            self.home_page,
            self.send_page,
            self.receive_page,
            self.transfers_page,
            self.devices_page,
            self.logs_page,
            self.settings_page,
            self.debug_page,
            self.about_page,
        ]:
            self.pages.addWidget(page)

        panel_layout.addWidget(header)
        panel_layout.addWidget(self.pages, 1)

        layout.addWidget(sidebar)
        layout.addWidget(panel, 1)

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.currentRowChanged.connect(self.on_page_changed)
        self.home_page.navigate_requested.connect(self.navigate_to)
        self.context.history_service.history_changed.connect(self.home_page.refresh)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)

        self.nav.setCurrentRow(0)
        self.check_croc()

    def navigate_to(self, page_name: str):
        mapping = {self.nav.item(i).text(): i for i in range(self.nav.count())}
        if page_name in mapping:
            self.nav.setCurrentRow(mapping[page_name])

    def on_page_changed(self, index: int):
        name = self.nav.item(index).text() if index >= 0 else ""
        self.context_label.setText(name)
        if name == "Home":
            self.home_page.refresh()
        elif name == "Transfers":
            self.transfers_page.refresh()
        elif name == "Devices":
            self.devices_page.refresh()

    def check_croc(self):
        info = self.context.croc_manager.detect_binary()
        self.context_label.setText(f"{info.source} | {info.version or 'missing'}")

    def on_transfer_finished(self, transfer_id: str, status: str):
        if status != "completed":
            return
        records = self.context.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record:
            return
        if record.direction not in {"receive", "selftest-receive"}:
            return
        message = "File download completed."
        if record.destination_folder:
            message = f"Saved to: {record.destination_folder}"
        ToastPopup("CrocDrop", message)
