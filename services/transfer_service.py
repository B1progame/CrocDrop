from __future__ import annotations

import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from models.transfer import TransferRecord
from services.sevenzip_service import PreparedArchive, SevenZipService, SevenZipServiceError
from services.transfer_parser import TransferOutputParser
from utils.codegen import generate_code_phrase
from utils.transfer_code import COMPRESSION_7ZIP, build_share_code, parse_share_code


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
        for thread in self._threads:
            thread.start()

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
        exit_code = self.process.wait()
        self.finished.emit(self.transfer_id, exit_code)

    def cancel(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            self.state_changed.emit(self.transfer_id, "canceled")


class SendPreparationWorker(QObject):
    progress = Signal(object)
    ready = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, sevenzip_service: SevenZipService, source_paths: list[str], compression_level: int):
        super().__init__()
        self.sevenzip_service = sevenzip_service
        self.source_paths = list(source_paths)
        self.compression_level = compression_level

    @Slot()
    def run(self) -> None:
        try:
            prepared = self.sevenzip_service.create_send_archive(
                self.source_paths,
                compression_level=self.compression_level,
                progress_callback=self.progress.emit,
            )
            self.ready.emit(prepared)
        except SevenZipServiceError as exc:
            self.failed.emit({"phase": "compressing", "detail": str(exc)})
        finally:
            self.finished.emit()


class ReceiveExtractionWorker(QObject):
    progress = Signal(object)
    completed = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, sevenzip_service: SevenZipService, archive_path: Path, destination: Path):
        super().__init__()
        self.sevenzip_service = sevenzip_service
        self.archive_path = archive_path
        self.destination = destination

    @Slot()
    def run(self) -> None:
        try:
            self.sevenzip_service.extract_archive(
                self.archive_path,
                self.destination,
                progress_callback=self.progress.emit,
            )
            self.completed.emit(self.archive_path)
        except SevenZipServiceError as exc:
            self.failed.emit({"phase": "extracting", "detail": str(exc), "archive_path": str(self.archive_path)})
        finally:
            self.finished.emit()


@dataclass(slots=True)
class ActiveTransfer:
    record: TransferRecord
    runtime: TransferRuntime | None = None
    prepared_archive: PreparedArchive | None = None
    receive_started_at: datetime | None = None
    detected_archive_names: list[str] = field(default_factory=list)
    corrected_code_announced: bool = False
    last_phase_message: str = ""
    phase_started_monotonic: float | None = None
    prep_thread: QThread | None = None
    prep_worker: SendPreparationWorker | None = None
    extract_thread: QThread | None = None
    extract_worker: ReceiveExtractionWorker | None = None


@dataclass(slots=True)
class ReservedCode:
    code_phrase: str
    expires_at: datetime


class TransferService(QObject):
    _AUTO_EXTRACT_TOLERANCE_SECONDS = 5

    transfer_updated = Signal(str)
    transfer_output = Signal(str, str)
    transfer_finished = Signal(str, str)
    next_code_ready = Signal(str, str, str)  # transfer_id, code, expires_at_iso

    def __init__(self, croc_manager, sevenzip_service, history_service, settings_service, log_service):
        super().__init__()
        self.croc_manager = croc_manager
        self.sevenzip_service = sevenzip_service
        self.history_service = history_service
        self.settings_service = settings_service
        self.log = log_service.get_logger("transfer")
        self.parser = TransferOutputParser()
        self.active: dict[str, ActiveTransfer] = {}
        self._reserved_codes: dict[str, ReservedCode] = {}

    def get_record(self, transfer_id: str) -> TransferRecord | None:
        active = self.active.get(transfer_id)
        if active is not None:
            return active.record
        return self.history_service.get_record(transfer_id)

    def start_send(
        self,
        paths: list[str],
        code_phrase: str = "",
        direction: str = "send",
        compress_7zip: bool = False,
    ) -> TransferRecord:
        active_profile = (self.settings_service.get().current_profile or "guest").strip() or "guest"
        base_code = code_phrase.strip()
        if not base_code:
            reserved = self._take_reserved_code(active_profile)
            base_code = reserved if reserved else generate_code_phrase(active_profile)

        if not compress_7zip:
            return self._start_send_immediately(paths, base_code, direction, active_profile)

        record = TransferRecord(
            direction=direction,
            source_paths=list(paths),
            relay=self.settings_service.get().relay_mode,
            status="preparing",
            code_phrase=build_share_code(base_code, compression_mode=COMPRESSION_7ZIP),
            connection_code=base_code,
            compression_mode=COMPRESSION_7ZIP,
        )
        record.croc_version = self.croc_manager.get_version(Path(self.croc_manager.detect_binary().path))
        self.history_service.add(record)
        self.active[record.transfer_id] = ActiveTransfer(record=record)
        self._set_phase(record, record.transfer_id, phase="preparing", message="Preparing compressed transfer...", indeterminate=True)

        next_code, expires_at = self._reserve_next_code(active_profile)
        self.next_code_ready.emit(record.transfer_id, next_code, expires_at.isoformat())
        self.transfer_updated.emit(record.transfer_id)

        compression_level = self.settings_service.get().sevenzip_compression_level
        self._start_send_preparation(record.transfer_id, paths, compression_level)
        return record

    def start_receive(self, code_phrase: str, destination: str, overwrite: bool, direction: str = "receive") -> TransferRecord:
        parsed = parse_share_code(code_phrase)
        if not parsed.connection_code:
            raise ValueError("Missing croc code phrase.")

        receive_started_at = datetime.now(timezone.utc)
        process = self.croc_manager.launch_receive(
            code_phrase=parsed.connection_code,
            destination=destination,
            overwrite=overwrite,
        )
        record = TransferRecord(
            direction=direction,
            source_paths=[],
            destination_folder=destination,
            code_phrase=parsed.share_code,
            connection_code=parsed.connection_code,
            compression_mode=parsed.compression_mode,
            archive_name=parsed.archive_name,
            relay=self.settings_service.get().relay_mode,
            started_at=receive_started_at.isoformat(),
        )
        record.croc_version = self.croc_manager.get_version(Path(self.croc_manager.detect_binary().path))
        self.history_service.add(record)
        self.history_service.mark_started(record)

        runtime = TransferRuntime(record.transfer_id, process, self.parser)
        self._wire_runtime(record, runtime)
        self.active[record.transfer_id] = ActiveTransfer(
            record=record,
            runtime=runtime,
            receive_started_at=receive_started_at,
        )
        runtime.start()
        return record

    def _start_send_immediately(
        self,
        paths: list[str],
        base_code: str,
        direction: str,
        active_profile: str,
    ) -> TransferRecord:
        share_code = build_share_code(base_code)
        started_at = datetime.now(timezone.utc).isoformat()
        process = self.croc_manager.launch_send(paths=list(paths), code_phrase=base_code)

        record = TransferRecord(
            direction=direction,
            source_paths=list(paths),
            relay=self.settings_service.get().relay_mode,
            started_at=started_at,
        )
        record.code_phrase = share_code
        record.connection_code = base_code
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

    def _start_send_preparation(self, transfer_id: str, paths: list[str], compression_level: int) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return

        thread = QThread(self)
        worker = SendPreparationWorker(self.sevenzip_service, paths, compression_level)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(lambda event, tid=transfer_id: self._on_phase_progress(tid, event))
        worker.ready.connect(lambda prepared, tid=transfer_id: self._on_send_prepared(tid, prepared))
        worker.failed.connect(lambda payload, tid=transfer_id: self._on_send_preparation_failed(tid, payload))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        active.prep_thread = thread
        active.prep_worker = worker
        thread.start()

    def _wire_runtime(self, record: TransferRecord, runtime: TransferRuntime) -> None:
        runtime.output_line.connect(lambda tid, line: self._on_output(record, tid, line))
        runtime.code_found.connect(lambda tid, code: self._on_code(record, tid, code))
        runtime.progress.connect(lambda tid, pct: self._on_progress(record, tid, pct))
        runtime.finished.connect(lambda tid, exit_code: self._on_finished(record, tid, exit_code))

    def _on_output(self, record: TransferRecord, transfer_id: str, line: str) -> None:
        lowered = line.lower()
        if "(for windows)" in lowered or "(for linux/macos)" in lowered:
            return
        if "croc_secret=" in lowered:
            return
        if self._should_hide_raw_compressed_send_line(record, line):
            active = self.active.get(transfer_id)
            if active is not None and "code is:" in lowered and not active.corrected_code_announced:
                active.corrected_code_announced = True
                self._append_system_line(record, transfer_id, f"[system] Use this CrocDrop code instead: {record.code_phrase}")
            return

        if len(record.output_excerpt) > 400:
            record.output_excerpt = record.output_excerpt[-400:]
        record.output_excerpt.append(line)
        event = self.parser.parse(line)
        active = self.active.get(transfer_id)
        changed = False
        if active is not None and record.direction in {"receive", "selftest-receive"} and record.compression_mode == COMPRESSION_7ZIP:
            self._capture_archive_names_from_output(active, line)
            detected_archive_name = self._extract_runtime_archive_name(line)
            if detected_archive_name and record.archive_name != detected_archive_name:
                record.archive_name = detected_archive_name
                changed = True
        if event.speed_text and record.speed_text != event.speed_text:
            record.speed_text = event.speed_text
            changed = True
        if event.failed and not record.error_message:
            record.error_message = line
            changed = True
        self.transfer_output.emit(transfer_id, line)
        if (
            active is not None
            and record.direction in {"send", "selftest-send"}
            and record.compression_mode == COMPRESSION_7ZIP
            and event.code_phrase
            and not active.corrected_code_announced
        ):
            active.corrected_code_announced = True
            self._append_system_line(record, transfer_id, f"[system] Use this CrocDrop code instead: {record.code_phrase}")
        if changed:
            self.transfer_updated.emit(transfer_id)

    def _on_code(self, record: TransferRecord, transfer_id: str, code: str) -> None:
        changed = False
        if record.compression_mode == COMPRESSION_7ZIP:
            if record.connection_code != code:
                record.connection_code = code
                changed = True
        else:
            if not record.code_phrase:
                record.code_phrase = code
                changed = True
            if not record.connection_code:
                record.connection_code = code
                changed = True
        if changed:
            self.history_service.update(record)
            self.transfer_updated.emit(transfer_id)

    def _on_progress(self, record: TransferRecord, transfer_id: str, pct: float) -> None:
        if record.phase_message:
            self._clear_phase(record)
        new_progress = int(pct)
        if record.bytes_done == new_progress:
            return
        record.bytes_done = new_progress
        self.transfer_updated.emit(transfer_id)

    def _on_finished(self, record: TransferRecord, transfer_id: str, exit_code: int) -> None:
        active = self.active.get(transfer_id)
        if transfer_id not in self.active and record.status == "canceled":
            return

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

        if status == "completed" and record.direction in {"receive", "selftest-receive"} and record.compression_mode == COMPRESSION_7ZIP:
            self._start_receive_extraction(transfer_id, record, active)
            return

        if status == "completed":
            self._append_system_line(record, transfer_id, "[system] DONE")
            self._auto_remember_device(record)

        self._complete_transfer(transfer_id, status=status, error=record.error_message)

    def cancel(self, transfer_id: str) -> None:
        active = self.active.get(transfer_id)
        if not active:
            return
        if active.runtime is None:
            return
        active.runtime.cancel()
        self.sevenzip_service.cleanup_prepared_archive(active.prepared_archive)
        self.history_service.mark_finished(active.record, status="canceled", error="Canceled by user")
        self.transfer_finished.emit(transfer_id, "canceled")
        self.active.pop(transfer_id, None)

    def retry(self, transfer_id: str) -> TransferRecord | None:
        records = self.history_service.list_records()
        record = next((item for item in records if item.transfer_id == transfer_id), None)
        if not record:
            return None
        if record.direction in ("send", "selftest-send"):
            return self.start_send(
                paths=record.source_paths,
                code_phrase="",
                direction=record.direction,
                compress_7zip=record.compression_mode == COMPRESSION_7ZIP,
            )
        if record.direction in ("receive", "selftest-receive") and record.code_phrase:
            return self.start_receive(
                code_phrase=record.code_phrase,
                destination=record.destination_folder or str(Path.home() / "Downloads"),
                overwrite=False,
                direction=record.direction,
            )
        return None

    def _start_receive_extraction(self, transfer_id: str, record: TransferRecord, active: ActiveTransfer | None) -> None:
        if active is None:
            self._complete_transfer(transfer_id, status="failed", error="Extraction failed. The archive was kept.")
            return
        try:
            archive_path = self._resolve_received_archive(record, active)
        except SevenZipServiceError as exc:
            self._append_system_line(record, transfer_id, f"[system] Auto-extract failed: {exc}")
            self._complete_transfer(transfer_id, status="failed", error=str(exc))
            return

        self._set_phase(record, transfer_id, phase="extracting", message="Extracting archive...", indeterminate=True)
        worker = ReceiveExtractionWorker(self.sevenzip_service, archive_path, Path(record.destination_folder))
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(lambda event, tid=transfer_id: self._on_phase_progress(tid, event))
        worker.completed.connect(lambda path, tid=transfer_id: self._on_receive_extraction_completed(tid, path))
        worker.failed.connect(lambda payload, tid=transfer_id: self._on_receive_extraction_failed(tid, payload))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        active.extract_thread = thread
        active.extract_worker = worker
        thread.start()

    def _on_phase_progress(self, transfer_id: str, event: dict[str, Any]) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return
        record = active.record
        phase = str(event.get("phase") or "")
        message = str(event.get("message") or "")
        raw_percent = event.get("percent")
        percent = float(raw_percent) if isinstance(raw_percent, (int, float)) else None
        indeterminate = bool(event.get("indeterminate", percent is None))
        eta_seconds = self._estimate_phase_eta(active, phase, percent)
        self._set_phase(
            record,
            transfer_id,
            phase=phase,
            message=message,
            percent=percent,
            eta_seconds=eta_seconds,
            indeterminate=indeterminate,
        )

    def _on_send_prepared(self, transfer_id: str, prepared_archive: PreparedArchive) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            self.sevenzip_service.cleanup_prepared_archive(prepared_archive)
            return

        record = active.record
        active.prepared_archive = prepared_archive
        record.archive_name = prepared_archive.archive_name
        archive_size_text = self._format_bytes(prepared_archive.archive_path.stat().st_size)
        self._append_system_line(
            record,
            transfer_id,
            f"[system] Prepared {prepared_archive.archive_name} for transfer ({archive_size_text}).",
        )
        self._set_phase(record, transfer_id, phase="starting-transfer", message="Starting transfer...", indeterminate=True)

        try:
            process = self.croc_manager.launch_send(paths=[str(prepared_archive.archive_path)], code_phrase=record.connection_code)
        except Exception as exc:
            self.log.error("Failed to launch compressed send after preparation: %s", exc)
            self.sevenzip_service.cleanup_prepared_archive(prepared_archive)
            self._append_system_line(record, transfer_id, "[system] Compression failed.")
            self._complete_transfer(transfer_id, status="failed", error="Compression failed.")
            return

        self._clear_phase(record)
        self.history_service.mark_started(record)
        runtime = TransferRuntime(transfer_id, process, self.parser)
        active.runtime = runtime
        active.prep_thread = None
        active.prep_worker = None
        self._wire_runtime(record, runtime)
        self.transfer_updated.emit(transfer_id)
        runtime.start()

    def _on_send_preparation_failed(self, transfer_id: str, payload: dict[str, Any]) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return

        detail = str(payload.get("detail") or "Unknown 7-Zip error.")
        phase = active.record.phase or str(payload.get("phase") or "")
        self.log.error("Compressed send preparation failed during %s: %s", phase, detail)

        if phase == "sevenzip-download":
            self._append_system_line(active.record, transfer_id, "[system] Could not download 7-Zip CLI. Check your internet connection and try again.")
            self._append_system_line(active.record, transfer_id, "[system] 7-Zip download failed before compression started.")
            error_message = "Could not download 7-Zip CLI. Check your internet connection and try again."
        else:
            self._append_system_line(active.record, transfer_id, "[system] Compression failed.")
            error_message = "Compression failed."

        self.sevenzip_service.cleanup_prepared_archive(active.prepared_archive)
        self._complete_transfer(transfer_id, status="failed", error=error_message)

    def _on_receive_extraction_completed(self, transfer_id: str, archive_path_obj: object) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return

        record = active.record
        archive_path = Path(str(archive_path_obj))
        record.auto_extracted = True
        try:
            archive_path.unlink()
        except OSError as exc:
            self.log.warning("Failed to delete extracted archive %s: %s", archive_path, exc)
            self._append_system_line(record, transfer_id, f"[system] Extracted successfully, but could not delete {archive_path.name}.")
        else:
            self._append_system_line(record, transfer_id, "[system] Temporary archive removed.")
            self._append_system_line(record, transfer_id, f"[system] Auto-extracted {archive_path.name} into {record.destination_folder}")

        self._clear_phase(record)
        self._append_system_line(record, transfer_id, "[system] DONE")
        self._auto_remember_device(record)
        self._complete_transfer(transfer_id, status="completed", error="")

    def _on_receive_extraction_failed(self, transfer_id: str, payload: dict[str, Any]) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return

        detail = str(payload.get("detail") or "Unknown extraction error.")
        self.log.error("Compressed receive extraction failed: %s", detail)
        self._append_system_line(active.record, transfer_id, "[system] Extraction failed. The archive was kept.")
        self._complete_transfer(transfer_id, status="failed", error="Extraction failed. The archive was kept.")

    def _complete_transfer(self, transfer_id: str, status: str, error: str) -> None:
        active = self.active.get(transfer_id)
        if active is None:
            return

        record = active.record
        record.error_message = error
        self._clear_phase(record)
        self.history_service.mark_finished(record, status=status, error=error)
        self.transfer_finished.emit(transfer_id, status)
        self.transfer_updated.emit(transfer_id)
        if active.prepared_archive is not None:
            self.sevenzip_service.cleanup_prepared_archive(active.prepared_archive)
        self.active.pop(transfer_id, None)

    def _set_phase(
        self,
        record: TransferRecord,
        transfer_id: str,
        *,
        phase: str,
        message: str,
        percent: float | None = None,
        eta_seconds: float | None = None,
        indeterminate: bool = False,
    ) -> None:
        active = self.active.get(transfer_id)
        previous_phase = record.phase
        record.phase = phase
        record.phase_message = message
        record.phase_percent = percent
        record.phase_eta_seconds = eta_seconds
        record.phase_indeterminate = indeterminate
        if active is not None and phase != previous_phase:
            active.phase_started_monotonic = time.monotonic()
        if active is not None and message and active.last_phase_message != message:
            active.last_phase_message = message
            self._append_system_line(record, transfer_id, f"[system] {message}")
        self.transfer_updated.emit(transfer_id)

    @staticmethod
    def _clear_phase(record: TransferRecord) -> None:
        record.phase = ""
        record.phase_message = ""
        record.phase_percent = None
        record.phase_eta_seconds = None
        record.phase_indeterminate = False

    @staticmethod
    def _estimate_phase_eta(active: ActiveTransfer, phase: str, percent: float | None) -> float | None:
        if percent is None or percent <= 0.0 or percent >= 100.0:
            return None
        if active.record.phase != phase or active.phase_started_monotonic is None:
            return None
        elapsed = max(0.0, time.monotonic() - active.phase_started_monotonic)
        if elapsed <= 0.0:
            return None
        remaining_ratio = (100.0 - percent) / percent
        return max(0.0, elapsed * remaining_ratio)

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
        code = (record.connection_code or record.code_phrase or "").strip()
        if not code:
            return
        settings = self.settings_service.get()
        if code in settings.trusted_devices:
            return
        peer_label = code.rsplit("-", 1)[-1].strip() if "-" in code else "peer"
        if not peer_label:
            peer_label = "peer"
        settings.trusted_devices[code] = f"Auto: {peer_label}"
        self.settings_service.save(settings)

    def _resolve_received_archive(self, record: TransferRecord, active: ActiveTransfer | None) -> Path:
        destination = Path(record.destination_folder)
        archive_name = record.archive_name.strip()
        if archive_name:
            expected = destination / archive_name
            if expected.exists():
                return expected
        detected_names = self._existing_detected_archives(destination, active)
        if len(detected_names) == 1:
            return detected_names[0]
        receive_started_at = active.receive_started_at if active is not None else self._parse_started_at(record.started_at)
        candidates = self._find_recent_archives(destination, receive_started_at)
        if archive_name:
            named_match = [item for item in candidates if item.name == archive_name]
            if len(named_match) == 1:
                return named_match[0]

        existing_detected_names = [item.name for item in detected_names]
        if existing_detected_names:
            hinted_candidates = [item for item in candidates if item.name in existing_detected_names]
            if len(hinted_candidates) == 1:
                return hinted_candidates[0]

        if len(candidates) == 1:
            return candidates[0]

        raise SevenZipServiceError("Compressed archive could not be identified automatically. Please extract the .7z manually.")

    def _append_system_line(self, record: TransferRecord, transfer_id: str, line: str) -> None:
        record.output_excerpt.append(line)
        self.transfer_output.emit(transfer_id, line)

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        units = ["B", "kB", "MB", "GB", "TB"]
        value = float(max(0, size_bytes))
        for unit in units:
            if value < 1000.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1000.0
        return f"{size_bytes} B"

    @staticmethod
    def _should_hide_raw_compressed_send_line(record: TransferRecord, line: str) -> bool:
        if record.direction not in {"send", "selftest-send"} or record.compression_mode != COMPRESSION_7ZIP:
            return False

        normalized = line.strip().lower()
        if not normalized:
            return False
        if "code is:" in normalized:
            return True
        if "on the other computer run:" in normalized:
            return True
        if "code copied to clipboard!" in normalized:
            return True
        if normalized.startswith("[system]") and "croc " in normalized and record.connection_code.lower() in normalized:
            return True
        return False

    def _capture_archive_names_from_output(self, active: ActiveTransfer, line: str) -> None:
        patterns = (
            r'"(?P<name>[^"\r\n]+\.7z)"',
            r"'(?P<name>[^'\r\n]+\.7z)'",
            r"(?P<name>[^\s\"']+\.7z)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                candidate = Path(match.group("name")).name.strip()
                if candidate and candidate not in active.detected_archive_names:
                    active.detected_archive_names.append(candidate)

    @staticmethod
    def _extract_runtime_archive_name(line: str) -> str:
        match = re.search(r"receiving\s+['\"](?P<name>[^'\"]+\.7z)['\"]", line, re.IGNORECASE)
        if not match:
            return ""
        return Path(match.group("name")).name.strip()

    @staticmethod
    def _existing_detected_archives(destination: Path, active: ActiveTransfer | None) -> list[Path]:
        if active is None:
            return []

        matches: list[Path] = []
        for name in dict.fromkeys(active.detected_archive_names):
            candidate = destination / name
            if candidate.exists():
                matches.append(candidate)
        return matches

    def _find_recent_archives(self, destination: Path, receive_started_at: datetime | None) -> list[Path]:
        if not destination.exists():
            return []

        threshold = None
        if receive_started_at is not None:
            threshold = receive_started_at.timestamp() - self._AUTO_EXTRACT_TOLERANCE_SECONDS

        candidates: list[Path] = []
        for item in destination.glob("*.7z"):
            try:
                stat = item.stat()
            except OSError:
                continue
            if threshold is not None and stat.st_mtime < threshold:
                continue
            candidates.append(item)
        return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)

    @staticmethod
    def _parse_started_at(value: str) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
