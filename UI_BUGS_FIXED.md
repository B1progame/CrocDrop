# Main UI Bugs Found and Fixed

## 1) Sidebar Uses Only Top Portion (Wasted Lower Area)
- **Symptom:** sidebar nav looked cramped in the top region with empty space below.
- **Root cause:** `QVBoxLayout` placed nav with no stretch ownership and then added a trailing stretch item, so free height was consumed below nav.
- **Fix:** sidebar layout now assigns nav as the expanding owner (`addWidget(self.nav, 1)`) and removes the competing bottom stretch pattern.
- **Result:** nav fills available sidebar height; internal nav scrolling appears only when needed.

## 2) Inconsistent Header/Title Hierarchy
- **Symptom:** page titles and shell header looked disconnected and inconsistent.
- **Fix:** introduced reusable `PageHeader` and updated shell header semantics.
- **Result:** consistent typography and spacing across pages.

## 3) Light Mode Readability/Contrast Issues
- **Symptom:** several controls retained dark-oriented backgrounds in light mode.
- **Fix:** rebuilt theme with semantic dark/light palette tokens and control states.
- **Result:** intentional light mode with better readability and state contrast.

## 4) Settings Page Scaling/Clipping Risk
- **Symptom:** long settings content could feel cramped without robust container behavior.
- **Fix:** wrapped settings content in a `QScrollArea` with a dedicated content container.
- **Result:** stable behavior on smaller window heights.

## 5) UI Pattern Duplication Across Pages
- **Symptom:** repeated inline title styling and inconsistent page spacing.
- **Fix:** moved repeated title behavior into `PageHeader`; normalized page layout spacing.
- **Result:** cleaner, more maintainable UI code.

## 6) Transfer View Responsiveness Presentation
- **Symptom:** high-volume transfer logs made views noisy and harder to scan.
- **Fix:** maintained plain-text log approach with capped blocks and structured cards/progress bars.
- **Result:** better readability and reduced visual overload.
