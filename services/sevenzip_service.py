from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils.paths import croc_runtime_dir, tools_dir


class SevenZipServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class PreparedArchive:
    archive_path: Path
    archive_name: str
    cleanup_root: Path


ProgressCallback = Callable[[dict[str, Any]], None]


class SevenZipService:
    DOWNLOAD_PAGE_URL = "https://www.7-zip.org/download.html"
    OFFICIAL_DOWNLOAD_PREFIX = "https://github.com/ip7z/7zip/releases/download/"
    MANAGED_BINARY_NAME = "7zr.exe"
    DOWNLOAD_CHUNK_SIZE = 64 * 1024
    _PERCENT_PATTERN = re.compile(r"(?<!\d)(?P<pct>\d{1,3})%")

    def __init__(self, log_service):
        self.log = log_service.get_logger("sevenzip")
        self._background_install_thread: threading.Thread | None = None
        self._background_install_lock = threading.Lock()

    def create_send_archive(
        self,
        source_paths: list[str],
        compression_level: int = 9,
        progress_callback: ProgressCallback | None = None,
    ) -> PreparedArchive:
        if not source_paths:
            raise SevenZipServiceError("No files or folders were selected for compression.")

        sources = [Path(path).expanduser().resolve() for path in source_paths]
        missing = [str(path) for path in sources if not path.exists()]
        if missing:
            raise SevenZipServiceError(f"Cannot compress missing path(s): {', '.join(missing)}")

        session_root = self._create_session_root("send")
        try:
            seven_zip = self._resolve_cli(session_root, progress_callback=progress_callback)
            archive_name = self._build_archive_name(sources)
            archive_path = session_root / archive_name
            work_dir, members = self._build_archive_members(sources)
            cmd = [
                str(seven_zip),
                "a",
                "-bb1",
                "-bsp1",
                "-t7z",
                f"-mx={self._normalize_compression_level(compression_level)}",
                str(archive_path),
                *members,
            ]
            self._run(cmd, cwd=work_dir, action="compress", progress_callback=progress_callback)
            if not archive_path.exists():
                raise SevenZipServiceError("7-Zip finished without creating the archive.")
            self._emit_progress(
                progress_callback,
                phase="compressing",
                percent=100.0,
                indeterminate=False,
                message="Compression complete.",
            )
            return PreparedArchive(archive_path=archive_path, archive_name=archive_name, cleanup_root=session_root)
        except Exception:
            self.cleanup_path(session_root)
            raise

    def extract_archive(
        self,
        archive_path: Path,
        destination: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        if not archive_path.exists():
            raise SevenZipServiceError(f"Compressed file was not found for extraction: {archive_path}")

        destination.mkdir(parents=True, exist_ok=True)
        session_root = self._create_session_root("receive")
        try:
            seven_zip = self._resolve_cli(session_root, progress_callback=progress_callback)
            cmd = [str(seven_zip), "x", "-bb1", "-bsp1", str(archive_path), f"-o{destination}", "-y"]
            self._run(cmd, cwd=destination, action="extract", progress_callback=progress_callback)
            self._emit_progress(
                progress_callback,
                phase="extracting",
                percent=100.0,
                indeterminate=False,
                message="Extraction complete.",
            )
        finally:
            self.cleanup_path(session_root)

    def install_cli(self, progress_callback: ProgressCallback | None = None) -> Path:
        target = self.managed_binary_path()
        if target.exists():
            self._emit_progress(
                progress_callback,
                phase="sevenzip-ready",
                percent=100.0,
                indeterminate=False,
                message="7-Zip CLI ready.",
            )
            return target

        target.parent.mkdir(parents=True, exist_ok=True)
        download_url = self._discover_cli_url()
        self.log.info("Installing managed 7-Zip CLI from %s to %s", download_url, target)
        self._download_to_file(download_url, target, progress_callback=progress_callback)
        self.log.info("Installed managed 7-Zip CLI at %s", target)
        self._emit_progress(
            progress_callback,
            phase="sevenzip-ready",
            percent=100.0,
            indeterminate=False,
            message="7-Zip CLI ready.",
        )
        return target

    def uninstall_cli(self) -> tuple[bool, str]:
        target = self.managed_binary_path()
        if not target.exists():
            return False, f"7-Zip CLI is not installed at {target}"

        try:
            target.unlink()
            if target.parent.exists() and not any(target.parent.iterdir()):
                target.parent.rmdir()
        except OSError as exc:
            return False, f"Failed to uninstall 7-Zip CLI: {exc}"

        self.log.info("Uninstalled managed 7-Zip CLI from %s", target)
        return True, f"Removed 7-Zip CLI from {target}"

    def status(self) -> dict[str, str | bool]:
        path = self.managed_binary_path()
        installed = path.exists()
        return {
            "installed": installed,
            "path": str(path),
            "mode": "installed" if installed else "temporary",
        }

    def cleanup_prepared_archive(self, prepared: PreparedArchive | None) -> None:
        if not prepared:
            return
        self.cleanup_path(prepared.cleanup_root)

    def cleanup_path(self, path: Path | None) -> None:
        if not path:
            return
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as exc:
            self.log.warning("Failed to clean up temporary 7-Zip path %s: %s", path, exc)

    def _create_session_root(self, prefix: str) -> Path:
        root = croc_runtime_dir()
        return Path(tempfile.mkdtemp(prefix=f"sevenzip-{prefix}-", dir=str(root)))

    def managed_binary_path(self) -> Path:
        return tools_dir() / "7zip" / self.MANAGED_BINARY_NAME

    def _download_cli(self, session_root: Path, progress_callback: ProgressCallback | None = None) -> Path:
        download_url = self._discover_cli_url()
        target = session_root / self.MANAGED_BINARY_NAME
        self.log.info("Downloading temporary 7-Zip CLI from %s", download_url)
        self._download_to_file(download_url, target, progress_callback=progress_callback)
        return target

    def _resolve_cli(self, session_root: Path, progress_callback: ProgressCallback | None = None) -> Path:
        managed = self.managed_binary_path()
        if managed.exists():
            self._emit_progress(
                progress_callback,
                phase="sevenzip-ready",
                percent=100.0,
                indeterminate=False,
                message="7-Zip CLI ready.",
            )
            return managed

        try:
            return self.install_cli(progress_callback=progress_callback)
        except SevenZipServiceError as exc:
            self.log.warning("Managed 7-Zip CLI install failed, falling back to temporary CLI: %s", exc)
            return self._download_cli(session_root, progress_callback=progress_callback)

    def _discover_cli_url(self) -> str:
        html = self._request_text(self.DOWNLOAD_PAGE_URL)
        match = re.search(
            r'href="(?P<url>https://github\.com/ip7z/7zip/releases/download/[^"]+/7zr\.exe)"',
            html,
            re.IGNORECASE,
        )
        if not match:
            raise SevenZipServiceError("Could not find the official temporary 7-Zip CLI download URL.")
        download_url = match.group("url")
        if not download_url.startswith(self.OFFICIAL_DOWNLOAD_PREFIX):
            raise SevenZipServiceError("Refusing to download 7-Zip CLI from a non-official URL.")
        return download_url

    def _request_text(self, url: str) -> str:
        req = Request(url, headers={"User-Agent": "CrocDrop/1.0"})
        try:
            with urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise SevenZipServiceError(f"Failed to contact the official 7-Zip download page: {exc}") from exc

    def _request_bytes(self, url: str, progress_callback: ProgressCallback | None = None) -> bytes:
        req = Request(url, headers={"User-Agent": "CrocDrop/1.0"})
        try:
            with urlopen(req, timeout=60) as response:
                total = self._parse_content_length(response.headers.get("Content-Length"))
                downloaded = 0
                chunks: list[bytes] = []
                self._emit_progress(
                    progress_callback,
                    phase="sevenzip-download",
                    downloaded=0,
                    total=total,
                    percent=0.0 if total else None,
                    indeterminate=total is None,
                    message="Downloading 7-Zip CLI...",
                )
                while True:
                    chunk = response.read(self.DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / total * 100.0) if total else None
                    self._emit_progress(
                        progress_callback,
                        phase="sevenzip-download",
                        downloaded=downloaded,
                        total=total,
                        percent=percent,
                        indeterminate=total is None,
                        message="Downloading 7-Zip CLI...",
                    )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise SevenZipServiceError(f"Failed to download the temporary 7-Zip CLI: {exc}") from exc

        payload = b"".join(chunks)
        if not payload:
            raise SevenZipServiceError("Downloaded 7-Zip CLI was empty.")
        return payload

    def _download_to_file(self, url: str, target: Path, progress_callback: ProgressCallback | None = None) -> Path:
        tmp_target = target.with_name(f"{target.name}.tmp")
        tmp_target.parent.mkdir(parents=True, exist_ok=True)
        req = Request(url, headers={"User-Agent": "CrocDrop/1.0"})
        try:
            with urlopen(req, timeout=60) as response:
                total = self._parse_content_length(response.headers.get("Content-Length"))
                downloaded = 0
                self._emit_progress(
                    progress_callback,
                    phase="sevenzip-download",
                    downloaded=0,
                    total=total,
                    percent=0.0 if total else None,
                    indeterminate=total is None,
                    message="Downloading 7-Zip CLI...",
                )
                with tmp_target.open("wb") as handle:
                    while True:
                        chunk = response.read(self.DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        percent = (downloaded / total * 100.0) if total else None
                        self._emit_progress(
                            progress_callback,
                            phase="sevenzip-download",
                            downloaded=downloaded,
                            total=total,
                            percent=percent,
                            indeterminate=total is None,
                            message="Downloading 7-Zip CLI...",
                        )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            self._cleanup_partial_file(tmp_target)
            raise SevenZipServiceError(f"Failed to download the temporary 7-Zip CLI: {exc}") from exc
        except Exception:
            self._cleanup_partial_file(tmp_target)
            raise

        if not tmp_target.exists() or tmp_target.stat().st_size <= 0:
            self._cleanup_partial_file(tmp_target)
            raise SevenZipServiceError("Downloaded 7-Zip CLI was empty.")

        if target.name.lower() != self.MANAGED_BINARY_NAME.lower():
            self._cleanup_partial_file(tmp_target)
            raise SevenZipServiceError("Unexpected 7-Zip CLI target filename.")

        tmp_target.replace(target)
        return target

    def _build_archive_name(self, sources: list[Path]) -> str:
        if len(sources) == 1:
            return f"{sources[0].name}.7z"
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return f"crocdrop-bundle-{stamp}.7z"

    def _build_archive_members(self, sources: list[Path]) -> tuple[Path, list[str]]:
        if len(sources) == 1:
            source = sources[0]
            return source.parent, [source.name]

        try:
            common = Path(os.path.commonpath([str(path) for path in sources]))
        except ValueError as exc:
            raise SevenZipServiceError(
                "Compressed send currently requires all selected paths to be on the same drive."
            ) from exc

        work_dir = common if common.is_dir() else common.parent
        members = [os.path.relpath(str(path), str(work_dir)) for path in sources]
        return work_dir, members

    def _run(
        self,
        cmd: list[str],
        cwd: Path,
        action: str,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        phase = "compressing" if action == "compress" else "extracting"
        start_message = "Compressing files..." if action == "compress" else "Extracting archive..."
        self._emit_progress(
            progress_callback,
            phase=phase,
            percent=None,
            indeterminate=True,
            message=start_message,
        )
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise SevenZipServiceError(f"Failed to start temporary 7-Zip CLI for {action}: {exc}") from exc

        output_lines: list[str] = []
        last_percent: float | None = None
        if proc.stdout is not None:
            for line in self._iter_output_records(proc.stdout):
                output_lines.append(line)
                percent = self._parse_percent_from_output(line)
                if percent is not None:
                    last_percent = percent
                self._emit_progress(
                    progress_callback,
                    phase=phase,
                    percent=last_percent,
                    indeterminate=last_percent is None,
                    message=start_message,
                )
        proc.wait()

        if proc.returncode == 0:
            return

        detail = "\n".join(output_lines).strip()
        if detail:
            detail = detail.splitlines()[-1]
        else:
            detail = f"exit code {proc.returncode}"
        raise SevenZipServiceError(f"7-Zip could not {action} the transfer payload: {detail}")

    def ensure_managed_cli_async(self, enabled: bool = True) -> None:
        if not enabled:
            return
        if self.managed_binary_path().exists():
            return

        with self._background_install_lock:
            if self._background_install_thread is not None and self._background_install_thread.is_alive():
                return
            self._background_install_thread = threading.Thread(
                target=self._background_install_target,
                name="crocdrop-sevenzip-install",
                daemon=True,
            )
            self._background_install_thread.start()

    def _background_install_target(self) -> None:
        try:
            self.log.info("Background 7-Zip managed install check started.")
            self.install_cli()
            self.log.info("Background 7-Zip managed install completed.")
        except SevenZipServiceError as exc:
            self.log.warning("Background 7-Zip managed install failed: %s", exc)

    @staticmethod
    def _parse_content_length(raw_value: str | None) -> int | None:
        if not raw_value:
            return None
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _parse_percent_from_output(self, line: str) -> float | None:
        match = self._PERCENT_PATTERN.search(line)
        if not match:
            return None
        try:
            value = float(match.group("pct"))
        except ValueError:
            return None
        return max(0.0, min(100.0, value))

    @staticmethod
    def _iter_output_records(stream) -> Iterator[str]:
        buffer: list[str] = []
        while True:
            chunk = stream.read(1)
            if chunk == "":
                break
            if chunk in {"\r", "\n"}:
                text = "".join(buffer).strip()
                buffer.clear()
                if text:
                    yield text
                continue
            buffer.append(chunk)

        text = "".join(buffer).strip()
        if text:
            yield text

    @staticmethod
    def _cleanup_partial_file(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    @staticmethod
    def _emit_progress(
        progress_callback: ProgressCallback | None,
        *,
        phase: str,
        message: str,
        downloaded: int | None = None,
        total: int | None = None,
        percent: float | None = None,
        indeterminate: bool = False,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(
            {
                "phase": phase,
                "downloaded": downloaded,
                "total": total,
                "percent": percent,
                "indeterminate": indeterminate,
                "message": message,
            }
        )

    @staticmethod
    def _normalize_compression_level(level: int) -> int:
        return max(0, min(9, int(level)))
