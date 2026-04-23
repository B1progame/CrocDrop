from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.version import APP_NAME, APP_REPOSITORY, APP_VERSION
from utils.paths import app_cache_dir


class UpdateServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    kind: str


@dataclass(slots=True)
class ReleaseInfo:
    tag_name: str
    name: str
    published_at: str
    asset: ReleaseAsset


@dataclass(slots=True)
class UpdateResult:
    status: str
    current_version: str
    latest_version: str
    message: str
    archive_path: str = ""


class UpdateService:
    RELEASE_API = f"https://api.github.com/repos/{APP_REPOSITORY}/releases/latest"
    RELEASE_PREFIX = f"https://github.com/{APP_REPOSITORY}/releases/download/"

    def __init__(self, log_service):
        self.log = log_service.get_logger("updater")

    def current_version(self) -> str:
        return APP_VERSION

    def _request_json(self, url: str) -> dict:
        req = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        with urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _normalize_version(self, value: str) -> tuple[int, ...]:
        numbers = [int(n) for n in re.findall(r"\d+", value or "")]
        return tuple(numbers[:4]) if numbers else tuple()

    def _is_newer(self, latest: str, current: str) -> bool:
        latest_v = self._normalize_version(latest)
        current_v = self._normalize_version(current)
        if latest_v and current_v:
            return latest_v > current_v
        return latest.strip().lower() != current.strip().lower()

    def _select_asset(self, assets: list[dict]) -> ReleaseAsset:
        installer_candidates: list[ReleaseAsset] = []
        zip_candidates: list[ReleaseAsset] = []
        for raw in assets:
            name = str(raw.get("name", "")).strip()
            url = str(raw.get("browser_download_url", "")).strip()
            size = int(raw.get("size", 0) or 0)
            if not url.startswith(self.RELEASE_PREFIX):
                continue
            lower_name = name.lower()
            if lower_name.endswith(".exe"):
                installer_candidates.append(ReleaseAsset(name=name, url=url, size=size, kind="installer"))
            elif lower_name.endswith(".zip"):
                zip_candidates.append(ReleaseAsset(name=name, url=url, size=size, kind="zip"))

        preferred_keywords = ("crocdrop", "setup", "installer", "windows", "win", "x64", "amd64")

        def _best(candidates: list[ReleaseAsset]) -> ReleaseAsset:
            scored = sorted(
                candidates,
                key=lambda c: sum(1 for kw in preferred_keywords if kw in c.name.lower()),
                reverse=True,
            )
            return scored[0]

        if installer_candidates:
            return _best(installer_candidates)
        if zip_candidates:
            return _best(zip_candidates)

        raise UpdateServiceError("No update installer (.exe) or ZIP asset was found in the latest GitHub release.")

    def get_latest_release(self) -> ReleaseInfo:
        try:
            payload = self._request_json(self.RELEASE_API)
        except HTTPError as exc:
            raise UpdateServiceError(f"GitHub API returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise UpdateServiceError(f"Could not connect to GitHub: {exc.reason}") from exc

        tag_name = str(payload.get("tag_name", "")).strip()
        if not tag_name:
            raise UpdateServiceError("GitHub release metadata is missing tag_name.")
        asset = self._select_asset(payload.get("assets", []))
        return ReleaseInfo(
            tag_name=tag_name,
            name=str(payload.get("name", "")).strip(),
            published_at=str(payload.get("published_at", "")).strip(),
            asset=asset,
        )

    def check_for_update(self) -> UpdateResult:
        current = self.current_version()
        release = self.get_latest_release()
        if not self._is_newer(release.tag_name, current):
            return UpdateResult(
                status="up-to-date",
                current_version=current,
                latest_version=release.tag_name,
                message=f"You are already on the latest version ({current}).",
            )
        return UpdateResult(
            status="update-available",
            current_version=current,
            latest_version=release.tag_name,
            message=f"Update available: {current} -> {release.tag_name}",
        )

    def download_release(self, release: ReleaseInfo, progress_callback=None, status_callback=None) -> Path:
        updates_dir = app_cache_dir() / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        safe_tag = re.sub(r"[^a-zA-Z0-9._-]+", "_", release.tag_name)
        package_path = updates_dir / f"{safe_tag}-{release.asset.name}"

        if status_callback:
            status_callback(f"Downloading {release.asset.name} ...")

        req = Request(release.asset.url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        try:
            with urlopen(req, timeout=60) as response, package_path.open("wb") as out:
                total = int(response.headers.get("Content-Length", "0") or 0)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)
        except HTTPError as exc:
            raise UpdateServiceError(f"Download failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise UpdateServiceError(f"Download failed: {exc.reason}") from exc

        if progress_callback:
            final_size = package_path.stat().st_size if package_path.exists() else 0
            progress_callback(final_size, final_size)
        return package_path

    def download_latest_update(self, progress_callback=None, status_callback=None) -> UpdateResult:
        if status_callback:
            status_callback("Checking GitHub releases ...")
        release = self.get_latest_release()
        current = self.current_version()
        if not self._is_newer(release.tag_name, current):
            return UpdateResult(
                status="up-to-date",
                current_version=current,
                latest_version=release.tag_name,
                message=f"You are already on the latest version ({current}).",
            )

        package_path = self.download_release(release, progress_callback=progress_callback, status_callback=status_callback)
        package_kind = "installer" if release.asset.kind == "installer" else "archive"
        return UpdateResult(
            status="downloaded",
            current_version=current,
            latest_version=release.tag_name,
            message=f"Downloaded {package_kind} for update {release.tag_name}.",
            archive_path=str(package_path),
        )

    def _resolve_runtime_paths(self) -> tuple[Path, str, str]:
        if getattr(sys, "frozen", False):
            exe_path = Path(sys.executable).resolve()
            app_dir = exe_path.parent
            return app_dir, str(exe_path), "[]"

        repo_root = Path(__file__).resolve().parents[1]
        restart_exe = str(Path(sys.executable).resolve())
        restart_args = json.dumps([str(repo_root / "main.py")])
        return repo_root, restart_exe, restart_args

    def _assert_install_writable(self, app_dir: Path) -> None:
        marker = app_dir / ".crocdrop_write_test.tmp"
        try:
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
        except Exception as exc:
            raise UpdateServiceError(f"Install directory is not writable: {app_dir}") from exc

    def _build_zip_updater_script(self, script_path: Path) -> None:
        script = r"""
param(
    [Parameter(Mandatory = $true)][string]$ArchivePath,
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$RestartExe,
    [Parameter(Mandatory = $false)][string]$RestartArgsJson = "[]",
    [Parameter(Mandatory = $true)][int]$SourcePid
)

$ErrorActionPreference = "Stop"

Start-Sleep -Milliseconds 600
try {
    Wait-Process -Id $SourcePid -Timeout 90 -ErrorAction Stop
} catch {
}
Start-Sleep -Milliseconds 800

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("CrocDropUpdate-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
Expand-Archive -Path $ArchivePath -DestinationPath $tempRoot -Force

$entries = @(Get-ChildItem -LiteralPath $tempRoot)
if ($entries.Count -eq 1 -and $entries[0].PSIsContainer) {
    $payloadRoot = $entries[0].FullName
} else {
    $payloadRoot = $tempRoot
}

Copy-Item -Path (Join-Path $payloadRoot "*") -Destination $AppDir -Recurse -Force
Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue

$restartArgs = @()
if ($RestartArgsJson) {
    try {
        $parsed = ConvertFrom-Json -InputObject $RestartArgsJson
        if ($parsed -is [System.Array]) {
            $restartArgs = @($parsed)
        } elseif ($parsed) {
            $restartArgs = @($parsed.ToString())
        }
    } catch {
    }
}

if ($restartArgs.Count -gt 0) {
    Start-Process -FilePath $RestartExe -WorkingDirectory $AppDir -ArgumentList $restartArgs | Out-Null
} else {
    Start-Process -FilePath $RestartExe -WorkingDirectory $AppDir | Out-Null
}
"""
        script_path.write_text(script.strip() + "\n", encoding="utf-8")

    def _build_installer_updater_script(self, script_path: Path) -> None:
        script = r"""
param(
    [Parameter(Mandatory = $true)][string]$InstallerPath,
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$RestartExe,
    [Parameter(Mandatory = $false)][string]$RestartArgsJson = "[]",
    [Parameter(Mandatory = $true)][int]$SourcePid
)

$ErrorActionPreference = "Stop"

Start-Sleep -Milliseconds 600
try {
    Wait-Process -Id $SourcePid -Timeout 120 -ErrorAction Stop
} catch {
}
Start-Sleep -Milliseconds 800

$installerArgs = @(
    "/SP-",
    "/VERYSILENT",
    "/SUPPRESSMSGBOXES",
    "/NORESTART",
    "/CLOSEAPPLICATIONS",
    "/FORCECLOSEAPPLICATIONS"
)
$proc = Start-Process -FilePath $InstallerPath -ArgumentList $installerArgs -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    exit $proc.ExitCode
}
Remove-Item -LiteralPath $InstallerPath -Force -ErrorAction SilentlyContinue

$restartArgs = @()
if ($RestartArgsJson) {
    try {
        $parsed = ConvertFrom-Json -InputObject $RestartArgsJson
        if ($parsed -is [System.Array]) {
            $restartArgs = @($parsed)
        } elseif ($parsed) {
            $restartArgs = @($parsed.ToString())
        }
    } catch {
    }
}

if ($restartArgs.Count -gt 0) {
    Start-Process -FilePath $RestartExe -WorkingDirectory $AppDir -ArgumentList $restartArgs | Out-Null
} else {
    Start-Process -FilePath $RestartExe -WorkingDirectory $AppDir | Out-Null
}
"""
        script_path.write_text(script.strip() + "\n", encoding="utf-8")

    def apply_update_and_restart(self, archive_path: str) -> None:
        package_path = Path(archive_path).expanduser().resolve()
        if not package_path.exists():
            raise UpdateServiceError("Downloaded update package was not found.")

        app_dir, restart_exe, restart_args_json = self._resolve_runtime_paths()

        updates_dir = app_cache_dir() / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        lower_name = package_path.name.lower()
        if lower_name.endswith(".exe"):
            script_path = updates_dir / "apply_installer_update.ps1"
            self._build_installer_updater_script(script_path)
        elif lower_name.endswith(".zip"):
            # ZIP in-place replacement needs write access to the install folder.
            self._assert_install_writable(app_dir)
            script_path = updates_dir / "apply_zip_update.ps1"
            self._build_zip_updater_script(script_path)
        else:
            raise UpdateServiceError("Unsupported update package type. Expected .exe or .zip.")

        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-ArchivePath" if lower_name.endswith(".zip") else "-InstallerPath",
            str(package_path),
            "-AppDir",
            str(app_dir),
            "-RestartExe",
            restart_exe,
            "-RestartArgsJson",
            restart_args_json,
            "-SourcePid",
            str(os.getpid()),
        ]
        self.log.info("Launching updater script for package %s", package_path)
        subprocess.Popen(cmd, creationflags=creationflags)
