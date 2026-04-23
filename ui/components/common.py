from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSizePolicy,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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
