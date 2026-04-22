# UI Audit (CrocDrop)

## Scope Audited
- Main shell, sidebar, header, stacked pages
- Settings page layout and form structure
- Theme/style architecture
- Navigation behavior and resize behavior
- Icon strategy and consistency

## Major Problems Found
- Sidebar vertical space was previously underused due to layout stretch misuse, causing nav controls to stay cramped at top while lower area was visually wasted.
- Sidebar used inconsistent iconography quality; visual language did not feel product-grade.
- Settings form rows had weak hierarchy and readability, making labels/controls feel misaligned.
- Navigation transitions were abrupt with no visual continuity.
- Accent system was inconsistent with requested premium dark direction.

## Sidebar Root Cause and Exact Fix
- Root cause: the sidebar layout used a bottom stretch competing with navigation sizing, so the nav container did not own available height.
- Structural fix: give the nav widget the layout stretch (`addWidget(self.nav, 1)`) and remove competing bottom stretch.
- Behavioral fix: keep nav scroll enabled only when required, and let the list naturally consume full vertical space.
- UX fix: add animated active indicator (`QFrame#NavIndicator`) tracking current item geometry for clear focus and better wayfinding.

## Technical Weak Spots
- Over-reliance on direct row labeling without semantic descriptions in Settings.
- Theme semantics existed but needed stronger accent consistency and selected-state behavior.
- No cross-page transition motion.

## Risk Notes
- Any parser/output assumptions from croc are version-sensitive; parser remains isolated in `services/transfer_parser.py`.
- Icon assets now depend on local `assets/icons/*.svg`; missing assets fall back gracefully to blank icon.
