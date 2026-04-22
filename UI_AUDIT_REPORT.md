# CrocDrop UI Audit Report

## Scope Reviewed
- App shell: `main.py`, `app/bootstrap.py`, `ui/main_window.py`, `ui/theme.py`
- Shared UI components: `ui/components/common.py`, `ui/components/toast_popup.py`
- All page modules under `ui/pages/`

## Architecture Findings
- A centralized shell exists (`MainWindow`) with sidebar + header + stacked pages.
- Styling was centralized in one stylesheet file, but semantics were mixed:
  - light mode still used dark-oriented field surfaces in many controls
  - repeated inline title styles existed across pages
- Page structure varied heavily (inconsistent margins, spacing, and control grouping).

## Major UI/UX Problems Found
- Sidebar vertical space bug:
  - nav region did not own available height due to a bottom stretch spacer
  - produced cramped top-half nav and wasted lower area
- Header/title inconsistency:
  - shell header and page headers used mixed patterns
  - many pages used one-off title styling
- Light mode quality:
  - input/table/list colors and borders were not consistently light-friendly
- Layout consistency issues:
  - mixed card spacing and control grouping patterns
  - settings page could become cramped without robust scroll containment
- Performance/UI pressure:
  - log-heavy views required high-frequency updates and needed better presentation patterns

## Research Notes
The redesign direction used patterns informed by:
- Fluent 2 layout guidance (spacing/proximity/hierarchy)
  - https://fluent2.microsoft.design/layout
- Apple HIG color guidance (semantic contrast and adaptive appearance)
  - https://developer.apple.com/design/human-interface-guidelines/color
- Qt layout and stretch behavior docs
  - https://doc.qt.io/qt-6/qboxlayout.html
- Qt scroll behavior docs
  - https://doc.qt.io/qt-6/qscrollarea.html
- Qt plain-text performance guidance for log-like views
  - https://doc.qt.io/qtforpython-6.5/PySide6/QtWidgets/QPlainTextEdit.html
- Product inspiration references (non-cloned adaptation):
  - Notion spacing/rhythm consistency notes
  - https://www.notion.com/blog/updating-the-design-of-notion-pages
  - Slack dark mode accessibility motivation
  - https://slack.com/help/articles/360019434914-Use-dark-mode-in-Slack

## Risk Notes
- Styling changes are broad but restricted to UI layers.
- Business logic for transfer operations was preserved.
- Nav icon set uses Qt standard icons for consistency and low dependency risk.
