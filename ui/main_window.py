from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QIcon
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from ui.components.toast_popup import ToastPopup
from ui.pages.about_page import AboutPage
from ui.pages.debug_page import DebugPage
from ui.pages.devices_page import DevicesPage
from ui.pages.home_page import HomePage
from ui.pages.logs_page import LogsPage
from ui.pages.receive_page import ReceivePage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage
from ui.pages.transfers_page import TransfersPage


class MainWindow(QMainWindow):
    def __init__(self, context, debug_peer: bool = False):
        super().__init__()
        self.context = context
        self.logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
        self.icon_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
        self.setWindowTitle("CrocDrop")
        self.resize(1320, 860)
        self.setMinimumSize(1060, 720)
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))

        root = QWidget()
        self.setCentralWidget(root)
        shell_layout = QHBoxLayout(root)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)

        brand_shell = QFrame()
        brand_shell.setObjectName("BrandShell")
        brand_layout = QVBoxLayout(brand_shell)
        brand_layout.setContentsMargins(10, 10, 10, 10)
        brand_layout.setSpacing(10)

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.setSpacing(10)

        logo_pill = QFrame()
        logo_pill.setObjectName("LogoPill")
        logo_pill_layout = QVBoxLayout(logo_pill)
        logo_pill_layout.setContentsMargins(6, 6, 6, 6)
        logo_widget = QSvgWidget(str(self.logo_path))
        logo_widget.setFixedSize(42, 42)
        logo_pill_layout.addWidget(logo_widget)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        brand = QLabel("CrocDrop")
        brand.setObjectName("BrandTitle")
        tagline = QLabel("Lock. Send. Done.")
        tagline.setProperty("role", "muted")
        text_col.addWidget(brand)
        text_col.addWidget(tagline)

        logo_row.addWidget(logo_pill, 0, Qt.AlignmentFlag.AlignTop)
        logo_row.addLayout(text_col, 1)

        badges = QHBoxLayout()
        badges.setContentsMargins(0, 0, 0, 0)
        badges.setSpacing(8)
        current_profile = self.context.settings_service.get().current_profile.strip() or "Guest"
        self.user_badge = QLabel(f"User: {current_profile}")
        self.user_badge.setObjectName("SidebarBadge")
        self.mode_badge = QLabel("Debug" if debug_peer else "Primary")
        self.mode_badge.setObjectName("SidebarBadge")
        badges.addWidget(self.user_badge)
        badges.addWidget(self.mode_badge)
        badges.addStretch(1)

        brand_layout.addLayout(logo_row)
        brand_layout.addLayout(badges)

        mode = QLabel("Debug Peer Instance" if debug_peer else "Primary Instance")
        mode.setProperty("role", "muted")
        mode.setContentsMargins(8, 0, 0, 2)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setUniformItemSizes(True)
        self._build_nav_items()

        # Sidebar bug fix: the previous layout added a bottom stretch, which consumed free height and kept
        # navigation items cramped near the top. Giving nav stretch=1 lets it use full height and scroll only if needed.
        side_layout.addWidget(brand_shell)
        side_layout.addWidget(mode)
        side_layout.addWidget(self.nav, 1)

        panel = QFrame()
        panel.setObjectName("MainPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 14, 18, 14)
        panel_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)
        self.header_title = QLabel("Home")
        self.header_title.setObjectName("HeaderTitle")
        self.context_label = QLabel("Ready")
        self.context_label.setObjectName("HeaderStatus")

        check_btn = QPushButton("Check Croc")
        check_btn.clicked.connect(self.check_croc)
        header_layout.addWidget(self.header_title)
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

        shell_layout.addWidget(sidebar)
        shell_layout.addWidget(panel, 1)

        self.nav.currentRowChanged.connect(self.switch_page)
        self.nav.currentRowChanged.connect(self.on_page_changed)
        self.nav.currentRowChanged.connect(lambda _: self._sync_nav_indicator(animated=True))
        self.nav.verticalScrollBar().valueChanged.connect(lambda _: self._sync_nav_indicator(animated=False))
        self.nav.viewport().installEventFilter(self)
        self._nav_indicator_anim: QPropertyAnimation | None = None
        self._page_fade_anim: QPropertyAnimation | None = None
        self.nav_indicator = QFrame(self.nav.viewport())
        self.nav_indicator.setObjectName("NavIndicator")
        self.nav_indicator.hide()
        self.nav_indicator.lower()
        self.home_page.navigate_requested.connect(self.navigate_to)
        self.context.history_service.history_changed.connect(self.home_page.refresh)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)

        self.nav.setCurrentRow(0)
        self._sync_nav_indicator(animated=False)
        self.check_croc()

    def eventFilter(self, watched, event):
        if watched is self.nav.viewport() and event.type() in {QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest}:
            self._sync_nav_indicator(animated=False)
        return super().eventFilter(watched, event)

    def _build_nav_items(self) -> None:
        items: list[tuple[str, str]] = [
            ("Home", "nav_home.svg"),
            ("Send", "nav_send.svg"),
            ("Receive", "nav_receive.svg"),
            ("Transfers", "nav_transfers.svg"),
            ("Devices", "nav_devices.svg"),
            ("Logs", "nav_logs.svg"),
            ("Settings", "nav_settings.svg"),
            ("Debug", "nav_debug.svg"),
            ("About", "nav_about.svg"),
        ]
        for label, icon_name in items:
            icon_path = self.icon_dir / icon_name
            icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
            item = QListWidgetItem(icon, label)
            self.nav.addItem(item)

    def navigate_to(self, page_name: str):
        mapping = {self.nav.item(i).text(): i for i in range(self.nav.count())}
        if page_name in mapping:
            self.nav.setCurrentRow(mapping[page_name])

    def on_page_changed(self, index: int):
        name = self.nav.item(index).text() if index >= 0 else ""
        self.header_title.setText(name or "CrocDrop")
        self.context_label.setText(name or "Ready")
        if name == "Home":
            self.home_page.refresh()
        elif name == "Transfers":
            self.transfers_page.refresh()
        elif name == "Devices":
            self.devices_page.refresh()

    def switch_page(self, index: int) -> None:
        if index < 0:
            return
        if self.pages.currentIndex() == index:
            return
        self.pages.setCurrentIndex(index)
        self._fade_current_page()

    def _fade_current_page(self) -> None:
        widget = self.pages.currentWidget()
        if widget is None:
            return
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)
        self._page_fade_anim = QPropertyAnimation(effect, b"opacity", self)
        self._page_fade_anim.setDuration(180)
        self._page_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._page_fade_anim.setStartValue(0.0)
        self._page_fade_anim.setEndValue(1.0)

        def _cleanup():
            widget.setGraphicsEffect(None)
            effect.deleteLater()

        self._page_fade_anim.finished.connect(_cleanup)
        self._page_fade_anim.start()

    def _sync_nav_indicator(self, animated: bool) -> None:
        row = self.nav.currentRow()
        if row < 0 or row >= self.nav.count():
            self.nav_indicator.hide()
            return
        item = self.nav.item(row)
        rect = self.nav.visualItemRect(item)
        if not rect.isValid():
            self.nav_indicator.hide()
            return

        target = QRect(rect.x() + 4, rect.y() + 2, max(12, rect.width() - 8), max(12, rect.height() - 4))
        self.nav_indicator.show()
        self.nav_indicator.lower()

        if not animated or self.nav_indicator.geometry().isNull():
            self.nav_indicator.setGeometry(target)
            return

        if self._nav_indicator_anim:
            self._nav_indicator_anim.stop()
            self._nav_indicator_anim.deleteLater()
        self._nav_indicator_anim = QPropertyAnimation(self.nav_indicator, b"geometry", self)
        self._nav_indicator_anim.setDuration(180)
        self._nav_indicator_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_indicator_anim.setStartValue(self.nav_indicator.geometry())
        self._nav_indicator_anim.setEndValue(target)
        self._nav_indicator_anim.start()

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
