# Settings Page Premium Redesign

## Current problems of the Settings page

- The page is spread across many generic form blocks with weak visual hierarchy.
- Important status information is buried inside labels instead of surfaced clearly.
- Theme mode is not exposed inside the page, even though it is part of persisted settings.
- The layout feels text-heavy and plain, with too much helper copy visible at once.
- Buttons do not communicate priority well enough between save, update, destructive, and neutral actions.
- Related controls are split across multiple cards without a stronger "control center" feel.
- The current UI relies on standard combo boxes and checkboxes where richer, clearer controls would fit better.
- The update dialog works functionally, but it does not visually match a premium settings experience.

## All settings/actions that must be preserved

### Settings

- `default_download_folder`
- `ask_before_receiving`
- `auto_open_received_folder`
- `remember_last_folders`
- `theme_mode`
- `accent_color`
- `relay_mode`
- `custom_relay`
- `croc_binary_path`
- `log_retention_days`
- `auto_download_croc`
- `upload_limit_kbps`
- `download_limit_kbps`
- `current_profile`
- `debug_mode`

### Actions

- Browse default download folder
- Browse croc binary
- Delete croc binary via `context.croc_manager.delete_binary()`
- Switch profile
- Remove current profile
- Use guest mode
- Enable debug features with existing password behavior
- Disable debug features
- Update app via existing worker/thread/dialog flow
- Save settings

### Behavior that must remain intact

- `settings_service.get()` remains the source of loaded settings
- `settings_service.save()` remains the persistence path
- `settings_changed` still emits after successful changes
- `apply_theme(self.app, settings)` still runs after saving theme/accent changes
- `normalize_theme_mode()` is still used for theme mode handling
- `log_service.prune_old_logs()` still runs after saving log retention
- Update flow remains based on the existing `QThread` worker pattern
- Bandwidth UI continues to show Mbit/s while persisting kbps, with `0` meaning unlimited
- Profile actions continue to use the settings service profile helpers

## New visual direction

- Dark-first control center with premium card surfaces and cleaner spacing
- Large hero header with concise subtitle and high-signal status pills
- Compact card-based sections with stronger hierarchy and less visible explanatory text
- Segmented controls for theme mode and relay mode
- Accent swatch picker with immediate visual feedback
- Polished pill toggles and action buttons with clear primary, secondary, ghost, and danger hierarchy
- Soft gradients, rounded corners, subtle borders, and restrained glass-panel feel
- Cleaner update area and action bar that feel intentional rather than form-like

## New component list

- `StatusPill`
- `SettingsHero`
- `SettingsCard`
- `SettingsRow`
- `SegmentedControl`
- `ColorSwatchButton`
- `ColorSwatchPicker`
- `ToggleSwitch` styling via reusable checkbox subclass or styled checkbox wrapper
- `PathInputRow`
- Refreshed `UpdateProgressDialog` shell styling

## Files that will be changed

- `docs/settings_page_premium_redesign.md`
- `ui/pages/settings_page.py`
- `ui/theme.py`
- `ui/components/common.py`

## Testing checklist

- App starts without import errors
- Settings page opens and scrolls correctly
- All preserved settings and actions are visible
- Theme mode loads, changes, saves, and syncs with existing theme switching
- Accent swatch loads, changes, and saves
- Default download folder browse works
- Ask-before-receiving saves
- Auto-open received folder saves
- Remember last folders saves
- Log retention saves and still prunes logs on save
- Upload and download bandwidth controls preserve unlimited/custom behavior and kbps conversion
- Relay mode toggles custom relay enable state correctly
- Croc binary browse works
- Delete Croc Binary still uses `context.croc_manager.delete_binary()`
- Auto-download croc saves
- Current profile display is correct
- Switch profile works
- Remove current profile works
- Guest mode works
- Debug status is accurate
- Enable debug features still requires the existing password flow
- Disable debug features works
- Update App still runs the update worker/dialog flow
- `settings_changed` emits after successful changes
- Dark, light, and system theme modes render without crashes
