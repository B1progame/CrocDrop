# TODO

- Clarify friend detection: currently a "friend" is only a remembered alias from transfer code/session history, not verified identity.
- Add clearer friend trust flow: let user mark entries as "Trusted Friend" manually and show trust badge in Devices page.
- Add identity warning text in Devices page: "Code-based alias only, not cryptographic proof of person."
- Add auto update support (check GitHub releases, notify user, and in-app update flow).

## Better Friend System

- Add dedicated `Friends` page (separate from Devices) with search, filter, and sortable columns.
- Add friend model fields: `display_name`, `notes`, `last_seen`, `trust_level`, and optional avatar color.
- Add quick actions: `Trust`, `Untrust`, `Rename`, `Remove`, and `Copy friend code/session`.
- Add transfer-to-friend shortcut from Send page: select remembered friend and prefill target context.
- Show friend relationship status in Transfers history (`Unknown`, `Remembered`, `Trusted`).
- Add import/export for friend list JSON (local-only backup/restore).
- Add clearer privacy copy: friend entries are local app metadata, not cryptographic identity.

## Better Profile Page

- Redesign Profile page into grouped sections: `Identity`, `Local Device`, `Croc Backend`, `Quick Actions`.
- Allow editing local display name directly from Profile page (with save/cancel state).
- Add profile avatar/initial customization (local-only color + initials).
- Show useful runtime info: app version, croc source/version, platform, hostname.
- Add inline shortcuts to Settings Profile controls (switch guest mode / manage saved profiles).
- Add recent activity summary card (last transfer count + last transfer time).
- Add clear distinction text: profile is local to this installation, not cloud account.
- Improve keyboard accessibility and focus order for all profile actions.

## UI/UX Improvements

- Add full theme switcher: `Light`, `Dark`, and `System`.
- Auto-apply theme on OS change when `System` is selected.
- Improve light theme contrast (especially muted text, borders, and cards).
- Improve dark theme readability (less glow, better neutral grays, clearer input states).
- Add accent presets with preview chips and a custom color picker.
- Add a compact density mode for smaller spacing in lists/tables.
- Add accessible font scaling (Small / Medium / Large).

## Quality of Life

- Add first-run onboarding tooltip flow for Send/Receive.
- Add transfer speed + ETA in active transfers.
- Add optional sound notification on transfer complete/fail.
- Add "Open logs folder" button in Logs page.
- Add "Copy diagnostics" one-click button for support.

## Stability & Security

- Add update channel selector (Stable / Beta).
- Add release signature/hash verification step for app self-updates.
- Add rollback support if update apply fails.
- Add safer shutdown handling during active transfers.
