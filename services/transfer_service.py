from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from models.transfer import TransferRecord
from services.transfer_parser import TransferOutputParser
from utils.codegen import generate_code_phrase


class TransferRuntime(QObject):
    output_line = Signal(str, str)  # transfer_id, line
    state_changed = Signal(str, str)  # transfer_id, status
    code_found = Signal(str, str)  # transfer_id, code
    progress = Signal(str, float)  # transfer_id, percent
    finished = Signal(str, int)  # transfer_id, exit_code

    def __init__(self, transfer_id: str, process: subprocess.Popen, parser: TransferOutputParser):
        super().__init__()
        self.transfer_id = transfer_id
        self.process = process
        self.parser = parser
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self.state_changed.emit(self.transfer_id, "running")
        self._threads = [
            threading.Thread(target=self._pump, args=(self.process.stdout, "stdout"), daemon=True),
            threading.Thread(target=self._pump, args=(self.process.stderr, "stderr"), daemon=True),
            threading.Thread(target=self._wait, daemon=True),
        ]
        for t in self._threads:
            t.start()

    def _pump(self, stream, stream_name: str) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            if not line:
                break
            channel = "system" if stream_name in {"stdout", "stderr"} else stream_name
            text = f"[{channel}] {line.rstrip()}"
            self.output_line.emit(self.transfer_id, text)
            event = self.parser.parse(line)
            if event.code_phrase:
                self.code_found.emit(self.transfer_id, event.code_phrase)
            if event.progress_percent is not None:
                self.progress.emit(self.transfer_id, event.progress_percent)

    def _wait(self) -> None:
        code = self.process.wait()
        self.finished.emit(self.transfer_id, code)

    def cancel(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            self.state_changed.emit(self.transfer_id, "canceled")


@dataclass(slots=True)
class ActiveTransfer:
    record: TransferRecord
    runtime: TransferRuntime


@dataclass(slots=True)
class ReservedCode:
    code_phrase: str
    expires_at: datetime


class TransferService(QObject):
    transfer_updated = Signal(str)
    transfer_output = Signal(str, str)
    transfer_finished = Signal(str, str)
    next_code_ready = Signal(str, str, str)  # transfer_id, code, expires_at_iso

    def __init__(self, croc_manager, history_service, settings_service, log_service):
        super().__init__()
        self.croc_manager = croc_manager
        self.history_service = history_service
        self.settings_service = settings_service
        self.log = log_service.get_logger("transfer")
        self.parser = TransferOutputParser()
        self.active: dict[str, ActiveTransfer] = {}
        self._reserved_codes: dict[str, ReservedCode] = {}

    def start_send(self, paths: list[str], code_phrase: str = "", direction: str = "send") -> TransferRecord:
        active_profile = (self.settings_service.get().current_profile or "guest").strip() or "guest"
        if not code_phrase.strip():
            reserved = self._take_reserved_code(active_profile)
            code_phrase = reserved if reserved else generate_code_phrase(active_profile)
        process = self.croc_manager.launch_send(paths=paths, code_phrase=code_phrase)
        record = TransferRecord(direction=direction, source_paths=paths, relay=self.settings_service.get().relay_mode)
        record.code_phrase = code_phrase
        record.croc_version = self.croc_manager.get_version(Path(self.croc_manager.detect_binary().path))
        self.history_service.add(record)
        self.history_service.mark_started(record)

        next_code, expires_at = self._reserve_next_code(active_profile)
        self.next_code_ready.emit(record.transfer_id, next_code, expires_at.isoformat())

        runtime = TransferRuntime(record.transfer_id, process, self.parser)
        self._wire_runtime(record, runtime)
        self.active[record.transfer_id] = ActiveTransfer(record=record, runtime=runtime)
        self.transfer_updated.emit(record.transfer_id)
        runtime.start()
        return record

    def start_receive(self, code_phrase: str, destination: str, overwrite: bool, direction: str = "receive") -> TransferRecord:
        process = self.croc_manager.launch_receive(code_phrase=code_phrase, destination=destination, overwrite=overwrite)
        record = TransferRecord(
            direction=direction,
            source_paths=[],
            destination_folder=destination,
            code_phrase=code_phrase,
            relay=self.settings_service.get().relay_mode,
        )
        record.croc_version = self.croc_manager.get_version(Path(self.croc_manager.detect_binary().path))
        self.history_service.add(record)
        self.history_service.mark_started(record)

        runtime = TransferRuntime(record.transfer_id, process, self.parser)
        self._wire_runtime(record, runtime)
        self.active[record.transfer_id] = ActiveTransfer(record=record, runtime=runtime)
        runtime.start()
        return record

    def _wire_runtime(self, record: TransferRecord, runtime: TransferRuntime) -> None:
        runtime.output_line.connect(lambda tid, line: self._on_output(record, tid, line))
        runtime.code_found.connect(lambda tid, code: self._on_code(record, tid, code))
        runtime.progress.connect(lambda tid, pct: self._on_progress(record, tid, pct))
        runtime.finished.connect(lambda tid, exit_code: self._on_finished(record, tid, exit_code))

    def _on_output(self, record: TransferRecord, transfer_id: str, line: str) -> None:
        lowered = line.lower()
        # Keep transfer logs platform-neutral in UI.
        if "(for windows)" in lowered or "(for linux/macos)" in lowered:
            return
        if "croc_secret=" in lowered:
            return

        if len(record.output_excerpt) > 400:
            record.output_excerpt = record.output_excerpt[-400:]
        record.output_excerpt.append(line)
        event = self.parser.parse(line)
        if event.speed_text:
            record.speed_text = event.speed_text
        if event.failed and not record.error_message:
            record.error_message = line
        # Avoid saving history on every output line; this is a major UI freeze source on large transfers.
        self.transfer_output.emit(transfer_id, line)

    def _on_code(self, record: TransferRecord, transfer_id: str, code: str) -> None:
        if not record.code_phrase:
            record.code_phrase = code
            self.history_service.update(record)
            self.transfer_updated.emit(transfer_id)

    def _on_progress(self, record: TransferRecord, transfer_id: str, pct: float) -> None:
        new_progress = int(pct)
        if record.bytes_done == new_progress:
            return
        record.bytes_done = new_progress
        self.history_service.update(record)
        self.transfer_updated.emit(transfer_id)

    def _on_finished(self, record: TransferRecord, transfer_id: str, exit_code: int) -> None:
        no_files_transferred = any("no files transferred" in line.lower() for line in record.output_excerpt[-80:])
        room_not_ready = any(
            ("room (secure channel) not ready" in line.lower() or "peer disconnected" in line.lower())
            for line in record.output_excerpt[-80:]
        )
        status = "completed" if exit_code == 0 and not no_files_transferred else "failed"
        if no_files_transferred and not record.error_message:
            record.error_message = "No files transferred (likely destination collision or skipped write)."
        if room_not_ready and not record.error_message:
            record.error_message = "Receive session is no longer active. Ask sender for a new code."
        if status == "completed":
            done_line = "[system] DONE"
            record.output_excerpt.append(done_line)
            self.transfer_output.emit(transfer_id, done_line)
            self._auto_remember_device(record)
        self.history_service.mark_finished(record, status=status, error=record.error_message)
        self.transfer_finished.emit(transfer_id, status)
        self.transfer_updated.emit(transfer_id)
        self.active.pop(transfer_id, None)

    def cancel(self, transfer_id: str) -> None:
        active = self.active.get(transfer_id)
        if not active:
            return
        active.runtime.cancel()
        self.history_service.mark_finished(active.record, status="canceled", error="Canceled by user")
        self.transfer_finished.emit(transfer_id, "canceled")
        self.active.pop(transfer_id, None)

    def retry(self, transfer_id: str) -> TransferRecord | None:
        records = self.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record:
            return None
        if record.direction in ("send", "selftest-send"):
            return self.start_send(paths=record.source_paths, code_phrase="", direction=record.direction)
        if record.direction in ("receive", "selftest-receive") and record.code_phrase:
            return self.start_receive(
                code_phrase=record.code_phrase,
                destination=record.destination_folder or str(Path.home() / "Downloads"),
                overwrite=False,
                direction=record.direction,
            )
        return None

    def _take_reserved_code(self, profile_name: str) -> str:
        self._prune_reserved_codes()
        reserved = self._reserved_codes.pop(profile_name, None)
        if not reserved:
            return ""
        if reserved.expires_at <= datetime.now(timezone.utc):
            return ""
        return reserved.code_phrase

    def _reserve_next_code(self, profile_name: str) -> tuple[str, datetime]:
        self._prune_reserved_codes()
        code = generate_code_phrase(profile_name)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        self._reserved_codes[profile_name] = ReservedCode(code_phrase=code, expires_at=expires_at)
        return code, expires_at

    def _prune_reserved_codes(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [profile for profile, reserved in self._reserved_codes.items() if reserved.expires_at <= now]
        for profile in expired:
            self._reserved_codes.pop(profile, None)

    def _auto_remember_device(self, record: TransferRecord) -> None:
        code = (record.code_phrase or "").strip()
        if not code:
            return
        settings = self.settings_service.get()
        if code in settings.trusted_devices:
            return
        peer_label = code.rsplit("-", 1)[-1].strip() if "-" in code else "peer"
        if not peer_label:
            peer_label = "peer"
        # App-level convenience only: this alias is inferred from code text, not cryptographic identity.
        settings.trusted_devices[code] = f"Auto: {peer_label}"
        self.settings_service.save(settings)
