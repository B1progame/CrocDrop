import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from services.sevenzip_service import SevenZipService, SevenZipServiceError


class _FakeLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None


class _FakeLogService:
    def get_logger(self, _name: str) -> _FakeLogger:
        return _FakeLogger()


class _FakeResponse:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None, fail_after_reads: int | None = None):
        self._stream = io.BytesIO(payload)
        self.headers = headers or {}
        self._fail_after_reads = fail_after_reads
        self._read_count = 0

    def read(self, size: int = -1) -> bytes:
        self._read_count += 1
        if self._fail_after_reads is not None and self._read_count > self._fail_after_reads:
            raise OSError("simulated download failure")
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _TestSevenZipService(SevenZipService):
    def __init__(self, managed_path: Path):
        super().__init__(_FakeLogService())
        self._managed_path = managed_path

    def managed_binary_path(self) -> Path:
        return self._managed_path

    def _discover_cli_url(self) -> str:
        return "https://github.com/ip7z/7zip/releases/download/test/7zr.exe"


class SevenZipServiceTests(unittest.TestCase):
    def test_install_cli_writes_managed_binary_and_status_reports_installed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            managed_path = Path(temp_dir) / "tools" / "7zip" / "7zr.exe"
            service = _TestSevenZipService(managed_path)

            with patch("services.sevenzip_service.urlopen", return_value=_FakeResponse(b"abc", {"Content-Length": "3"})):
                installed_path = service.install_cli()

            self.assertEqual(installed_path, managed_path)
            self.assertTrue(managed_path.exists())
            self.assertEqual(managed_path.read_bytes(), b"abc")
            self.assertTrue(service.status()["installed"])

    def test_download_progress_callback_receives_increasing_values(self) -> None:
        with TemporaryDirectory() as temp_dir:
            managed_path = Path(temp_dir) / "tools" / "7zip" / "7zr.exe"
            service = _TestSevenZipService(managed_path)
            payload = b"x" * (SevenZipService.DOWNLOAD_CHUNK_SIZE * 2 + 17)
            progress_updates: list[int] = []

            def on_progress(event: dict) -> None:
                downloaded = event.get("downloaded")
                if isinstance(downloaded, int):
                    progress_updates.append(downloaded)

            with patch(
                "services.sevenzip_service.urlopen",
                return_value=_FakeResponse(payload, {"Content-Length": str(len(payload))}),
            ):
                service.install_cli(progress_callback=on_progress)

            self.assertGreaterEqual(len(progress_updates), 3)
            self.assertEqual(progress_updates, sorted(progress_updates))
            self.assertEqual(progress_updates[-1], len(payload))

    def test_partial_download_cleanup_on_failure(self) -> None:
        with TemporaryDirectory() as temp_dir:
            managed_path = Path(temp_dir) / "tools" / "7zip" / "7zr.exe"
            service = _TestSevenZipService(managed_path)

            with patch(
                "services.sevenzip_service.urlopen",
                return_value=_FakeResponse(b"x" * 128, {"Content-Length": "128"}, fail_after_reads=1),
            ):
                with self.assertRaises(SevenZipServiceError):
                    service.install_cli()

            self.assertFalse(managed_path.exists())
            self.assertFalse(managed_path.with_name("7zr.exe.tmp").exists())

    def test_install_cli_skips_redownload_when_managed_binary_exists(self) -> None:
        with TemporaryDirectory() as temp_dir:
            managed_path = Path(temp_dir) / "tools" / "7zip" / "7zr.exe"
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_bytes(b"existing")
            service = _TestSevenZipService(managed_path)

            with patch.object(service, "_download_to_file") as download_mock:
                installed_path = service.install_cli()

            self.assertEqual(installed_path, managed_path)
            download_mock.assert_not_called()

    def test_iter_output_records_splits_carriage_return_progress_updates(self) -> None:
        records = list(SevenZipService._iter_output_records(io.StringIO("  0%\r     \r 49%\rEverything is Ok\n")))
        self.assertEqual(records, ["0%", "49%", "Everything is Ok"])

    def test_parse_percent_from_output_accepts_sevenzip_progress_lines(self) -> None:
        with TemporaryDirectory() as temp_dir:
            managed_path = Path(temp_dir) / "tools" / "7zip" / "7zr.exe"
            service = _TestSevenZipService(managed_path)

            self.assertEqual(service._parse_percent_from_output("100% 1"), 100.0)
            self.assertEqual(service._parse_percent_from_output(" 49%"), 49.0)
            self.assertIsNone(service._parse_percent_from_output("Everything is Ok"))


if __name__ == "__main__":
    unittest.main()
