from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, Signal

from models.transfer import TransferRecord
from storage.json_store import JsonStore
from utils.paths import state_dir


class HistoryService(QObject):
    history_changed = Signal()

    def __init__(self, log_service):
        super().__init__()
        self.log = log_service.get_logger("history")
        self.store = JsonStore(state_dir() / "history.json")
        self._records: list[TransferRecord] = []
        self.load()

    def load(self) -> list[TransferRecord]:
        payload = self.store.load(default=[])
        self._records = [TransferRecord.from_dict(item) for item in payload]
        return self._records

    def save(self) -> None:
        self.store.save([r.to_dict() for r in self._records])
        self.history_changed.emit()

    def list_records(self) -> list[TransferRecord]:
        return list(reversed(self._records))

    def clear(self) -> None:
        self._records = []
        self.save()

    def add(self, record: TransferRecord) -> TransferRecord:
        self._records.append(record)
        self.save()
        return record

    def update(self, record: TransferRecord) -> None:
        for idx, item in enumerate(self._records):
            if item.transfer_id == record.transfer_id:
                self._records[idx] = record
                self.save()
                return

    def mark_started(self, record: TransferRecord) -> None:
        record.status = "running"
        record.started_at = datetime.utcnow().isoformat()
        self.update(record)

    def mark_finished(self, record: TransferRecord, status: str, error: str = "") -> None:
        record.status = status
        record.error_message = error
        record.ended_at = datetime.utcnow().isoformat()
        self.update(record)
