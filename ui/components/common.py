from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def refresh_widget_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class Card(QFrame):
    def __init__(self, title: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(8)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            self.layout.addWidget(label)


class PageHeader(QFrame):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("PageHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        self.subtitle_label.setProperty("role", "muted")
        self.subtitle_label.setVisible(bool(subtitle))

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))


class StatusPill(QLabel):
    _VARIANT_NAMES = {
        "neutral": "StatusPill",
        "accent": "StatusPillAccent",
        "success": "StatusPillSuccess",
        "warning": "StatusPillWarning",
        "danger": "StatusPillDanger",
    }

    def __init__(self, text: str = "", variant: str = "neutral", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(28)
        self.setProperty("variant", variant)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        variant = variant if variant in self._VARIANT_NAMES else "neutral"
        self.setProperty("variant", variant)
        self.setObjectName(self._VARIANT_NAMES[variant])
        refresh_widget_style(self)


class SettingsHero(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SettingsHero")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SettingsHeroTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("SettingsHeroSubtitle")
        self.subtitle_label.setWordWrap(True)

        self.status_strip = QWidget()
        self.status_strip.setObjectName("SettingsStatusStrip")
        self.status_layout = QHBoxLayout(self.status_strip)
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_layout.setSpacing(8)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.status_strip)

    def set_status_pills(self, pills: list[QWidget]) -> None:
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        for pill in pills:
            self.status_layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignLeft)
        self.status_layout.addStretch(1)


class SettingsCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SettingsCard")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        header = QVBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SettingsCardTitle")
        header.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("SettingsCardSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        header.addWidget(self.subtitle_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 4, 0, 0)
        self.content_layout.setSpacing(12)

        outer.addLayout(header)
        outer.addLayout(self.content_layout)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)


class SettingsRow(QFrame):
    def __init__(self, label: str, description: str = "", control: QWidget | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SettingsRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        self.label = QLabel(label)
        self.label.setObjectName("SettingsLabel")
        info_layout.addWidget(self.label)

        self.description = QLabel(description)
        self.description.setObjectName("SettingsDescription")
        self.description.setWordWrap(True)
        self.description.setVisible(bool(description))
        info_layout.addWidget(self.description)

        layout.addLayout(info_layout, 1)

        self.control = control
        if control is not None:
            layout.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class SegmentedControl(QFrame):
    valueChanged = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current_value: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SegmentedControl")
        self._options = list(options)
        self._current_value = ""
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for value, label in self._options:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, option=value: self.set_current_value(option, emit_signal=True))
            layout.addWidget(button)
            self._group.addButton(button)
            self._buttons[value] = button

        fallback = current_value or (self._options[0][0] if self._options else "")
        self.set_current_value(fallback, emit_signal=False)

    def current_value(self) -> str:
        return self._current_value

    def set_current_value(self, value: str, emit_signal: bool = False) -> None:
        if value not in self._buttons:
            return
        changed = value != self._current_value
        self._current_value = value

        for option, button in self._buttons.items():
            selected = option == value
            button.blockSignals(True)
            button.setChecked(selected)
            button.blockSignals(False)
            button.setProperty("selected", selected)
            button.setObjectName("SegmentedButtonSelected" if selected else "SegmentedButton")
            refresh_widget_style(button)

        refresh_widget_style(self)
        if changed and emit_signal:
            self.valueChanged.emit(value)


class ToggleSwitch(QCheckBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ToggleSwitch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("")
        self.setFixedSize(52, 30)
        self._accent = QColor("#8f5cff")

    def set_accent_color(self, color: str) -> None:
        candidate = QColor(color)
        if candidate.isValid():
            self._accent = candidate
            self.update()

    def paintEvent(self, _event) -> None:
        track_rect = QRectF(self.rect()).adjusted(1.5, 3.0, -1.5, -3.0)
        radius = track_rect.height() / 2.0
        knob_diameter = track_rect.height() - 4.0
        knob_y = track_rect.top() + 2.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = QColor(self._accent)
        track_off = QColor(128, 142, 160, 95)
        border_off = QColor(90, 105, 124, 120)
        track_on = QColor(accent)
        track_on.setAlpha(210 if self.isEnabled() else 110)
        border_on = QColor(accent)
        border_on.setAlpha(235 if self.isEnabled() else 125)
        knob = QColor("#f7fbff" if self.isEnabled() else "#d7dde7")

        if self.isChecked():
            track_color = track_on
            border_color = border_on
            knob_x = track_rect.right() - knob_diameter - 2.0
        else:
            track_color = track_off
            border_color = border_off
            knob_x = track_rect.left() + 2.0

        painter.setPen(QPen(border_color, 1.1))
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, radius, radius)

        if self.hasFocus():
            focus = QColor(accent)
            focus.setAlpha(70)
            painter.setPen(QPen(focus, 2.0))
            focus_rect = track_rect.adjusted(-2.0, -2.0, 2.0, 2.0)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(focus_rect, radius + 2.0, radius + 2.0)

        knob_rect = QRectF(knob_x, knob_y, knob_diameter, knob_diameter)
        painter.setPen(QPen(QColor(28, 38, 54, 28), 1.0))
        painter.setBrush(knob)
        painter.drawEllipse(knob_rect)


class ColorSwatchButton(QPushButton):
    def __init__(self, name: str, color: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.name = name
        self.color = QColor(color)
        self.setObjectName("ColorSwatch")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)
        self.setAccessibleName(name)
        self.setFixedSize(32, 32)
        self.setText("")

    def set_selected(self, selected: bool) -> None:
        self.blockSignals(True)
        self.setChecked(selected)
        self.blockSignals(False)
        self.setProperty("selected", selected)
        self.setObjectName("ColorSwatchSelected" if selected else "ColorSwatch")
        refresh_widget_style(self)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        outer = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        inner = outer.adjusted(5.0, 5.0, -5.0, -5.0)

        ring_color = QColor("#ffffff" if self.isChecked() else "#7f8ba0")
        ring_color.setAlpha(235 if self.isChecked() else 95)
        painter.setPen(QPen(ring_color, 2.0 if self.isChecked() else 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(outer)

        painter.setPen(QPen(QColor(255, 255, 255, 36), 1.0))
        painter.setBrush(self.color)
        painter.drawEllipse(inner)

        if self.hasFocus():
            focus = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(QColor(255, 255, 255, 78), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(focus)


class ColorSwatchPicker(QWidget):
    valueChanged = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current_value: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: dict[str, ColorSwatchButton] = {}
        self._current_value = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        group = QButtonGroup(self)
        group.setExclusive(True)

        for name, color in options:
            button = ColorSwatchButton(name, color)
            button.clicked.connect(lambda _checked=False, option=color: self.set_current_value(option, emit_signal=True))
            layout.addWidget(button)
            group.addButton(button)
            self._buttons[color] = button

        layout.addStretch(1)
        fallback = current_value or (options[0][1] if options else "")
        self.set_current_value(fallback, emit_signal=False)

    def current_value(self) -> str:
        return self._current_value

    def set_current_value(self, value: str, emit_signal: bool = False) -> None:
        if value not in self._buttons:
            return
        changed = value != self._current_value
        self._current_value = value
        for option, button in self._buttons.items():
            button.set_selected(option == value)
        if changed and emit_signal:
            self.valueChanged.emit(value)


class PathInputRow(QWidget):
    def __init__(
        self,
        placeholder: str = "",
        button_text: str = "Browse",
        extra_button_text: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("PathInput")
        self.line_edit.setClearButtonEnabled(True)
        self.line_edit.setPlaceholderText(placeholder)
        layout.addWidget(self.line_edit, 1)

        self.primary_button = QPushButton(button_text)
        self.primary_button.setObjectName("SecondaryButton")
        layout.addWidget(self.primary_button)

        self.extra_button: QPushButton | None = None
        if extra_button_text:
            self.extra_button = QPushButton(extra_button_text)
            self.extra_button.setObjectName("GhostButton")
            layout.addWidget(self.extra_button)


class CollapsibleOutputSection(Card):
    expanded_changed = Signal(bool)

    def __init__(self, title: str = "Live Output", subtitle: str = "Transfer stream", max_blocks: int = 1200):
        super().__init__()
        self._expanded = True
        self._expanded_body_height = 260
        self._body_anim: QPropertyAnimation | None = None

        header = QFrame()
        header.setObjectName("CollapsibleHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("role", "muted")
        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)

        self.toggle_btn = QPushButton("-")
        self.toggle_btn.setObjectName("SectionToggleButton")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setFixedSize(32, 28)
        self.toggle_btn.setToolTip("Collapse live output")
        self.toggle_btn.setAccessibleName("Toggle live output")
        self.toggle_btn.clicked.connect(lambda checked: self.set_expanded(checked, animated=True))

        header_layout.addLayout(title_col)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_btn)

        self.body = QWidget()
        self.body.setObjectName("CollapsibleBody")
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 2, 0, 0)
        body_layout.setSpacing(0)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(max_blocks)
        body_layout.addWidget(self.output)

        self.layout.addWidget(header)
        self.layout.addWidget(self.body, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_expanded(self, expanded: bool, animated: bool = True) -> None:
        if expanded == self._expanded and self.body.isVisible() == expanded:
            return
        self._expanded = expanded
        self.expanded_changed.emit(expanded)
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setText("-" if expanded else "+")
        self.toggle_btn.setToolTip("Collapse live output" if expanded else "Expand live output")

        if self._body_anim:
            self._body_anim.stop()
            self._body_anim.deleteLater()
            self._body_anim = None

        if expanded:
            self.setMaximumHeight(16777215)
            self.body.setVisible(True)
            start_height = max(0, self.body.height())
            target_height = max(self._expanded_body_height, 220)
        else:
            self._expanded_body_height = max(self.body.height(), self.output.height(), 220)
            start_height = max(0, self.body.height())
            target_height = 0

        if not animated:
            self.body.setMaximumHeight(16777215 if expanded else 0)
            self.body.setVisible(expanded)
            if not expanded:
                self.setMaximumHeight(self.sizeHint().height())
            return

        self.body.setMaximumHeight(start_height)
        self._body_anim = QPropertyAnimation(self.body, b"maximumHeight", self)
        self._body_anim.setDuration(180)
        self._body_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._body_anim.setStartValue(start_height)
        self._body_anim.setEndValue(target_height)

        def _finish() -> None:
            if expanded:
                self.body.setMaximumHeight(16777215)
            else:
                self.body.setVisible(False)
                self.setMaximumHeight(self.sizeHint().height())

        self._body_anim.finished.connect(_finish)
        self._body_anim.start()


class DropList(QListWidget):
    paths_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.exists():
                self.add_path(str(path))
        self.paths_changed.emit(self.paths())
        event.acceptProposedAction()

    def add_path(self, path: str):
        if path not in self.paths():
            self.addItem(QListWidgetItem(path))

    def remove_selected(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.paths_changed.emit(self.paths())

    def paths(self) -> list[str]:
        return [self.item(i).text() for i in range(self.count())]
