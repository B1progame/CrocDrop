from __future__ import annotations

import argparse
import sys

from app.bootstrap import build_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CrocDrop desktop app")
    parser.add_argument("--debug-peer", action="store_true", help="Launch secondary debug instance mode")
    return parser.parse_args()


def main() -> int:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CrocDrop.Desktop")
        except Exception:
            pass

    args = parse_args()
    qt_app, window = build_app(debug_peer=args.debug_peer)
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
