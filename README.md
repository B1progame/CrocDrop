# CrocDrop

CrocDrop is a Windows-first desktop GUI for the official [`schollz/croc`](https://github.com/schollz/croc) file transfer tool.

Author: `B1progame`

## What This Project Does

- Uses **only** croc as transfer backend.
- Provides a modern PySide6 GUI with pages for Home, Send, Receive, Transfers, Devices, Logs, Settings, Debug, and About.
- Detects existing croc binary or downloads official release assets from GitHub releases.
- Captures transfer output, stores history, and exposes logs/diagnostics.
- Includes local self-test flow (sender + receiver on same machine) and dual-instance launch helper.

## Architecture Summary

- `ui/`: desktop interface (sidebar shell + page modules)
- `services/`: backend logic and orchestration
  - `croc_manager.py`: official binary detection/download/version/process launch
  - `transfer_parser.py`: output parsing (isolated for version drift)
  - `transfer_service.py`: runtime process lifecycle + history updates
  - `debug_service.py`: self-test, dual-instance launch, diagnostics
  - `settings_service.py`, `history_service.py`, `log_service.py`
- `models/`: typed dataclasses (settings, transfer records, croc state)
- `storage/`: JSON persistence
- `utils/`: app dirs, hashing, platform mapping

## Croc Integration Model

CrocDrop shells out to the croc binary as a managed subprocess:

- Send: `croc [relay args] send <file(s)/folder(s)>`
- Receive: `croc [relay args] --yes [--overwrite] --out <destination> <code>`
- Version check: `croc --version`

Notes:
- Parser logic is best-effort and intentionally isolated in `services/transfer_parser.py` because CLI text output can vary across croc versions.
- Collision modes (`ask/rename/overwrite-disabled/skip`) are represented in UI; behavior depends on croc CLI prompts and flags in the installed version.

## Official Binary Source Rules

Auto-download path is pinned to official release channels:

- Metadata endpoint: `https://api.github.com/repos/schollz/croc/releases/latest`
- Asset URLs must start with: `https://github.com/schollz/croc/releases/download/`

If download fails or is disabled, users can select a manual croc binary path in Settings.

## Run (Dev)

1. Create venv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Start app:

```powershell
python main.py
```

3. Optional second debug instance:

```powershell
python main.py --debug-peer
```

Startup diagnostics are written to `%APPDATA%\CrocDrop\Logs\startup.log`. The log captures process context, bootstrap phases, main window show, and the deferred croc status check without interrupting the UI.

## Packaging (single app install target)

Example with PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean CrocDrop.spec
```

Distribute the generated `dist\CrocDrop` folder (or build an installer around it).

## Inno Setup Installer

This repo includes a ready Inno Setup script:

- `installer/CrocDrop.iss`

Manual flow:

1. Build `dist\CrocDrop` with PyInstaller.
2. Open `installer/CrocDrop.iss` in Inno Setup 6.
3. Build the installer.
4. Output is written to `installer_output\`.

Automated flow (PowerShell):

```powershell
.\installer\build_installer.ps1 -Version 1.3.0
```

## Publish Release (No Manual Asset Upload)

After building the installer, publish/update the GitHub release and upload the `.exe` asset automatically.

Prerequisite:
- Set `GITHUB_TOKEN` (PAT with `repo` scope).

PowerShell:

```powershell
.\installer\publish_release.ps1 -Version 1.3.0
```

Batch (uses version from `app/version.py` if omitted):

```bat
installer\publish_release.bat
```

## Key Safety Constraints in App

- No automatic firewall changes.
- No permanent background services.
- Failed/canceled transfers are never marked successful.
- Logs and diagnostics include exact croc binary path/version.
- Security guarantees are not overstated; app defers protocol claims to croc itself.

## Project Files

See full structure in `DEVELOPER_NOTES.md`.

## License

This project is licensed under the MIT License.
See [`LICENSE`](LICENSE) for terms (including no warranty / no liability clause).
