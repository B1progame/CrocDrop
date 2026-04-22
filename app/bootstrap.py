from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from services.croc_manager import CrocManager
from services.debug_service import DebugService
from services.history_service import HistoryService
from services.log_service import LogService
from services.settings_service import SettingsService
from services.transfer_service import TransferService
from ui.main_window import MainWindow
from ui.profile_dialog import ProfileDialog
from ui.theme import apply_theme


@dataclass(slots=True)
class AppContext:
    log_service: LogService
    settings_service: SettingsService
    history_service: HistoryService
    croc_manager: CrocManager
    transfer_service: TransferService
    debug_service: DebugService


def _build_app_icon() -> QIcon:
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
    icon = QIcon()
    if not logo_path.exists():
        return icon

    renderer = QSvgRenderer(str(logo_path))
    for size in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pix)
    return icon


def build_app(debug_peer: bool = False) -> tuple[QApplication, MainWindow]:
    qt_app = QApplication([])
    qt_app.setApplicationName("CrocDrop")
    qt_app.setOrganizationName("CrocDrop")

    app_icon = _build_app_icon()
    if not app_icon.isNull():
        qt_app.setWindowIcon(app_icon)

    settings_service = SettingsService()
    settings = settings_service.load()
    if not settings.current_profile:
        dialog = ProfileDialog(settings.profiles)
        if dialog.exec():
            if dialog.use_guest:
                settings_service.use_guest_mode()
            elif dialog.selected_profile:
                settings_service.add_profile(dialog.selected_profile)
        settings = settings_service.get()

    log_service = LogService(debug_enabled=settings.debug_mode)
    history_service = HistoryService(log_service)
    croc_manager = CrocManager(log_service=log_service, settings_service=settings_service)
    transfer_service = TransferService(
        croc_manager=croc_manager,
        history_service=history_service,
        settings_service=settings_service,
        log_service=log_service,
    )
    debug_service = DebugService(
        transfer_service=transfer_service,
        croc_manager=croc_manager,
        log_service=log_service,
    )
    context = AppContext(
        log_service=log_service,
        settings_service=settings_service,
        history_service=history_service,
        croc_manager=croc_manager,
        transfer_service=transfer_service,
        debug_service=debug_service,
    )

    apply_theme(qt_app, settings)
    window = MainWindow(context=context, debug_peer=debug_peer)
    return qt_app, window
