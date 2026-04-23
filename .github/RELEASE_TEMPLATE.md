# CrocDrop v1.1.1 - Silent Installer Updates + Release Upload Automation

## Highlights
- In-app updater now supports **installer `.exe` assets** and runs upgrades silently (no click-through wizard).
- Added automated GitHub release upload scripts to publish the newest installer asset without manual drag-and-drop.
- Synced version defaults and metadata to `1.1.1` across app and installer tooling.

## What Changed
- Updater asset selection now prefers `.exe` installer assets, with `.zip` fallback.
- Silent installer update flow added using Inno Setup silent flags.
- Added `installer/publish_release.ps1` and `installer/publish_release.bat`.
- Updated build/publish fallbacks and docs to current version.

## User Impact
- Users can update from Settings without going through installer UI.
- Releases can be published with the correct installer asset in one command.
- Better consistency between tags, installer filenames, and in-app version checks.

## Notes
- For updater compatibility, each release should include a Windows installer `.exe` asset.
- If installed in a protected location, Windows may still require elevation during update apply.
