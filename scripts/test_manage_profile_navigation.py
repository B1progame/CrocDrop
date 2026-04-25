from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap import build_app
from ui.profile_dialog import ProfileDialog


def _pump(app, seconds: float) -> None:
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    ProfileDialog.exec = lambda self: False

    app, window = build_app(debug_peer=False)
    window.show()
    app.processEvents()

    try:
        window.navigate_to("Profile", animated=False)
        _pump(app, 0.1)
        window.profile_page.settings_category_requested.emit("profiles")
        _pump(app, 0.25)

        assert window._active_page_name == "Settings", window._active_page_name
        assert window.pages.currentWidget() is window.settings_page
        assert window.footer_buttons["Settings"].isChecked()
        assert not window.footer_buttons["Profile"].isChecked()
        assert window.nav.currentRow() == -1, window.nav.currentRow()
        assert window.settings_page.current_category == "profiles", window.settings_page.current_category

        screenshot_dir = Path("debug_screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / "manage_profile_navigation.png"
        if not window.grab().save(str(screenshot_path)):
            raise RuntimeError(f"Failed to save screenshot to {screenshot_path}")

        print("Manage Profile navigation test passed.")
        print(f"Saved screenshot to {screenshot_path}")
        return 0
    finally:
        window.close()
        app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
