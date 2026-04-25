from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QEasingCurve, QRect, QRectF, QSize, QSignalBlocker, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from ui.theme import (
    THEME_DARK,
    THEME_LIGHT,
    THEME_MODE_OPTIONS,
    THEME_SYSTEM,
    accent_gradient_stops,
    normalize_accent_color,
    normalize_theme_mode,
)


class ThemeSwitcherIndicator(QWidget):
    def __init__(self, parent: QWidget, dark_mode: bool, accent_color: str):
        super().__init__(parent)
        self._dark_mode = dark_mode
        self._accent_color = normalize_accent_color(accent_color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def set_dark_mode(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self.update()

    def set_accent_color(self, accent_color: str) -> None:
        self._accent_color = normalize_accent_color(accent_color)
        self.update()

    def paintEvent(self, _event) -> None:
        if self.width() <= 1 or self.height() <= 1:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(rect.width(), rect.height()) / 2.0

        shadow_rect = rect.adjusted(0.0, 1.25, 0.0, 1.25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(7, 12, 20, 34 if self._dark_mode else 18))
        painter.drawRoundedRect(shadow_rect, radius, radius)

        gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        start, middle, end = accent_gradient_stops(self._accent_color, self._dark_mode)
        if self._dark_mode:
            start_color = QColor(start)
            middle_color = QColor(middle)
            end_color = QColor(end)
            start_color.setAlpha(214)
            middle_color.setAlpha(224)
            end_color.setAlpha(208)
            gradient.setColorAt(0.0, start_color)
            gradient.setColorAt(0.58, middle_color)
            gradient.setColorAt(1.0, end_color)
            border = QColor(255, 255, 255, 44)
        else:
            start_color = QColor(start)
            middle_color = QColor(middle)
            end_color = QColor(end)
            start_color.setAlpha(150)
            middle_color.setAlpha(168)
            end_color.setAlpha(156)
            gradient.setColorAt(0.0, start_color)
            gradient.setColorAt(0.58, middle_color)
            gradient.setColorAt(1.0, end_color)
            border = QColor(255, 255, 255, 128)

        painter.setBrush(gradient)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(rect, radius, radius)

        highlight = QRectF(rect).adjusted(1.25, 1.1, -1.25, -rect.height() * 0.42)
        highlight_radius = max(4.0, radius - 2.0)
        highlight_gradient = QLinearGradient(highlight.left(), highlight.top(), highlight.left(), highlight.bottom())
        highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 58 if self._dark_mode else 76))
        highlight_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(highlight_gradient)
        painter.drawRoundedRect(highlight, highlight_radius, highlight_radius)


class ThemeSwitcher(QFrame):
    themeChanged = Signal(str)

    def __init__(
        self,
        icon_dir: Path,
        theme_mode: str,
        dark_mode: bool,
        accent_color: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.icon_dir = Path(icon_dir)
        self._theme_mode = normalize_theme_mode(theme_mode, dark_mode)
        self._dark_mode = bool(dark_mode)
        self._accent_color = normalize_accent_color(accent_color)
        self._svg_cache: dict[Path, str] = {}
        self._slide_anim: QVariantAnimation | None = None
        self._settle_anim: QVariantAnimation | None = None
        self._option_icons = {
            THEME_DARK: self.icon_dir / "theme_dark.svg",
            THEME_LIGHT: self.icon_dir / "theme_light.svg",
            THEME_SYSTEM: self.icon_dir / "theme_system.svg",
        }

        self.setObjectName("SidebarThemeSwitcher")
        self.setFixedSize(188, 68)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        shell_layout = QHBoxLayout(self)
        shell_layout.setContentsMargins(4, 4, 4, 4)
        shell_layout.setSpacing(0)

        self.track = QFrame()
        self.track.setObjectName("SidebarThemeTrack")
        track_layout = QHBoxLayout(self.track)
        track_layout.setContentsMargins(10, 7, 10, 7)
        track_layout.setSpacing(8)
        shell_layout.addWidget(self.track)

        self.indicator = ThemeSwitcherIndicator(self.track, self._dark_mode, self._accent_color)
        self.indicator.lower()

        self.buttons: dict[str, QPushButton] = {}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        track_layout.addStretch(1)
        for theme_key, label in THEME_MODE_OPTIONS:
            button = QPushButton()
            button.setObjectName("SidebarThemeButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(f"{label} theme")
            button.setAccessibleName(f"{label} theme")
            button.setFixedSize(44, 44)
            button.setIconSize(QSize(20, 20))
            button.clicked.connect(lambda _checked=False, option=theme_key: self._handle_button_click(option))
            track_layout.addWidget(button)
            self.group.addButton(button)
            button.installEventFilter(self)
            self.buttons[theme_key] = button
        track_layout.addStretch(1)

        self.track.installEventFilter(self)
        self.set_dark_mode(self._dark_mode)
        self.set_theme_mode(self._theme_mode, animated=False, emit_signal=False)

    def eventFilter(self, watched, event):
        observed = {self.track, *self.buttons.values()}
        if watched in observed and event.type() in {
            QEvent.Type.LayoutRequest,
            QEvent.Type.Move,
            QEvent.Type.Resize,
            QEvent.Type.Show,
        }:
            self._sync_indicator(animated=False)
        return super().eventFilter(watched, event)

    def set_dark_mode(self, dark_mode: bool) -> None:
        dark_mode = bool(dark_mode)
        if dark_mode == self._dark_mode:
            self._refresh_icons()
            return
        self._dark_mode = dark_mode
        self.indicator.set_dark_mode(dark_mode)
        self._refresh_icons()

    def set_accent_color(self, accent_color: str) -> None:
        self._accent_color = normalize_accent_color(accent_color)
        self.indicator.set_accent_color(self._accent_color)

    def set_theme_mode(self, theme_mode: str, animated: bool = True, emit_signal: bool = False) -> None:
        normalized = normalize_theme_mode(theme_mode, self._dark_mode)
        changed = normalized != self._theme_mode
        self._theme_mode = normalized

        blockers = [QSignalBlocker(button) for button in self.buttons.values()]
        for option, button in self.buttons.items():
            button.setChecked(option == normalized)
        del blockers

        self._refresh_icons()
        self._sync_indicator(animated=animated)
        if changed and emit_signal:
            self.themeChanged.emit(normalized)

    def theme_mode(self) -> str:
        return self._theme_mode

    def _handle_button_click(self, theme_mode: str) -> None:
        normalized = normalize_theme_mode(theme_mode, self._dark_mode)
        if normalized == self._theme_mode:
            self._sync_indicator(animated=False)
            return
        self.set_theme_mode(normalized, animated=True, emit_signal=True)

    def _refresh_icons(self) -> None:
        active_color = "#fbfcff" if self._dark_mode else "#152131"
        inactive_color = "#9fb0c8" if self._dark_mode else "#5f7186"
        for option, button in self.buttons.items():
            color = active_color if option == self._theme_mode else inactive_color
            button.setIcon(self._render_icon(self._option_icons[option], color))

    def _render_icon(self, icon_path: Path, color: str) -> QIcon:
        svg_text = self._svg_cache.get(icon_path)
        if svg_text is None:
            svg_text = icon_path.read_text(encoding="utf-8")
            self._svg_cache[icon_path] = svg_text

        renderer = QSvgRenderer(QByteArray(svg_text.replace("currentColor", color).encode("utf-8")))
        logical_size = 20
        device_ratio = 2.0
        pixmap = QPixmap(round(logical_size * device_ratio), round(logical_size * device_ratio))
        pixmap.setDevicePixelRatio(device_ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, logical_size, logical_size))
        painter.end()
        return QIcon(pixmap)

    def _sync_indicator(self, animated: bool) -> None:
        target_rect = self._target_rect()
        if target_rect is None:
            self.indicator.hide()
            return

        was_hidden = self.indicator.isHidden() or self.indicator.geometry().isNull()
        self.indicator.show()
        self.indicator.lower()

        if not animated or was_hidden:
            self._stop_indicator_animations()
            self.indicator.setGeometry(target_rect)
            return

        if self.indicator.geometry() == target_rect:
            return

        self._animate_indicator_to(target_rect)

    def _target_rect(self) -> QRect | None:
        button = self.buttons.get(self._theme_mode)
        if button is None:
            return None
        top_left = button.mapTo(self.track, button.rect().topLeft())
        return QRect(top_left.x(), top_left.y(), button.width(), button.height())

    def _stop_indicator_animations(self) -> None:
        for attr_name in ("_slide_anim", "_settle_anim"):
            anim = getattr(self, attr_name, None)
            if anim is not None:
                anim.stop()
                anim.deleteLater()
                setattr(self, attr_name, None)

    def _animate_indicator_to(self, target_rect: QRect) -> None:
        self._stop_indicator_animations()
        start_rect = QRect(self.indicator.geometry())
        dx = target_rect.center().x() - start_rect.center().x()
        dy = target_rect.center().y() - start_rect.center().y()
        distance = math.hypot(dx, dy)
        duration = min(260, max(170, int(165 + distance * 0.35)))

        self._slide_anim = QVariantAnimation(self)
        self._slide_anim.setDuration(duration)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.setStartValue(0.0)
        self._slide_anim.setEndValue(1.0)

        def _step(value: float) -> None:
            t = float(value)
            self.indicator.setGeometry(self._interpolate_rect(start_rect, target_rect, t))

        def _finish() -> None:
            self.indicator.setGeometry(target_rect)
            self._start_settle(target_rect, dx, dy)

        self._slide_anim.valueChanged.connect(_step)
        self._slide_anim.finished.connect(_finish)
        self._slide_anim.start()

    def _start_settle(self, target_rect: QRect, dx: float, dy: float) -> None:
        distance = math.hypot(dx, dy)
        if distance <= 0.5:
            return

        unit_x = dx / distance
        unit_y = dy / distance
        amplitude = min(1.8, max(0.45, distance * 0.016))

        self._settle_anim = QVariantAnimation(self)
        self._settle_anim.setDuration(115)
        self._settle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._settle_anim.setStartValue(0.0)
        self._settle_anim.setEndValue(1.0)

        def _step(value: float) -> None:
            t = float(value)
            damped = math.sin(t * math.pi * 2.0) * (1.0 - t)
            offset_x = unit_x * amplitude * damped
            offset_y = unit_y * amplitude * damped
            self.indicator.setGeometry(
                QRect(
                    round(target_rect.x() + offset_x),
                    round(target_rect.y() + offset_y),
                    target_rect.width(),
                    target_rect.height(),
                )
            )

        def _finish() -> None:
            self.indicator.setGeometry(target_rect)

        self._settle_anim.valueChanged.connect(_step)
        self._settle_anim.finished.connect(_finish)
        self._settle_anim.start()

    @staticmethod
    def _interpolate_rect(start: QRect, end: QRect, t: float) -> QRect:
        return QRect(
            round(start.x() + (end.x() - start.x()) * t),
            round(start.y() + (end.y() - start.y()) * t),
            round(start.width() + (end.width() - start.width()) * t),
            round(start.height() + (end.height() - start.height()) * t),
        )
