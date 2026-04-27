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
        self._record_index: dict[str, int] = {}
        self.load()

    def load(self) -> list[TransferRecord]:
        payload = self.store.load(default=[])
        self._records = [TransferRecord.from_dict(item) for item in payload]
        self._record_index = {record.transfer_id: idx for idx, record in enumerate(self._records)}
        return self._records

    def save(self, emit_signal: bool = True) -> None:
        self.store.save([r.to_dict() for r in self._records])
        if emit_signal:
            self.history_changed.emit()

    def list_records(self) -> list[TransferRecord]:
        return list(reversed(self._records))

    def get_record(self, transfer_id: str) -> TransferRecord | None:
        idx = self._record_index.get(transfer_id)
        if idx is None:
            return None
        if idx >= len(self._records):
            return None
        return self._records[idx]

    def clear(self) -> None:
        self._records = []
        self._record_index = {}
        self.save()

    def add(self, record: TransferRecord) -> TransferRecord:
        self._record_index[record.transfer_id] = len(self._records)
        self._records.append(record)
        self.save()
        return record

    def update(self, record: TransferRecord, persist: bool = True, emit_signal: bool = True) -> None:
        idx = self._record_index.get(record.transfer_id)
        if idx is None:
            return
        self._records[idx] = record
        if persist:
            self.save(emit_signal=emit_signal)
        elif emit_signal:
            self.history_changed.emit()

    def mark_started(self, record: TransferRecord) -> None:
        record.status = "running"
        if not record.started_at:
            record.started_at = datetime.utcnow().isoformat()
        self.update(record)

    def mark_finished(self, record: TransferRecord, status: str, error: str = "") -> None:
        record.status = status
        record.error_message = error
        record.ended_at = datetime.utcnow().isoformat()
        self.update(record)
