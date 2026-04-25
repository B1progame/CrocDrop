# Settings Page Refinement Plan

## What is currently broken

- The redesigned Settings page still behaves like a long scrolling document instead of a true app settings panel.
- Section jump navigation scrolls to cards instead of switching real categories.
- Theme mode controls were reintroduced inside Settings, which duplicates the existing sidebar theme switcher.
- Some toggle controls feel visually unreliable and do not clearly communicate their checked state.
- Unlimited upload/download toggles are especially fragile because their visual state and enabled/disabled inputs can drift.
- A few indicator and arrow-style visuals add clutter without improving usability.
- The layout currently mixes too many unrelated controls on one long surface, which makes the page feel noisy.

## Which old functionality must stay

- Accent color selection and persistence via `settings.accent_color`
- Remember last folders
- Log retention days
- Default download folder browsing
- Ask before receiving
- Auto-open received folder
- Upload/download limit persistence in kbps with `0` meaning unlimited
- Relay mode and custom relay handling
- Croc binary path browse/delete behavior
- Auto-download croc
- Profile status, switch, removal, and guest mode controls
- Debug enable/disable behavior, including the existing password prompt
- Update button, worker thread, progress dialog, and result handling
- `save()`, `pick_folder()`, `pick_binary()`, `delete_binary()`
- `refresh_account_section()`
- `switch_profile()`, `remove_current_profile()`, `set_guest_mode()`
- `enable_debug_features()`, `disable_debug_features()`, `refresh_debug_controls()`
- `update_app()` and the update worker/dialog lifecycle
- Settings persistence through `settings_service`
- Existing theme support outside Settings, including `apply_theme()` and stored theme fields

## Which UI parts will be removed

- Section scroll-jump navigation
- Theme mode selector inside Settings
- Any dark/light/system selector inside Settings
- Any duplicate dark mode switch inside Settings
- Broken or unnecessary arrow/indicator visuals tied to the old long-page navigation
- Old card layout code that only exists to support the scroll-jump experience

## New underpage/category structure

- `General`
  - Accent color
  - Remember last folders
  - Log retention days
  - Accent preview
- `Transfers`
  - Default download folder
  - Ask before receiving
  - Auto-open received folder
- `Speed Limits`
  - Upload speed limit
  - Download speed limit
  - Unlimited upload toggle
  - Unlimited download toggle
- `Connection`
  - Relay mode
  - Custom relay
  - Croc binary status/path
  - Browse/delete binary
  - Auto-download croc
- `Profiles`
  - Current profile
  - Profile picker
  - Switch profile
  - Remove current profile
  - Guest mode
- `Advanced`
  - Debug status
  - Enable debug features
  - Disable debug features
- `Updates`
  - Current version
  - Update status
  - Update app action

## Testing checklist

- App starts without import errors
- Settings page opens successfully
- There is no theme mode control inside Settings
- Sidebar theme switcher still works
- Left-side category navigation is visible
- Switching categories updates the visible content instead of scrolling
- No scroll-jump navigation remains
- No broken arrow indicators remain
- Toggle switches show correct ON/OFF state after clicks and `setChecked()`
- Ask before receiving saves
- Auto-open received folder saves
- Remember last folders saves
- Auto-download croc saves
- Unlimited upload toggle disables/enables its input correctly
- Unlimited download toggle disables/enables its input correctly
- Upload limit persists as `round(Mbit/s * 125.0)` when not unlimited
- Download limit persists as `round(Mbit/s * 125.0)` when not unlimited
- Unlimited upload/download save `0`
- Accent color selection is obvious and saves correctly
- Default download folder browse works
- Relay mode saves and custom relay enables/disables correctly
- Croc binary browse works
- Delete croc binary works
- Profile switch works
- Remove current profile works
- Guest mode works
- Debug enable still prompts for the existing password
- Debug disable works
- Update app still uses the existing worker/dialog flow
- Global Save Settings saves values from every subpage
- Dark theme looks correct
- Light theme looks correct
