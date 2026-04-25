# Bug Fix Notes

## Manage Profile Routing Bug

- **Date logged:** 2026-04-25
- **Area:** `Profile -> Manage Profile`
- **Status:** Still reported / needs verification in the live app

### Symptom

When the user opens the `Profile` page and clicks `Manage Profile`, the sidebar selector can move to the `Settings` footer button, but the real Settings route is not always completed correctly.

### Observed failure modes

- The sidebar selector moves visually, but the main `QStackedWidget` may not fully switch to the real `Settings` page.
- The `Settings` page can remain on `General` instead of opening `Profiles`.
- The `Profiles` category button/highlight may fail to move even when the footer selector moves.
- The normal nav state can become inconsistent, which makes the transition look partially applied.

### Expected behavior

- Open the real `Settings` page in the main page stack.
- Keep the sidebar selector animation intact.
- Mark the `Settings` footer button as active.
- Clear the normal nav selection so `Home` is not active.
- Open the `Profiles` category directly.
- Move the Settings category selector/highlight to `Profiles`.

### Suspected root cause

The bug appears to be a routing/state-sync issue rather than a styling or animation issue. The footer selector transition can succeed visually while the Settings content/category state is not fully re-applied.

### Important constraints

- Do not redesign the sidebar.
- Do not redesign the Settings UI.
- Do not remove or change the existing sidebar selector animation.
- Fix the real routing/state behavior, not just the visual selector movement.
