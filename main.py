from __future__ import annotations

import argparse
import multiprocessing
import os
import sys

from app.bootstrap import build_app
from app.version import APP_NAME
from utils.single_instance import SingleInstanceGuard
from utils.startup_diagnostics import StartupDiagnostics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CrocDrop desktop app")
    parser.add_argument("--debug-peer", action="store_true", help="Launch secondary debug instance mode")
    args, _unknown = parser.parse_known_args()
    return args


def main() -> int:
    startup = StartupDiagnostics()

    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    startup.log_process_context("main.entry")
    multiprocessing.freeze_support()

    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CrocDrop.Desktop")
        except Exception:
            pass

    args = parse_args()
    startup.log_phase("args.parsed", debug_peer=bool(args.debug_peer))

    instance_guard = None
    if not args.debug_peer:
        instance_guard = SingleInstanceGuard(f"Local\\{APP_NAME}-SingleInstance")
        startup.log_phase("single_instance.acquire.start")
        if not instance_guard.acquire():
            startup.log_phase("single_instance.acquire.duplicate")
            return 0
        startup.log_phase("single_instance.acquire.end")

    qt_app, window = build_app(debug_peer=args.debug_peer, startup_diagnostics=startup)
    startup.log_phase("mainwindow.show.schedule")
    window.begin_initial_show()

    try:
        exit_code = qt_app.exec()
        startup.log_phase("app.exec.exit", exit_code=exit_code)
        return exit_code
    finally:
        if instance_guard is not None:
            instance_guard.release()


if __name__ == "__main__":
    raise SystemExit(main())
