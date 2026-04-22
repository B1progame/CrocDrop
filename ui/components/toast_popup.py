from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ToastPopup(QWidget):
    def __init__(self, title: str, message: str, timeout_ms: int = 4000):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(
            """
            QWidget#ToastRoot {
                background-color: rgba(21, 28, 37, 0.97);
                border: 1px solid #2f4258;
                border-radius: 12px;
            }
            QLabel#ToastTitle {
                font-size: 14px;
                font-weight: 700;
                color: #dff8ef;
            }
            QLabel#ToastBody {
                font-size: 12px;
                color: #b9d0c4;
            }
            """
        )
        self.setObjectName("ToastRoot")
        self.resize(320, 88)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("ToastTitle")
        body_label = QLabel(message)
        body_label.setObjectName("ToastBody")
        body_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(body_label)

        self._move_top_right()
        self.show()
        QTimer.singleShot(timeout_ms, self.close)

    def _move_top_right(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.move(20, 20)
            return
        rect = screen.availableGeometry()
        margin = 18
        self.move(rect.right() - self.width() - margin, rect.top() + margin)
