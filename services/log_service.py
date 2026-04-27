from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from utils.paths import app_log_dir


@dataclass(slots=True)
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str


class QtLogHandler(logging.Handler):
    def __init__(self, sink: "LogService"):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self.sink.emit_log(
            level=record.levelname.lower(),
            source=record.name,
            message=self.format(record),
        )


class LogService(QObject):
    log_emitted = Signal(dict)

    def __init__(self, debug_enabled: bool = False):
        super().__init__()
        self.log_dir = app_log_dir()
        self.log_file = self.log_dir / "crocdrop.log"

        self.logger = logging.getLogger("crocdrop")
        self.logger.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
        self.logger.handlers.clear()

        file_handler = self._build_file_handler()
        if file_handler is not None:
            self.logger.addHandler(file_handler)

        qt_handler = QtLogHandler(self)
        qt_handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(qt_handler)

    def emit_log(self, level: str, source: str, message: str) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "source": source,
            "message": message,
        }
        self.log_emitted.emit(entry)

    def get_logger(self, name: str) -> logging.Logger:
        return self.logger.getChild(name)

    def get_log_file_path(self) -> Path:
        return self.log_file

    def _build_file_handler(self) -> logging.Handler | None:
        candidate_paths = [self.log_file, self.log_dir / f"crocdrop-{os.getpid()}.log"]
        for path in candidate_paths:
            try:
                handler = logging.FileHandler(path, encoding="utf-8")
            except OSError:
                continue
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
            self.log_file = path
            return handler
        return None

    def clear_logs(self) -> None:
        for file in self.log_dir.glob("*.log"):
            file.write_text("", encoding="utf-8")
        self.emit_log("info", "log", "Logs cleared")

    def export_logs(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.log_file.read_text(encoding="utf-8") if self.log_file.exists() else "", encoding="utf-8")
        self.emit_log("info", "log", f"Exported logs to {destination}")
        return destination

    def prune_old_logs(self, retention_days: int) -> None:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        for file in self.log_dir.glob("*.log"):
            if datetime.utcfromtimestamp(file.stat().st_mtime) < cutoff:
                file.unlink(missing_ok=True)
