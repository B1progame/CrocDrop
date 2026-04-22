# PR: UI Modernization and Sidebar Layout Fix

## What Was Analyzed
- Full PySide6 UI architecture:
  - shell, sidebar, header, stacked pages
  - dialogs and shared components
  - style system and dark/light mode handling
- Layout behavior under resize and long-content conditions.

## Key Issues Found
- Sidebar nav was not using full vertical space due to layout stretch ownership.
- Theme semantics were inconsistent in light mode.
- Page title/spacing patterns were duplicated and uneven.
- Settings and several pages needed more robust structure for resize/scaling quality.

## What Changed
- Reworked app shell (`ui/main_window.py`) with:
  - corrected sidebar stretch behavior
  - cleaner header status treatment
  - standardized navigation visuals/icons
- Rebuilt theme system (`ui/theme.py`) with semantic palette roles for dark/light.
- Added reusable page header component (`ui/components/common.py`).
- Modernized page layouts and grouping across all major screens.
- Added audit and redesign documentation (`UI_AUDIT_REPORT.md`, `UI_REDESIGN_SUMMARY.md`, `UI_BUGS_FIXED.md`).

## Sidebar Bug: Exact Cause and Fix
- Cause: a trailing `addStretch(1)` consumed free height under nav while nav itself had no expansion ownership.
- Fix: assign nav stretch ownership (`addWidget(nav, 1)`) and remove competing bottom spacer usage.
- Outcome: nav uses full available sidebar height; scrolling is only needed when item count exceeds visible area.

## Risks / Notes
- UI styling changed broadly but only in UI layers.
- Core transfer/business logic intentionally preserved.
- Uses Qt standard icons (no external runtime icon dependency added).

## Validation
- `python -m compileall main.py app ui services models utils` passed.
