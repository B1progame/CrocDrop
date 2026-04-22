# DEVELOPER_NOTES

## Full Project Tree

```text
.
├─ main.py
├─ requirements.txt
├─ README.md
├─ LICENSE
├─ TRUST_AND_SECURITY.md
├─ DEVELOPER_NOTES.md
├─ installer/
│  ├─ CrocDrop.iss
│  └─ build_installer.ps1
├─ app/
│  ├─ __init__.py
│  └─ bootstrap.py
├─ models/
│  ├─ __init__.py
│  ├─ croc.py
│  ├─ settings.py
│  └─ transfer.py
├─ services/
│  ├─ __init__.py
│  ├─ croc_manager.py
│  ├─ debug_service.py
│  ├─ history_service.py
│  ├─ log_service.py
│  ├─ settings_service.py
│  ├─ transfer_parser.py
│  └─ transfer_service.py
├─ storage/
│  ├─ __init__.py
│  └─ json_store.py
├─ ui/
│  ├─ __init__.py
│  ├─ main_window.py
│  ├─ theme.py
│  ├─ components/
│  │  └─ common.py
│  └─ pages/
│     ├─ __init__.py
│     ├─ about_page.py
│     ├─ debug_page.py
│     ├─ devices_page.py
│     ├─ home_page.py
│     ├─ logs_page.py
│     ├─ receive_page.py
│     ├─ send_page.py
│     ├─ settings_page.py
│     └─ transfers_page.py
└─ utils/
   ├─ __init__.py
   ├─ hashing.py
   ├─ paths.py
   └─ platforming.py
```

## Notes on Croc Output Parsing

- The parser (`services/transfer_parser.py`) is intentionally isolated.
- Current extraction covers:
  - code phrase lines (`Code is: ...` and fallback regex)
  - percent progress from lines containing `%`
  - speed tokens (e.g. `MB/s`)
  - coarse completion/error keyword detection
- Exact output can change with croc version. Update this module first if parse behavior drifts.

## Self-Test Strategy

`DebugService.run_self_test()`:
1. Creates temp send/receive directories.
2. Generates binary dummy payload.
3. Starts local sender transfer (`selftest-send`).
4. Captures emitted code phrase from transfer history updates.
5. Starts local receiver transfer (`selftest-receive`) on same machine.
6. Compares SHA-256 hashes and reports PASS/FAIL.

## Dual-Instance Helper

- `DebugService.launch_second_instance()` starts:
  - `python <repo>/main.py --debug-peer`
- Useful for local manual send/receive verification with separate windows.

## Persistence

Uses JSON stores in platform user data dirs (`platformdirs`):
- `settings.json`
- `history.json`
- log files in app log directory
- downloaded tools in app data `tools/`

## Known V1 Constraints

- Windows-first asset selection is implemented directly.
- Receive collision strategy beyond croc native prompt/overwrite behavior is best-effort.
- Progress details are parsed from output text (not protocol-level API), so future croc text changes may require regex updates.

## Windows Installer

- Inno Setup script: `installer/CrocDrop.iss`
- Build helper: `installer/build_installer.ps1`
- Installer includes MIT `LICENSE` page and publisher metadata (`B1progame`).
