from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from models.croc import CrocBinaryInfo
from services.settings_service import SettingsService
from utils.hashing import sha256_of_file
from utils.paths import croc_runtime_dir, tools_dir
from utils.platforming import platform_key, select_windows_asset_token


class CrocManagerError(RuntimeError):
    pass


class CrocManager:
    RELEASE_API = "https://api.github.com/repos/schollz/croc/releases/latest"
    RELEASE_PREFIX = "https://github.com/schollz/croc/releases/download/"

    def __init__(self, log_service, settings_service: SettingsService):
        self.log = log_service.get_logger("croc")
        self.settings_service = settings_service
        self._cached_info: CrocBinaryInfo | None = None
        self._cached_detect_signature: tuple[str, str, str] | None = None
        self._cached_flag_support: dict[str, set[str]] = {}

    def _request_json(self, url: str) -> dict:
        req = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "CrocDrop/1.0"})
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _request_bytes(self, url: str) -> bytes:
        req = Request(url, headers={"User-Agent": "CrocDrop/1.0"})
        with urlopen(req, timeout=60) as response:
            return response.read()

    def detect_binary(self) -> CrocBinaryInfo:
        settings = self.settings_service.get()
        bundled = tools_dir() / "croc" / "croc.exe"
        exe = shutil.which("croc")
        signature = (settings.croc_binary_path, str(bundled), exe or "")

        if self._cached_info is not None and self._cached_detect_signature == signature:
            if self._cached_info.source == "not-found":
                return self._cached_info
            if self._cached_info.path and Path(self._cached_info.path).exists():
                return self._cached_info

        candidates: list[tuple[str, Path]] = []

        if settings.croc_binary_path:
            candidates.append(("manual", Path(settings.croc_binary_path)))

        candidates.append(("downloaded", bundled))

        if exe:
            candidates.append(("system", Path(exe)))

        for source, path in candidates:
            if path.exists():
                version = self.get_version(path)
                info = CrocBinaryInfo(path=str(path), version=version, source=source)
                self._cached_info = info
                self._cached_detect_signature = signature
                return info

        info = CrocBinaryInfo(path="", version="", source="not-found", notes="No croc binary detected")
        self._cached_info = info
        self._cached_detect_signature = signature
        return info

    def ensure_binary(self, auto_download: bool = True) -> CrocBinaryInfo:
        info = self.detect_binary()
        if info.source != "not-found":
            return info
        if not auto_download:
            raise CrocManagerError("croc binary missing and auto-download disabled")
        return self.download_official_release()

    def download_official_release(self) -> CrocBinaryInfo:
        system, machine = platform_key()
        if system != "windows":
            raise CrocManagerError(f"Current implementation targets Windows first, got {system}/{machine}")

        self.log.info("Fetching latest official release metadata from GitHub")
        metadata = self._request_json(self.RELEASE_API)
        tag_name = metadata.get("tag_name", "")
        assets = metadata.get("assets", [])

        release_html = metadata.get("html_url", "")
        if not release_html.startswith("https://github.com/schollz/croc/releases/"):
            raise CrocManagerError("Release metadata did not point to official schollz/croc release URL")

        token = select_windows_asset_token(machine)
        asset = next((a for a in assets if token in a.get("name", "") and a.get("name", "").endswith((".zip", ".tar.gz"))), None)
        checksum_asset = next((a for a in assets if "checksums" in a.get("name", "").lower()), None)

        if not asset:
            raise CrocManagerError(f"No matching Windows asset found for token {token}")

        download_url = asset.get("browser_download_url", "")
        if not download_url.startswith(self.RELEASE_PREFIX):
            raise CrocManagerError("Refusing to download from non-official release URL")

        asset_name = asset.get("name", "")
        self.log.info("Downloading croc asset: %s", asset_name)
        payload = self._request_bytes(download_url)

        tools_root = tools_dir() / "downloads"
        tools_root.mkdir(parents=True, exist_ok=True)
        archive_path = tools_root / asset_name
        archive_path.write_bytes(payload)

        checksum_map: dict[str, str] = {}
        if checksum_asset:
            checksum_url = checksum_asset.get("browser_download_url", "")
            if checksum_url.startswith(self.RELEASE_PREFIX):
                text = self._request_bytes(checksum_url).decode("utf-8", errors="ignore")
                checksum_map = self._parse_checksums(text)

        local_sha = sha256_of_file(archive_path)
        expected_sha = checksum_map.get(asset_name, "")
        verified = bool(expected_sha and expected_sha.lower() == local_sha.lower())

        target_dir = tools_dir() / "croc"
        target_dir.mkdir(parents=True, exist_ok=True)
        binary_path = self._extract_binary(archive_path, target_dir)

        self.settings_service.set_manual_binary_path(binary_path)
        version = self.get_version(binary_path)

        info = CrocBinaryInfo(
            path=str(binary_path),
            version=version,
            source="downloaded",
            release_tag=tag_name,
            asset_name=asset_name,
            sha256=local_sha,
            verified_checksum=verified,
            notes="Checksum not published for selected asset" if not expected_sha else "",
        )
        self._cached_info = info
        self._cached_detect_signature = None
        self.log.info("croc installed at %s version=%s", binary_path, version)
        return info

    def _parse_checksums(self, text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or "sha256:" in line.lower():
                continue
            parts = line.split()
            if len(parts) >= 2:
                checksum = parts[0].strip()
                name = parts[-1].strip().lstrip("*")
                if len(checksum) >= 32:
                    result[name] = checksum
        return result

    def _extract_binary(self, archive_path: Path, target_dir: Path) -> Path:
        binary_name = "croc.exe"
        out_path = target_dir / binary_name

        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                member = next((n for n in zf.namelist() if n.lower().endswith("croc.exe")), None)
                if not member:
                    raise CrocManagerError("Downloaded archive does not contain croc.exe")
                with zf.open(member) as src, out_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                return out_path

        if archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tf:
                member = next((m for m in tf.getmembers() if m.name.lower().endswith("croc.exe")), None)
                if not member:
                    member = next((m for m in tf.getmembers() if m.name.lower().endswith("/croc")), None)
                if not member:
                    raise CrocManagerError("Downloaded archive does not contain croc binary")
                fobj = tf.extractfile(member)
                if not fobj:
                    raise CrocManagerError("Failed to extract croc binary from archive")
                out_name = "croc.exe" if member.name.lower().endswith(".exe") else "croc"
                out_path = target_dir / out_name
                with out_path.open("wb") as dst:
                    dst.write(fobj.read())
                return out_path

        raise CrocManagerError(f"Unsupported archive format: {archive_path.name}")

    def get_version(self, binary_path: Path | None = None) -> str:
        if binary_path is None:
            info = self.detect_binary()
            if not info.path:
                return ""
            binary_path = Path(info.path)
        try:
            proc = subprocess.run([str(binary_path), "--version"], capture_output=True, text=True, timeout=10)
            out = (proc.stdout or proc.stderr).strip().splitlines()
            return out[0] if out else "unknown"
        except Exception as exc:
            self.log.warning("Unable to query croc version: %s", exc)
            return "unknown"

    def build_relay_args(self) -> list[str]:
        settings = self.settings_service.get()
        if settings.relay_mode == "custom" and settings.custom_relay.strip():
            return ["--relay", settings.custom_relay.strip()]
        return []

    def _supported_global_flags(self, binary_path: Path) -> set[str]:
        key = str(binary_path)
        cached = self._cached_flag_support.get(key)
        if cached is not None:
            return cached

        try:
            proc = subprocess.run([str(binary_path), "--help"], capture_output=True, text=True, timeout=10)
            help_text = f"{proc.stdout}\n{proc.stderr}"
        except Exception as exc:
            self.log.warning("Unable to detect croc flag support: %s", exc)
            self._cached_flag_support[key] = set()
            return set()

        flags = set(re.findall(r"--([A-Za-z][A-Za-z0-9-]*)", help_text))
        self._cached_flag_support[key] = flags
        return flags

    def _build_speed_limit_args(self, binary_path: Path, direction: str) -> list[str]:
        settings = self.settings_service.get()
        supported = self._supported_global_flags(binary_path)
        args: list[str] = []

        if direction == "send" and settings.upload_limit_kbps > 0:
            if "throttleUpload" in supported:
                args.extend(["--throttleUpload", f"{settings.upload_limit_kbps}k"])
            else:
                self.log.warning("Upload limiter set but this croc build does not support --throttleUpload")

        if direction == "receive" and settings.download_limit_kbps > 0:
            if "throttleDownload" in supported:
                args.extend(["--throttleDownload", f"{settings.download_limit_kbps}k"])
            else:
                self.log.warning("Download limiter set but this croc build does not support --throttleDownload")

        return args

    def launch_send(self, paths: list[str], code_phrase: str = "") -> subprocess.Popen:
        info = self.ensure_binary(auto_download=self.settings_service.get().auto_download_croc)
        cmd = [
            info.path,
            *self.build_relay_args(),
            *self._build_speed_limit_args(Path(info.path), "send"),
            "--ignore-stdin",
            "--no-compress",
            "send",
            "--hash",
            "md5",
        ]
        if code_phrase.strip():
            cmd.extend(["--code", code_phrase.strip()])
        cmd.extend(paths)
        runtime_cwd = croc_runtime_dir()
        self.log.info("Starting send process: %s | cwd=%s", cmd, runtime_cwd)
        return subprocess.Popen(
            cmd,
            cwd=str(runtime_cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def launch_receive(self, code_phrase: str, destination: str, overwrite: bool) -> subprocess.Popen:
        info = self.ensure_binary(auto_download=self.settings_service.get().auto_download_croc)
        cmd = [
            info.path,
            *self.build_relay_args(),
            *self._build_speed_limit_args(Path(info.path), "receive"),
            "--yes",
            "--ignore-stdin",
            "--no-compress",
        ]
        if overwrite:
            cmd.append("--overwrite")
        cmd.extend(["--out", destination, code_phrase])
        runtime_cwd = croc_runtime_dir()
        self.log.info("Starting receive process: %s | cwd=%s", cmd, runtime_cwd)
        return subprocess.Popen(
            cmd,
            cwd=str(runtime_cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def diagnostics(self) -> dict:
        info = self.detect_binary()
        return info.to_dict()

    def delete_binary(self, requested_path: str | None = None) -> tuple[bool, str]:
        target: Path | None = None
        if requested_path and requested_path.strip():
            target = Path(requested_path.strip())
        else:
            info = self.detect_binary()
            if info.path:
                target = Path(info.path)

        if target is None:
            return False, "No croc binary path was provided."
        if not target.exists():
            return False, f"Binary not found: {target}"
        if not target.is_file():
            return False, f"Target is not a file: {target}"

        try:
            target.unlink()
        except PermissionError:
            return False, f"Permission denied deleting: {target}"
        except OSError as exc:
            return False, f"Failed to delete binary: {exc}"

        settings = self.settings_service.get()
        if settings.croc_binary_path and Path(settings.croc_binary_path) == target:
            settings.croc_binary_path = ""
            self.settings_service.save(settings)

        downloaded_dir = tools_dir() / "croc"
        if target.parent == downloaded_dir:
            try:
                if not any(downloaded_dir.iterdir()):
                    downloaded_dir.rmdir()
            except OSError:
                pass

        self._cached_info = None
        self._cached_detect_signature = None
        self.log.info("Deleted croc binary at %s", target)
        return True, f"Deleted croc binary: {target}"
