from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from utils.hashing import sha256_of_file


@dataclass(slots=True)
class SelfTestState:
    test_id: str
    source_file: Path
    source_hash: str
    receive_dir: Path
    send_transfer_id: str = ""
    receive_transfer_id: str = ""
    code_phrase: str = ""


class DebugService(QObject):
    self_test_progress = Signal(str)
    self_test_finished = Signal(bool, str)

    def __init__(self, transfer_service, croc_manager, log_service):
        super().__init__()
        self.transfer_service = transfer_service
        self.croc_manager = croc_manager
        self.log = log_service.get_logger("debug")
        self._state: SelfTestState | None = None

        self.transfer_service.transfer_updated.connect(self._on_transfer_updated)
        self.transfer_service.transfer_finished.connect(self._on_transfer_finished)

    def generate_dummy_file(self, directory: Path, size_mb: int = 10) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        file_path = directory / f"dummy_{size_mb}mb.bin"
        size_bytes = int(size_mb) * 1024 * 1024
        free_bytes = shutil.disk_usage(directory).free
        if size_bytes > free_bytes:
            raise RuntimeError(
                f"Not enough free disk space. Needed ~{size_mb} MB, available ~{free_bytes // (1024 * 1024)} MB."
            )

        # Use sparse/truncate creation for large files so >1GB remains fast and reliable.
        with file_path.open("wb") as f:
            if size_bytes > 0:
                f.seek(size_bytes - 1)
                f.write(b"\0")
        self.log.info("Dummy file generated: %s", file_path)
        return file_path

    def run_self_test(self, size_mb: int = 5) -> None:
        if self._state is not None:
            self.self_test_progress.emit("A self-test is already running. Wait for it to finish before starting another.")
            return

        base = Path(tempfile.mkdtemp(prefix="crocdrop_selftest_"))
        send_dir = base / "send"
        recv_dir = base / "recv"
        recv_dir.mkdir(parents=True, exist_ok=True)
        source_file = self.generate_dummy_file(send_dir, size_mb=size_mb)
        source_hash = sha256_of_file(source_file)
        state = SelfTestState(test_id=base.name, source_file=source_file, source_hash=source_hash, receive_dir=recv_dir)
        self._state = state

        self.self_test_progress.emit(f"Self-test started in {base}")
        record = self.transfer_service.start_send([str(source_file)], direction="selftest-send")
        state.send_transfer_id = record.transfer_id
        self.self_test_progress.emit("Sender started. Waiting for code phrase...")

    def _on_transfer_updated(self, transfer_id: str) -> None:
        if not self._state:
            return
        state = self._state
        if transfer_id != state.send_transfer_id:
            return

        records = self.transfer_service.history_service.list_records()
        record = next((r for r in records if r.transfer_id == transfer_id), None)
        if not record or not record.code_phrase or state.receive_transfer_id:
            return

        state.code_phrase = record.code_phrase
        self.self_test_progress.emit(f"Code captured: {state.code_phrase}. Starting local receiver...")
        recv_record = self.transfer_service.start_receive(
            code_phrase=state.code_phrase,
            destination=str(state.receive_dir),
            overwrite=True,
            direction="selftest-receive",
        )
        state.receive_transfer_id = recv_record.transfer_id

    def _on_transfer_finished(self, transfer_id: str, status: str) -> None:
        if not self._state:
            return
        state = self._state
        if transfer_id not in {state.send_transfer_id, state.receive_transfer_id}:
            return

        if status in {"failed", "canceled"}:
            records = self.transfer_service.history_service.list_records()
            failed_record = next((r for r in records if r.transfer_id == transfer_id), None)
            detail = failed_record.error_message if failed_record and failed_record.error_message else "No parser error captured."
            if failed_record and failed_record.output_excerpt:
                detail = failed_record.output_excerpt[-1]
            self.self_test_finished.emit(
                False,
                f"Transfer {transfer_id} ended with status={status}. Detail: {detail}",
            )
            self._state = None
            return

        if state.send_transfer_id and state.receive_transfer_id:
            records = self.transfer_service.history_service.list_records()
            send_record = next((r for r in records if r.transfer_id == state.send_transfer_id), None)
            recv_record = next((r for r in records if r.transfer_id == state.receive_transfer_id), None)
            if not send_record or not recv_record:
                return
            if send_record.status != "completed" or recv_record.status != "completed":
                return

            received_files = list(state.receive_dir.rglob("*"))
            payload = next((p for p in received_files if p.is_file()), None)
            if not payload:
                self.self_test_finished.emit(False, "No file found in receive directory")
                self._state = None
                return

            recv_hash = sha256_of_file(payload)
            if recv_hash == state.source_hash:
                self.self_test_finished.emit(True, f"PASS: hash matched ({recv_hash[:12]}...)")
            else:
                self.self_test_finished.emit(False, "FAIL: hash mismatch")
            self._state = None

    def launch_second_instance(self) -> subprocess.Popen:
        app_entry = str(Path(__file__).resolve().parents[1] / "main.py")
        cmd = [sys.executable, app_entry, "--debug-peer"]
        self.log.info("Launching secondary instance: %s", cmd)
        return subprocess.Popen(cmd)

    def backend_health(self) -> dict:
        diag = self.croc_manager.diagnostics()
        diag["version_probe"] = self.croc_manager.get_version(Path(diag["path"])) if diag.get("path") else "missing"
        return diag
