from __future__ import annotations

import re

from models.croc import ParsedTransferEvent


class TransferOutputParser:
    """Parser is intentionally isolated because croc output can vary by version."""

    code_patterns = [
        re.compile(r"Code is:\s*(?P<code>.+)$", re.IGNORECASE),
        re.compile(r"secret(?: code)?\s*[:=]\s*(?P<code>[\w-]+)", re.IGNORECASE),
    ]
    percent_pattern = re.compile(r"(?P<pct>\d{1,3}(?:\.\d+)?)%")
    speed_pattern = re.compile(r"(?P<speed>\d+(?:\.\d+)?\s?(?:[KMG]?B|[KMG]?iB)/s)", re.IGNORECASE)

    def parse(self, line: str) -> ParsedTransferEvent:
        event = ParsedTransferEvent(level="info", message=line.rstrip())

        lowered = line.lower()
        if any(key in lowered for key in ["error", "failed", "panic", "invalid"]):
            event.level = "error"
            event.failed = True
        if "no files transferred" in lowered:
            event.level = "error"
            event.failed = True
        if "room (secure channel) not ready" in lowered or "peer disconnected" in lowered:
            event.level = "error"
            event.failed = True

        if any(key in lowered for key in ["finished", "complete", "received", "sent"]):
            event.completed = True

        for pattern in self.code_patterns:
            match = pattern.search(line)
            if match:
                event.code_phrase = match.group("code").strip()
                break

        pct_match = self.percent_pattern.search(line)
        if pct_match:
            try:
                event.progress_percent = float(pct_match.group("pct"))
            except ValueError:
                event.progress_percent = None

        speed_match = self.speed_pattern.search(line)
        if speed_match:
            event.speed_text = speed_match.group("speed")

        return event
