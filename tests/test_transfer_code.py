import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from utils.transfer_code import COMPRESSION_7ZIP, ParsedShareCode, build_share_code, parse_share_code
from models.transfer import TransferRecord
from services.transfer_service import ActiveTransfer, TransferService


def assert_parsed(
    case: unittest.TestCase,
    parsed: ParsedShareCode,
    *,
    share_code: str,
    connection_code: str,
    compression_mode: str,
    archive_name: str,
) -> None:
    case.assertEqual(parsed.share_code, share_code)
    case.assertEqual(parsed.connection_code, connection_code)
    case.assertEqual(parsed.compression_mode, compression_mode)
    case.assertEqual(parsed.archive_name, archive_name)


class TransferCodeTests(unittest.TestCase):
    def test_build_uncompressed_share_code_returns_base_code(self) -> None:
        self.assertEqual(build_share_code("cd-spark-river-ben"), "cd-spark-river-ben")

    def test_build_compressed_share_code_embeds_marker_before_final_token(self) -> None:
        self.assertEqual(
            build_share_code("cd-spark-river-ben", compression_mode=COMPRESSION_7ZIP),
            "cd-spark-river-z-ben",
        )

    def test_parse_uncompressed_share_code_keeps_connection_code(self) -> None:
        parsed = parse_share_code("cd-spark-river-ben")
        assert_parsed(
            self,
            parsed,
            share_code="cd-spark-river-ben",
            connection_code="cd-spark-river-ben",
            compression_mode="",
            archive_name="",
        )

    def test_parse_new_compressed_share_code_removes_marker_for_connection_code(self) -> None:
        parsed = parse_share_code("cd-spark-river-z-ben")
        assert_parsed(
            self,
            parsed,
            share_code="cd-spark-river-z-ben",
            connection_code="cd-spark-river-ben",
            compression_mode=COMPRESSION_7ZIP,
            archive_name="",
        )

    def test_parse_old_compressed_share_code_keeps_legacy_archive_name(self) -> None:
        parsed = parse_share_code("cd-spark-river-ben::cd1:z7:test.7z")
        assert_parsed(
            self,
            parsed,
            share_code="cd-spark-river-ben::cd1:z7:test.7z",
            connection_code="cd-spark-river-ben",
            compression_mode=COMPRESSION_7ZIP,
            archive_name="test.7z",
        )

    def test_z_inside_normal_word_does_not_trigger_compression(self) -> None:
        parsed = parse_share_code("cd-spark-river-zed-ben")
        self.assertEqual(parsed.compression_mode, "")
        self.assertEqual(parsed.connection_code, "cd-spark-river-zed-ben")

    def test_short_code_with_z_token_is_handled_safely(self) -> None:
        parsed = parse_share_code("cd-z-ben")
        self.assertEqual(parsed.compression_mode, "")
        self.assertEqual(parsed.connection_code, "cd-z-ben")

    def test_malformed_legacy_code_does_not_crash(self) -> None:
        parsed = parse_share_code("cd-spark-river-ben::cd1:badpayload")
        self.assertEqual(parsed.compression_mode, "")
        self.assertEqual(parsed.connection_code, "cd-spark-river-ben")

    def test_empty_code_does_not_crash(self) -> None:
        parsed = parse_share_code("")
        self.assertEqual(parsed.share_code, "")
        self.assertEqual(parsed.connection_code, "")

    def test_extract_runtime_archive_name_reads_receive_output(self) -> None:
        self.assertEqual(
            TransferService._extract_runtime_archive_name("[system] Receiving 'dummy_1536mb.bin.7z' (229.2 kB)"),
            "dummy_1536mb.bin.7z",
        )

    def test_resolve_received_archive_prefers_detected_existing_archive_even_with_old_mtime(self) -> None:
        service = _build_transfer_service_test_double()
        with TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            archive_path = destination / "dummy_1536mb.bin.7z"
            archive_path.write_bytes(b"archive")
            old_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()
            archive_path.touch()
            os.utime(archive_path, (old_timestamp, old_timestamp))

            record = TransferRecord(
                direction="receive",
                destination_folder=str(destination),
                compression_mode=COMPRESSION_7ZIP,
                started_at=datetime.now(timezone.utc).isoformat(),
            )
            active = ActiveTransfer(
                record=record,
                runtime=None,  # type: ignore[arg-type]
                receive_started_at=datetime.now(timezone.utc),
                detected_archive_names=["dummy_1536mb.bin.7z"],
            )

            resolved = service._resolve_received_archive(record, active)
            self.assertEqual(resolved, archive_path)

    def test_resolve_received_archive_prefers_runtime_archive_name_when_present(self) -> None:
        service = _build_transfer_service_test_double()
        with TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            archive_path = destination / "dummy_1536mb.bin.7z"
            archive_path.write_bytes(b"archive")

            record = TransferRecord(
                direction="receive",
                destination_folder=str(destination),
                compression_mode=COMPRESSION_7ZIP,
                archive_name="dummy_1536mb.bin.7z",
            )

            resolved = service._resolve_received_archive(record, None)
            self.assertEqual(resolved, archive_path)


class _TransferServiceTestDouble:
    _AUTO_EXTRACT_TOLERANCE_SECONDS = TransferService._AUTO_EXTRACT_TOLERANCE_SECONDS
    _resolve_received_archive = TransferService._resolve_received_archive
    _find_recent_archives = TransferService._find_recent_archives
    _parse_started_at = staticmethod(TransferService._parse_started_at)
    _existing_detected_archives = staticmethod(TransferService._existing_detected_archives)


def _build_transfer_service_test_double() -> _TransferServiceTestDouble:
    return _TransferServiceTestDouble()


if __name__ == "__main__":
    unittest.main()
