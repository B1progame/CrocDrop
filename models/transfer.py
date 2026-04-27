from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4

TransferDirection = Literal["send", "receive", "selftest-send", "selftest-receive"]
TransferStatus = Literal["queued", "preparing", "running", "completed", "failed", "canceled"]


@dataclass(slots=True)
class TransferRecord:
    transfer_id: str = field(default_factory=lambda: str(uuid4()))
    direction: TransferDirection = "send"
    status: TransferStatus = "queued"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: str = ""
    ended_at: str = ""
    code_phrase: str = ""
    connection_code: str = ""
    source_paths: list[str] = field(default_factory=list)
    destination_folder: str = ""
    compression_mode: str = ""
    archive_name: str = ""
    auto_extracted: bool = False
    bytes_total: int = 0
    bytes_done: int = 0
    phase: str = ""
    phase_message: str = ""
    phase_percent: float | None = None
    phase_eta_seconds: float | None = None
    phase_indeterminate: bool = False
    speed_text: str = ""
    relay: str = "public"
    croc_version: str = ""
    error_message: str = ""
    output_excerpt: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "TransferRecord":
        known = {k: payload.get(k) for k in cls.__dataclass_fields__.keys() if k in payload}
        return cls(**known)
