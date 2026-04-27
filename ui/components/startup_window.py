from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QRectF
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class StartupPulse(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.setInterval(170)
        self._timer.timeout.connect(self._advance)
        self._timer.start()
        self.setFixedSize(68, 18)

    def _advance(self) -> None:
        self._frame = (self._frame + 1) % 3
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index in range(3):
            alpha = 220 if index == self._frame else 80
            painter.setBrush(QColor(53, 201, 165, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            x = 8 + index * 22
            painter.drawEllipse(QRectF(x, 4, 10, 10))


class StartupWindow(QFrame):
    def __init__(self, title: str, logo_path: Path | None = None, icon: QIcon | None = None):
        super().__init__(None)
        self.setObjectName("StartupWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(420, 300)
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)

        self.setStyleSheet(
            """
            QFrame#StartupWindow {
                background-color: rgba(14, 20, 28, 245);
                border: 1px solid rgba(87, 111, 138, 180);
                border-radius: 18px;
            }
            QLabel#StartupTitle {
                font-size: 26px;
                font-weight: 700;
                color: #eef6fb;
            }
            QLabel#StartupSubtitle {
                font-size: 13px;
                color: #a8bbcb;
            }
            QLabel#StartupStatus {
                font-size: 13px;
                color: #d7ece5;
                font-weight: 600;
            }
            QProgressBar {
                border: 1px solid rgba(87, 111, 138, 150);
                border-radius: 8px;
                background: rgba(27, 38, 50, 220);
                height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(53, 201, 165, 210),
                    stop:1 rgba(95, 149, 255, 220)
                );
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(10)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFixedSize(92, 92)
        self.logo_label.setPixmap(self._load_logo_pixmap(logo_path, icon))

        self.title_label = QLabel(title)
        self.title_label.setObjectName("StartupTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle_label = QLabel("Preparing a stable startup...")
        self.subtitle_label.setObjectName("StartupSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Starting...")
        self.status_label.setObjectName("StartupStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(8)
        self.progress.setTextVisible(False)

        self.pulse = StartupPulse()

        layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(4)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.pulse, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        self._center_on_primary_screen()

    def set_status(self, text: str, progress: int | None = None) -> None:
        self.status_label.setText(text)
        if progress is not None:
            self.set_progress(progress)
        app = QApplication.instance()
        if app is not None:
            app.processEvents()

    def set_progress(self, value: int) -> None:
        target = max(0, min(100, int(value)))
        self.progress.setValue(target)

    def _center_on_primary_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        rect = screen.availableGeometry()
        self.move(rect.center().x() - self.width() // 2, rect.center().y() - self.height() // 2)

    @staticmethod
    def _load_logo_pixmap(logo_path: Path | None, icon: QIcon | None) -> QPixmap:
        if logo_path is not None and logo_path.exists():
            renderer = QSvgRenderer(str(logo_path))
            pix = QPixmap(92, 92)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            renderer.render(painter, QRectF(2, 2, 88, 88))
            painter.end()
            return pix
        if icon is not None and not icon.isNull():
            return icon.pixmap(92, 92)
        pix = QPixmap(92, 92)
        pix.fill(Qt.GlobalColor.transparent)
        return pix
