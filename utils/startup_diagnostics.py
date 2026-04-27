from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone

from utils.paths import app_log_dir


class StartupDiagnostics:
    """Best-effort startup logger that works before the main logging service is ready."""

    def __init__(self, log_name: str = "startup.log"):
        self.log_path = app_log_dir() / log_name
        self._lock = threading.Lock()
        self._runtime_logger = None

    def attach_logger(self, logger) -> None:
        self._runtime_logger = logger

    def log_phase(self, phase: str, **fields) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "pid": os.getpid(),
            **fields,
        }
        self._write(payload)
        if self._runtime_logger is not None:
            try:
                self._runtime_logger.info("startup | %s", json.dumps(payload, ensure_ascii=True, sort_keys=True))
            except Exception:
                pass

    def log_process_context(self, phase: str) -> None:
        self.log_phase(
            phase,
            argv=sys.argv,
            frozen=bool(getattr(sys, "frozen", False)),
            cwd=os.getcwd(),
            executable=sys.executable,
        )

    def _write(self, payload: dict) -> None:
        try:
            line = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            with self._lock:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except Exception:
            pass
