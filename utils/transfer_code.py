from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote

COMPRESSION_NONE = ""
COMPRESSION_7ZIP = "7zip"
_MARKER = "::cd1:"
_FORMAT_7ZIP = "z7"
_EMBEDDED_7ZIP_TOKEN = "z"


@dataclass(slots=True)
class ParsedShareCode:
    share_code: str
    connection_code: str
    compression_mode: str = COMPRESSION_NONE
    archive_name: str = ""


def build_share_code(connection_code: str, compression_mode: str = COMPRESSION_NONE, archive_name: str = "") -> str:
    base_code = connection_code.strip()
    if not base_code:
        raise ValueError("Connection code is required.")
    if compression_mode != COMPRESSION_7ZIP:
        return base_code
    return _embed_compression_marker(base_code)


def parse_share_code(code: str) -> ParsedShareCode:
    share_code = code.strip()
    if not share_code:
        return ParsedShareCode(share_code="", connection_code="")

    legacy = _parse_legacy_share_code(share_code)
    if legacy is not None:
        return legacy

    embedded_connection_code = _strip_embedded_compression_marker(share_code)
    if embedded_connection_code != share_code:
        return ParsedShareCode(
            share_code=share_code,
            connection_code=embedded_connection_code,
            compression_mode=COMPRESSION_7ZIP,
            archive_name="",
        )

    return ParsedShareCode(share_code=share_code, connection_code=share_code)


def _embed_compression_marker(base_code: str) -> str:
    sanitized = _strip_embedded_compression_marker(base_code.strip())
    parts = sanitized.split("-")
    if len(parts) >= 3 and parts[0].lower() == "cd":
        return "-".join([*parts[:-1], _EMBEDDED_7ZIP_TOKEN, parts[-1]])
    if len(parts) >= 2:
        return "-".join([*parts[:-1], _EMBEDDED_7ZIP_TOKEN, parts[-1]])
    return f"{sanitized}-{_EMBEDDED_7ZIP_TOKEN}"


def _strip_embedded_compression_marker(share_code: str) -> str:
    parts = share_code.strip().split("-")
    if _has_embedded_compression_marker(parts):
        return "-".join([*parts[:-2], parts[-1]])
    return share_code.strip()


def _has_embedded_compression_marker(parts: list[str]) -> bool:
    return len(parts) >= 4 and parts[0].lower() == "cd" and parts[-2].lower() == _EMBEDDED_7ZIP_TOKEN


def _parse_legacy_share_code(share_code: str) -> ParsedShareCode | None:
    if _MARKER not in share_code:
        return None

    connection_code, payload = share_code.split(_MARKER, 1)
    connection_code = connection_code.strip()
    if not connection_code:
        return ParsedShareCode(share_code=share_code, connection_code=share_code)

    format_token, _, raw_archive_name = payload.partition(":")
    if format_token.lower() != _FORMAT_7ZIP:
        return ParsedShareCode(share_code=share_code, connection_code=connection_code)

    archive_name = unquote(raw_archive_name).strip()
    return ParsedShareCode(
        share_code=share_code,
        connection_code=connection_code,
        compression_mode=COMPRESSION_7ZIP,
        archive_name=archive_name,
    )
