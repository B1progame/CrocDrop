# UI Changelog

## v1.3.1
- Fixed the startup flicker/open-close loop by stabilizing bootstrap flow around one splash window and one main window.
- Deferred croc detection until after the first UI paint so startup no longer blocks the shell.
- Added startup diagnostics logging for bootstrap phases, process context, main window show, and deferred croc checks.
- Added a compact startup window with status text while settings, services, and profile selection are prepared.
- Added single-instance protection for normal launches while keeping `--debug-peer` available for dual-instance testing.
- Compressed CrocDrop share codes now use a compact embedded `z` marker instead of exposing archive filenames.
- Old `::cd1:z7:<archive>.7z` compressed codes remain supported for backward-compatible receives.
- Receive auto-extract still runs only for marked compressed transfers, without requiring the archive filename in the visible code.
- Managed 7-Zip CLI is now auto-installed in the background when missing and reused for future compressed transfers.
- Compressed send now shows 7-Zip download, compression, and transfer startup progress without blocking the UI.
- Compressed receive now shows archive extraction progress and keeps the archive when extraction fails.
- Installer uninstall now removes the managed 7-Zip CLI from CrocDrop's app-data tools folder.

## v1.2.x
- Added optional 7-Zip send compression with automatic receive-side extraction.
- Added managed 7-Zip CLI install/uninstall controls in Settings > Connection.
- Added selectable 7-Zip compression strength presets.

## Main Shell
- Redesigned sidebar top block with cleaner branding composition and profile/mode badges.
- Replaced legacy nav icon look with dedicated SVG icon set.
- Added animated active nav indicator to improve selection clarity.
- Added stacked-page fade transition to reduce abrupt context switching.

## Sidebar Bug Fix
- Corrected sidebar layout ownership so navigation consumes available vertical space.
- Scroll now appears only when the nav item list exceeds available height.

## Theme Overhaul
- Upgraded dark theme accent treatment to a controlled purple?pink gradient family.
- Updated selected/hover states for navigation and primary actions.
- Enforced transparent label backgrounds to avoid visual artifact blocks.

## Settings Page
- Reworked settings rows with structured label + description column.
- Improved spacing, hierarchy, and readability.
- Updated accent color options to modern palette.

## Assets
- Added real SVG icons:
  - `assets/icons/nav_home.svg`
  - `assets/icons/nav_send.svg`
  - `assets/icons/nav_receive.svg`
  - `assets/icons/nav_transfers.svg`
  - `assets/icons/nav_devices.svg`
  - `assets/icons/nav_logs.svg`
  - `assets/icons/nav_settings.svg`
  - `assets/icons/nav_debug.svg`
  - `assets/icons/nav_about.svg`
