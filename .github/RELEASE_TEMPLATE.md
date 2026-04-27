# CrocDrop v1.3.1 - Cleaner Compressed Transfers + Startup Polish

## Highlights
- Compressed CrocDrop codes now use a compact embedded `z` marker instead of exposing temporary archive filenames.
- Managed 7-Zip CLI setup is smoother, reused across transfers, and shows visible download/compression/extraction progress.
- CrocDrop now keeps croc subprocesses hidden on Windows so send/receive stays GUI-only.

## What Changed
- Reworked compressed share-code parsing and generation while keeping old `::cd1:z7:<archive>.7z` codes compatible.
- Updated send output, copy behavior, and croc output handling so the CrocDrop share code stays the user-facing source of truth.
- Added safer receive-side archive detection for compressed transfers without relying on visible archive names.
- Added progress-aware 7-Zip download, compression, and extraction handling with percentage/ETA where 7-Zip reports it.
- Added managed 7-Zip background preinstall and installer cleanup for CrocDrop-managed tools.
- Added a Send page Clear button for resetting selected files, codes, progress, and output before starting a new upload.
- Improved startup splash sizing/logo rendering and tightened the splash-to-main-window transition.
- Suppressed visible Windows console windows when CrocDrop launches croc subprocesses.
- Bumped app and installer metadata to `1.3.1`.

## User Impact
- Compressed transfer codes are shorter, cleaner, and no longer reveal temporary archive filenames.
- Receivers can still paste old compressed codes, and new compressed receives still auto-extract when safe.
- Compressed sends feel less stuck because 7-Zip setup and preparation now report what is happening.
- Starting send/receive should no longer flash or leave behind CMD windows in the installed app.
- The Send page is easier to reuse for a new upload after a transfer finishes.

## Notes
- Each release should continue to include the Windows installer `.exe` asset for updater compatibility.
- Auto-extraction still only runs for marked compressed CrocDrop transfers and keeps the archive if extraction fails.
- The managed 7-Zip CLI is stored in CrocDrop's app-data tools folder and removed by uninstall cleanup when present.
