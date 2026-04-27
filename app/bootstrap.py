from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from app.version import APP_NAME
from services.croc_manager import CrocManager
from services.debug_service import DebugService
from services.history_service import HistoryService
from services.log_service import LogService
from services.sevenzip_service import SevenZipService
from services.settings_service import SettingsService
from services.transfer_service import TransferService
from services.update_service import UpdateService
from ui.components.startup_window import StartupWindow
from ui.main_window import MainWindow
from ui.profile_dialog import ProfileDialog
from ui.theme import apply_theme
from utils.startup_diagnostics import StartupDiagnostics


@dataclass(slots=True)
class AppContext:
    log_service: LogService
    startup_diagnostics: StartupDiagnostics | None
    settings_service: SettingsService
    history_service: HistoryService
    croc_manager: CrocManager
    sevenzip_service: SevenZipService
    transfer_service: TransferService
    debug_service: DebugService
    update_service: UpdateService


def _build_app_icon() -> QIcon:
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
    icon = QIcon()
    if not logo_path.exists():
        if getattr(sys, "frozen", False):
            exe_icon = QIcon(str(Path(sys.executable)))
            if not exe_icon.isNull():
                return exe_icon
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


def build_app(debug_peer: bool = False, startup_diagnostics: StartupDiagnostics | None = None) -> tuple[QApplication, MainWindow]:
    startup = startup_diagnostics or StartupDiagnostics()
    startup.log_phase("qapplication.create.start")
    qt_app = QApplication.instance() or QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setOrganizationName(APP_NAME)
    startup.log_phase("qapplication.create.end")

    logo_path = Path(__file__).resolve().parents[1] / "assets" / "crocdrop_lock_logo.svg"
    app_icon = _build_app_icon()
    if not app_icon.isNull():
        qt_app.setWindowIcon(app_icon)

    startup_window = StartupWindow(APP_NAME, logo_path=logo_path, icon=app_icon)
    startup_window.set_status("Loading settings...", progress=15)
    startup_window.show()
    qt_app.processEvents()

    def update_startup(status: str, phase: str, progress: int, **extra) -> None:
        startup.log_phase(phase, status=status, **extra)
        startup_window.set_status(status, progress=progress)

    update_startup("Loading settings...", "settings.load.start", progress=15)
    settings_service = SettingsService()
    settings = settings_service.load()
    startup.log_phase(
        "settings.load.end",
        current_profile=settings.current_profile or "",
        profiles=len(settings.profiles),
    )

    if not settings.current_profile:
        update_startup("Selecting profile...", "profile_dialog.start", progress=32)
        dialog = ProfileDialog(settings.profiles, parent=startup_window)
        if not app_icon.isNull():
            dialog.setWindowIcon(app_icon)
        if dialog.exec():
            if dialog.use_guest:
                settings_service.use_guest_mode()
            elif dialog.selected_profile:
                settings_service.add_profile(dialog.selected_profile)
        settings = settings_service.get()
        startup.log_phase(
            "profile_dialog.end",
            current_profile=settings.current_profile or "",
            guest_mode=bool(dialog.use_guest),
        )

    update_startup("Preparing services...", "services.create.start", progress=52)
    log_service = LogService(debug_enabled=settings.debug_mode)
    startup.attach_logger(log_service.get_logger("startup"))
    startup.log_phase("services.log.ready", log_file=str(log_service.get_log_file_path()))
    history_service = HistoryService(log_service)
    croc_manager = CrocManager(log_service=log_service, settings_service=settings_service)
    sevenzip_service = SevenZipService(log_service=log_service)
    transfer_service = TransferService(
        croc_manager=croc_manager,
        sevenzip_service=sevenzip_service,
        history_service=history_service,
        settings_service=settings_service,
        log_service=log_service,
    )
    debug_service = DebugService(
        transfer_service=transfer_service,
        croc_manager=croc_manager,
        log_service=log_service,
    )
    update_service = UpdateService(log_service=log_service)
    startup.log_phase("services.create.end")

    context = AppContext(
        log_service=log_service,
        startup_diagnostics=startup,
        settings_service=settings_service,
        history_service=history_service,
        croc_manager=croc_manager,
        sevenzip_service=sevenzip_service,
        transfer_service=transfer_service,
        debug_service=debug_service,
        update_service=update_service,
    )

    apply_theme(qt_app, settings)
    update_startup("Building interface...", "mainwindow.create.start", progress=76)
    window = MainWindow(context=context, debug_peer=debug_peer)
    startup_window.set_status("Finalizing startup...", progress=92)
    window.attach_startup_window(startup_window)
    startup.log_phase("mainwindow.create.end")
    QTimer.singleShot(
        1500,
        lambda: sevenzip_service.ensure_managed_cli_async(enabled=settings_service.get().auto_install_7zip_cli),
    )
    return qt_app, window
