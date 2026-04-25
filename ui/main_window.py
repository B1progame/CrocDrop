from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    Property,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    QSignalBlocker,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
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
)

from ui.components.theme_switcher import ThemeSwitcher
from ui.components.toast_popup import ToastPopup
from ui.pages.about_page import AboutPage
from ui.pages.debug_page import DebugPage
from ui.pages.devices_page import DevicesPage
from ui.pages.home_page import HomePage
from ui.pages.logs_page import LogsPage
from ui.pages.profile_page import ProfilePage
from ui.pages.receive_page import ReceivePage
from ui.pages.send_page import SendPage
from ui.pages.settings_page import SettingsPage
from ui.pages.transfers_page import TransfersPage
from ui.theme import apply_theme


class SidebarActiveIndicator(QWidget):
    def __init__(self, parent: QWidget, dark_mode: bool):
        super().__init__(parent)
        self._radius = 10.0
        self._dark_mode = dark_mode
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAutoFillBackground(False)
        self.hide()

    def get_radius(self) -> float:
        return self._radius

    def set_radius(self, radius: float) -> None:
        self._radius = max(0.0, float(radius))
        self.update()

    radius = Property(float, get_radius, set_radius)

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self.update()

    def paintEvent(self, _event) -> None:
        if self.width() <= 1 or self.height() <= 1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        gradient = QLinearGradient(0, 0, max(1, self.width()), max(1, self.height()))
        if self._dark_mode:
            gradient.setColorAt(0.0, QColor(79, 42, 144, 132))
            gradient.setColorAt(0.58, QColor(140, 69, 255, 132))
            gradient.setColorAt(1.0, QColor(245, 139, 198, 126))
            border = QColor(255, 255, 255, 34)
        else:
            gradient.setColorAt(0.0, QColor(106, 69, 204, 92))
            gradient.setColorAt(0.6, QColor(155, 92, 255, 96))
            gradient.setColorAt(1.0, QColor(232, 115, 180, 92))
            border = QColor(255, 255, 255, 96)

        painter.setBrush(gradient)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(rect, self._radius, self._radius)


class MainWindow(QMainWindow):
    def __init__(self, context, debug_peer: bool = False):
        super().__init__()
        self.context = context
        self.debug_enabled = bool(self.context.settings_service.get().debug_mode or debug_peer)
        self.logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
        self.icon_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
        self._nav_icon_names: dict[str, str] = {
            "Home": "nav_home.svg",
            "Send": "nav_send.svg",
            "Receive": "nav_receive.svg",
            "Transfers": "nav_transfers.svg",
            "Devices": "nav_devices.svg",
            "Logs": "nav_logs.svg",
            "Settings": "nav_settings.svg",
            "Debug": "nav_debug.svg",
            "About": "nav_about.svg",
        }
        self._footer_icon_names: dict[str, str] = {
            "Settings": "nav_settings.svg",
            "About": "nav_about.svg",
            "Profile": "nav_profile.svg",
        }
        self._sidebar_svg_cache: dict[Path, str] = {}
        self._sidebar_icon_cache: dict[tuple[str, str, int], QIcon] = {}
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

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(236)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)

        brand_shell = QFrame()
        brand_shell.setObjectName("BrandShell")
        brand_layout = QVBoxLayout(brand_shell)
        brand_layout.setContentsMargins(10, 10, 10, 10)
        brand_layout.setSpacing(8)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        brand = QLabel("CrocDrop")
        brand.setObjectName("BrandTitle")
        tagline = QLabel("Lock. Send. Done.")
        tagline.setProperty("role", "muted")
        text_col.addWidget(brand)
        text_col.addWidget(tagline)

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

        brand_layout.addLayout(text_col)
        brand_layout.addLayout(badges)

        mode = QLabel("Debug Peer Instance" if debug_peer else "Primary Instance")
        mode.setProperty("role", "muted")
        mode.setContentsMargins(8, 0, 0, 2)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setUniformItemSizes(True)
        self.nav.setIconSize(QSize(20, 20))
        self._build_nav_items()
        self.footer_buttons: dict[str, QPushButton] = {}
        self.sidebar_footer = self._build_sidebar_footer()
        current_settings = self.context.settings_service.get()
        self.theme_switcher = ThemeSwitcher(
            icon_dir=self.icon_dir,
            theme_mode=current_settings.theme_mode,
            dark_mode=current_settings.dark_mode,
        )
        self.theme_switcher.themeChanged.connect(self._on_sidebar_theme_changed)
        self.sidebar_footer_section = self._build_sidebar_footer_section()

        # Sidebar bug fix: the previous layout added a bottom stretch, which consumed free height and kept
        # navigation items cramped near the top. Giving nav stretch=1 lets it use full height and scroll only if needed.
        side_layout.addWidget(brand_shell)
        side_layout.addWidget(mode)
        side_layout.addWidget(self.nav, 1)
        side_layout.addWidget(self.sidebar_footer_section)

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
        self.profile_page = ProfilePage(context)

        self.page_map: dict[str, QWidget] = {
            "Home": self.home_page,
            "Send": self.send_page,
            "Receive": self.receive_page,
            "Transfers": self.transfers_page,
            "Devices": self.devices_page,
            "Logs": self.logs_page,
            "Settings": self.settings_page,
            "About": self.about_page,
            "Profile": self.profile_page,
        }
        if self.debug_enabled:
            self.page_map["Debug"] = self.debug_page

        self.page_indices: dict[str, int] = {}
        self.nav_rows: dict[str, int] = {}
        for label in self._page_labels():
            page = self.page_map.get(label)
            if page is not None:
                self.page_indices[label] = self.pages.count()
                self.pages.addWidget(page)
        self.nav_rows = {self.nav.item(i).text(): i for i in range(self.nav.count())}

        panel_layout.addWidget(header)
        panel_layout.addWidget(self.pages, 1)

        shell_layout.addWidget(self.sidebar)
        shell_layout.addWidget(panel, 1)

        self.nav.currentRowChanged.connect(self._on_nav_row_changed)
        self.nav.verticalScrollBar().valueChanged.connect(lambda _: self._sync_nav_indicator(animated=False))
        self.nav.viewport().installEventFilter(self)
        self.sidebar.installEventFilter(self)
        self.sidebar_footer.installEventFilter(self)
        for button in self.footer_buttons.values():
            button.installEventFilter(self)
        self._active_page_name = ""
        self._nav_indicator_anim: QVariantAnimation | None = None
        self._nav_indicator_settle_anim: QVariantAnimation | None = None
        self.nav_indicator = SidebarActiveIndicator(self.sidebar, self.context.settings_service.get().dark_mode)
        self.nav_indicator.setObjectName("NavIndicator")
        self.home_page.navigate_requested.connect(self.navigate_to)
        self.profile_page.navigate_requested.connect(self.navigate_to)
        self.settings_page.settings_changed.connect(self._on_settings_changed)
        try:
            QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_system_color_scheme_changed)
        except Exception:
            pass
        self.context.history_service.history_changed.connect(self.home_page.refresh)
        self.context.transfer_service.transfer_finished.connect(self.on_transfer_finished)

        self.navigate_to("Home", animated=False)
        self.check_croc()

    def eventFilter(self, watched, event):
        if not hasattr(self, "nav_indicator"):
            return super().eventFilter(watched, event)
        watched_widgets = [
            self.nav.viewport(),
            getattr(self, "sidebar", None),
            getattr(self, "sidebar_footer", None),
            *getattr(self, "footer_buttons", {}).values(),
        ]
        if watched in watched_widgets and event.type() in {QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest, QEvent.Type.Move}:
            self._sync_nav_indicator(animated=False)
        return super().eventFilter(watched, event)

    def _main_nav_labels(self) -> list[str]:
        labels = ["Home", "Send", "Receive", "Transfers", "Devices", "Logs"]
        if self.debug_enabled:
            labels.append("Debug")
        return labels

    def _page_labels(self) -> list[str]:
        return [*self._main_nav_labels(), "Settings", "About", "Profile"]

    def _build_nav_items(self) -> None:
        for label in self._main_nav_labels():
            icon_name = self._nav_icon_names[label]
            icon_path = self.icon_dir / icon_name
            icon = self._sidebar_svg_icon(icon_path, active=False) if icon_path.exists() else QIcon()
            item = QListWidgetItem(icon, label)
            self.nav.addItem(item)

    def _build_sidebar_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("SidebarFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        for label, icon_name in self._footer_icon_names.items():
            button = QPushButton()
            button.setObjectName("SidebarFooterButton")
            button.setCheckable(True)
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setFixedSize(46, 46)
            button.setIconSize(QSize(20, 20))
            icon_path = self.icon_dir / icon_name
            if icon_path.exists():
                button.setIcon(self._sidebar_svg_icon(icon_path, active=False))
            button.clicked.connect(lambda _checked=False, page=label: self.navigate_to(page))
            layout.addWidget(button)
            self.footer_buttons[label] = button

        return footer

    def _build_sidebar_footer_section(self) -> QWidget:
        section = QWidget()
        section.setObjectName("SidebarFooterCluster")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.theme_switcher, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.sidebar_footer)
        return section

    def navigate_to(self, page_name: str, animated: bool = True):
        self._show_page(page_name, animated=animated, sync_nav=True)

    def _on_nav_row_changed(self, index: int):
        if index < 0:
            return
        item = self.nav.item(index)
        if item is None:
            return
        self._show_page(item.text(), animated=True, sync_nav=False)

    def _show_page(self, name: str, animated: bool = True, sync_nav: bool = True):
        if name not in self.page_indices:
            return
        self._active_page_name = name

        if sync_nav:
            with QSignalBlocker(self.nav):
                if name in self.nav_rows:
                    self.nav.setCurrentRow(self.nav_rows[name])
                else:
                    self.nav.clearSelection()
                    self.nav.setCurrentRow(-1)
                    self.nav.setCurrentItem(None)
                    if self.nav.selectionModel() is not None:
                        self.nav.selectionModel().clearCurrentIndex()

        page_index = self.page_indices[name]
        if self.pages.currentIndex() != page_index:
            self._clear_page_effects()
            self.pages.setCurrentIndex(page_index)

        self._update_page_chrome(name)
        self._sync_footer_buttons(name)
        self._refresh_sidebar_icons()
        self._sync_nav_indicator(animated=animated)

    def _update_page_chrome(self, name: str):
        self.header_title.setText(name or "CrocDrop")
        self.context_label.setText(name or "Ready")
        if name == "Home":
            self.home_page.refresh()
        elif name == "Transfers":
            self.transfers_page.refresh()
        elif name == "Devices":
            self.devices_page.refresh()
        elif name == "Settings":
            self.settings_page.refresh_account_section()
            self.settings_page.refresh_debug_controls()
        elif name == "Profile":
            self.profile_page.refresh()
        self._refresh_identity_surfaces()

    def _sync_footer_buttons(self, active_page: str) -> None:
        for page, button in self.footer_buttons.items():
            button.setChecked(page == active_page)

    def _refresh_identity_surfaces(self) -> None:
        current_profile = self.context.settings_service.get().current_profile.strip() or "Guest"
        self.user_badge.setText(f"User: {current_profile}")

    def _on_settings_changed(self) -> None:
        settings = self.context.settings_service.get()
        self._refresh_identity_surfaces()
        self.nav_indicator.set_dark_mode(settings.dark_mode)
        self.theme_switcher.set_dark_mode(settings.dark_mode)
        self.theme_switcher.set_theme_mode(settings.theme_mode, animated=False, emit_signal=False)
        self._refresh_sidebar_icons()
        self.settings_page.refresh_theme_mode_control()
        if self.pages.currentWidget() is self.profile_page:
            self.profile_page.refresh()

    def _on_sidebar_theme_changed(self, theme_mode: str) -> None:
        settings = self.context.settings_service.get()
        settings.theme_mode = theme_mode
        apply_theme(QApplication.instance(), settings)
        self.context.settings_service.save(settings)
        self._on_settings_changed()

    def _on_system_color_scheme_changed(self, _scheme) -> None:
        settings = self.context.settings_service.get()
        if settings.theme_mode != "system":
            return
        apply_theme(QApplication.instance(), settings)
        self.context.settings_service.save(settings)
        self._on_settings_changed()

    def _clear_page_effects(self) -> None:
        for page in self.page_map.values():
            try:
                if page.graphicsEffect() is not None:
                    page.setGraphicsEffect(None)
            except RuntimeError:
                continue

    def _sync_nav_indicator(self, animated: bool) -> None:
        target = self._indicator_target_for_page(self._active_page_name)
        if target is None:
            self.nav_indicator.hide()
            return

        target_rect, target_radius = target
        was_hidden = self.nav_indicator.isHidden() or self.nav_indicator.geometry().isNull()
        self.nav_indicator.show()
        self.nav_indicator.raise_()

        if not animated or was_hidden:
            self._stop_nav_indicator_animations()
            self.nav_indicator.setGeometry(target_rect)
            self.nav_indicator.set_radius(target_radius)
            return

        if self.nav_indicator.geometry() == target_rect and abs(self.nav_indicator.radius - target_radius) < 0.2:
            return

        self._animate_nav_indicator_to(target_rect, target_radius)

    def _indicator_target_for_page(self, page_name: str) -> tuple[QRect, float] | None:
        if page_name in self.nav_rows:
            row = self.nav_rows[page_name]
            item = self.nav.item(row)
            if item is None:
                return None
            rect = self.nav.visualItemRect(item)
            if not rect.isValid():
                return None
            top_left = self.nav.viewport().mapTo(self.sidebar, rect.topLeft())
            target = QRect(top_left.x() + 4, top_left.y() + 2, max(12, rect.width() - 8), max(12, rect.height() - 4))
            return target, 10.0

        button = self.footer_buttons.get(page_name)
        if button is None:
            return None
        top_left = button.mapTo(self.sidebar, button.rect().topLeft())
        target = QRect(top_left.x(), top_left.y(), button.width(), button.height())
        return target, min(target.width(), target.height()) / 2.0

    def _stop_nav_indicator_animations(self) -> None:
        for anim_name in ("_nav_indicator_anim", "_nav_indicator_settle_anim"):
            anim = getattr(self, anim_name, None)
            if anim:
                anim.stop()
                anim.deleteLater()
                setattr(self, anim_name, None)

    def _animate_nav_indicator_to(self, target_rect: QRect, target_radius: float) -> None:
        self._stop_nav_indicator_animations()
        start_rect = QRect(self.nav_indicator.geometry())
        start_radius = self.nav_indicator.radius
        dx = target_rect.center().x() - start_rect.center().x()
        dy = target_rect.center().y() - start_rect.center().y()
        distance = math.hypot(dx, dy)
        size_delta = abs(target_rect.width() - start_rect.width()) + abs(target_rect.height() - start_rect.height())
        duration = min(320, max(190, int(170 + distance * 0.22 + size_delta * 0.18)))

        self._nav_indicator_anim = QVariantAnimation(self)
        self._nav_indicator_anim.setDuration(duration)
        self._nav_indicator_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_indicator_anim.setStartValue(0.0)
        self._nav_indicator_anim.setEndValue(1.0)

        def _step(value: float) -> None:
            t = float(value)
            rect = self._interpolate_rect(start_rect, target_rect, t)
            radius = start_radius + (target_radius - start_radius) * t
            self.nav_indicator.setGeometry(rect)
            self.nav_indicator.set_radius(radius)
            self.nav_indicator.raise_()

        def _finish() -> None:
            self.nav_indicator.setGeometry(target_rect)
            self.nav_indicator.set_radius(target_radius)
            self._start_nav_indicator_settle(target_rect, target_radius, dx, dy)

        self._nav_indicator_anim.valueChanged.connect(_step)
        self._nav_indicator_anim.finished.connect(_finish)
        self._nav_indicator_anim.start()

    def _start_nav_indicator_settle(self, target_rect: QRect, target_radius: float, dx: float, dy: float) -> None:
        distance = math.hypot(dx, dy)
        if distance <= 0.5:
            return
        unit_x = dx / distance
        unit_y = dy / distance
        amplitude = min(2.6, max(0.8, distance * 0.012))

        self._nav_indicator_settle_anim = QVariantAnimation(self)
        self._nav_indicator_settle_anim.setDuration(135)
        self._nav_indicator_settle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._nav_indicator_settle_anim.setStartValue(0.0)
        self._nav_indicator_settle_anim.setEndValue(1.0)

        def _step(value: float) -> None:
            t = float(value)
            damped = math.sin(t * math.pi * 2.0) * (1.0 - t)
            offset_x = unit_x * amplitude * damped
            offset_y = unit_y * amplitude * damped
            scale = 1.0 + 0.012 * damped
            width = max(12, target_rect.width() * scale)
            height = max(12, target_rect.height() * (1.0 - 0.006 * damped))
            center_x = target_rect.center().x() + offset_x
            center_y = target_rect.center().y() + offset_y
            rect = QRect(
                round(center_x - width / 2.0),
                round(center_y - height / 2.0),
                round(width),
                round(height),
            )
            self.nav_indicator.setGeometry(rect)
            self.nav_indicator.set_radius(target_radius * min(width / target_rect.width(), height / target_rect.height()))
            self.nav_indicator.raise_()

        def _finish() -> None:
            self.nav_indicator.setGeometry(target_rect)
            self.nav_indicator.set_radius(target_radius)

        self._nav_indicator_settle_anim.valueChanged.connect(_step)
        self._nav_indicator_settle_anim.finished.connect(_finish)
        self._nav_indicator_settle_anim.start()

    def _refresh_sidebar_icons(self) -> None:
        for label, icon_name in self._nav_icon_names.items():
            row = self.nav_rows.get(label)
            if row is None:
                continue
            item = self.nav.item(row)
            if item is None:
                continue
            icon_path = self.icon_dir / icon_name
            if not icon_path.exists():
                continue
            item.setIcon(self._sidebar_svg_icon(icon_path, active=(label == self._active_page_name)))

        for label, icon_name in self._footer_icon_names.items():
            button = self.footer_buttons.get(label)
            if button is None:
                continue
            icon_path = self.icon_dir / icon_name
            if not icon_path.exists():
                continue
            button.setIcon(self._sidebar_svg_icon(icon_path, active=(label == self._active_page_name)))

    def _sidebar_svg_icon(self, icon_path: Path, active: bool, size: int = 20) -> QIcon:
        color = self._sidebar_icon_color(active)
        cache_key = (str(icon_path), color, size)
        cached = self._sidebar_icon_cache.get(cache_key)
        if cached is not None:
            return cached

        svg_text = self._sidebar_svg_cache.get(icon_path)
        if svg_text is None:
            svg_text = icon_path.read_text(encoding="utf-8")
            self._sidebar_svg_cache[icon_path] = svg_text

        svg_text = (
            svg_text.replace("currentColor", color)
            .replace("#9FB0C8", color)
            .replace("#9fb0c8", color)
        )
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        device_ratio = 2.0
        pixmap = QPixmap(round(size * device_ratio), round(size * device_ratio))
        pixmap.setDevicePixelRatio(device_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()

        icon = QIcon(pixmap)
        self._sidebar_icon_cache[cache_key] = icon
        return icon

    def _sidebar_icon_color(self, active: bool) -> str:
        if self.context.settings_service.get().dark_mode:
            return "#ffffff" if active else "#9fb0c8"
        return "#0f1726" if active else "#2a3a4f"

    @staticmethod
    def _interpolate_rect(start: QRect, end: QRect, t: float) -> QRect:
        return QRect(
            round(start.x() + (end.x() - start.x()) * t),
            round(start.y() + (end.y() - start.y()) * t),
            round(start.width() + (end.width() - start.width()) * t),
            round(start.height() + (end.height() - start.height()) * t),
        )

    def check_croc(self):
        info = self.context.croc_manager.detect_binary()
        self.context_label.setText(f"{info.source} | {info.version or 'missing'}")

    def on_transfer_finished(self, transfer_id: str, status: str):
        if status != "completed":
            return
        record = self.context.transfer_service.get_record(transfer_id)
        if not record:
            return
        if record.direction not in {"receive", "selftest-receive"}:
            return
        message = "File download completed."
        if record.destination_folder:
            message = f"Saved to: {record.destination_folder}"
        ToastPopup("CrocDrop", message)
