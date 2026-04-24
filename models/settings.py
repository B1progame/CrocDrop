from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    default_download_folder: str = str(Path.home() / "Downloads")
    ask_before_receiving: bool = True
    auto_open_received_folder: bool = False
    remember_last_folders: bool = True
    dark_mode: bool = True
    theme_mode: str = "dark"
    accent_color: str = "#35c9a5"
    relay_mode: str = "public"  # public/custom
    custom_relay: str = ""
    croc_binary_path: str = ""
    auto_download_croc: bool = True
    upload_limit_kbps: int = 0
    download_limit_kbps: int = 0
    log_retention_days: int = 14
    debug_mode: bool = False
    trusted_devices: dict[str, str] = field(default_factory=dict)
    last_send_folder: str = ""
    last_receive_folder: str = ""
    profiles: list[str] = field(default_factory=list)
    current_profile: str = ""

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["theme_mode"] = self._normalize_theme_mode(self.theme_mode, self.dark_mode)
        if payload["theme_mode"] == "dark":
            payload["dark_mode"] = True
        elif payload["theme_mode"] == "light":
            payload["dark_mode"] = False
        else:
            payload["dark_mode"] = bool(self.dark_mode)
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "AppSettings":
        known = {k: payload.get(k) for k in cls.__dataclass_fields__.keys() if k in payload}
        dark_mode = bool(payload.get("dark_mode", True))
        known["theme_mode"] = cls._normalize_theme_mode(payload.get("theme_mode"), dark_mode)
        known["dark_mode"] = bool(known.get("dark_mode", dark_mode))
        return cls(**known)

    @staticmethod
    def _normalize_theme_mode(theme_mode: str | None, dark_mode: bool) -> str:
        if theme_mode in {"dark", "light", "system"}:
            return theme_mode
        return "dark" if dark_mode else "light"
