from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.version import APP_VERSION
from ui.components.common import (
    ColorSwatchPicker,
    PathInputRow,
    SegmentedControl,
    SettingsCard,
    SettingsHero,
    SettingsRow,
    StatusPill,
    ToggleSwitch,
    repolish,
)
from ui.theme import apply_theme


class UpdateWorker(QObject):
    progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, update_service):
        super().__init__()
        self.update_service = update_service

    @Slot()
    def run(self):
        try:
            result = self.update_service.download_latest_update(
                progress_callback=lambda done, total: self.progress.emit(done, total),
                status_callback=lambda text: self.status.emit(text),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UpdateProgressDialog")
        self.setWindowTitle("Updating CrocDrop")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        self.title_label = QLabel("Installing the latest CrocDrop build")
        self.title_label.setObjectName("UpdateDialogTitle")
        self.subtitle_label = QLabel("The updater runs in the background while this window tracks progress.")
        self.subtitle_label.setObjectName("UpdateDialogSubtitle")
        self.subtitle_label.setWordWrap(True)

        self.status_label = QLabel("Preparing update ...")
        self.status_label.setObjectName("SettingsDescription")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)

        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(4)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(min(downloaded, total))
            percent = int((downloaded / total) * 100)
            self.status_label.setText(f"Downloading update ... {percent}%")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Downloading update ...")


class SettingsPage(QWidget):
    settings_changed = Signal()

    ACCENT_OPTIONS: tuple[tuple[str, str], ...] = (
        ("Purple", "#8f5cff"),
        ("Violet", "#b06cff"),
        ("Pink", "#ff7cc5"),
        ("Mint", "#35c9a5"),
        ("Blue", "#4aa8ff"),
        ("Orange", "#ffad4a"),
    )

    CATEGORY_OPTIONS: tuple[tuple[str, str], ...] = (
        ("general", "General"),
        ("transfers", "Transfers"),
        ("speed", "Speed Limits"),
        ("connection", "Connection"),
        ("profiles", "Profiles"),
        ("advanced", "Advanced"),
        ("updates", "Updates"),
    )

    def __init__(self, context, app):
        super().__init__()
        self.context = context
        self.app = app
        self.update_thread: QThread | None = None
        self.update_worker: UpdateWorker | None = None
        self.update_dialog: UpdateProgressDialog | None = None
        self._loading = False
        self._dirty = False
        self._current_category = "general"
        self._saved_settings_snapshot: dict[str, object] = {}
        self.category_buttons: dict[str, QPushButton] = {}
        self.category_pages: dict[str, QWidget] = {}

        self._build_ui()
        self._connect_signals()
        self._load_settings_into_controls()
        self.refresh_account_section()
        self.refresh_debug_controls()
        self._sync_relay_controls()
        self._sync_bandwidth_controls()
        self._refresh_binary_status()
        self._refresh_status_pills()
        self._switch_category("general")
        self._capture_saved_settings_snapshot()
        self._set_dirty(False)

    def _build_ui(self) -> None:
        self.setObjectName("SettingsPageRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        root.addWidget(self._build_header())
        root.addWidget(self._build_settings_shell(), 1)
        root.addWidget(self._build_action_bar())

    def _build_header(self) -> QWidget:
        self.hero = SettingsHero(
            "Settings",
            "Manage local preferences, transfers, connection tools, profiles, debug access, and updates.",
        )
        self._build_status_strip()
        return self.hero

    def _build_status_strip(self) -> None:
        self.accent_status_pill = StatusPill(variant="accent")
        self.relay_status_pill = StatusPill()
        self.profile_status_pill = StatusPill()
        self.debug_status_pill = StatusPill()
        self.version_status_pill = StatusPill(variant="accent")
        self.hero.set_status_pills(
            [
                self.accent_status_pill,
                self.relay_status_pill,
                self.profile_status_pill,
                self.debug_status_pill,
                self.version_status_pill,
            ]
        )

    def _build_settings_shell(self) -> QWidget:
        self.settings_shell = QFrame()
        self.settings_shell.setObjectName("SettingsShell")

        layout = QHBoxLayout(self.settings_shell)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)

        layout.addWidget(self._build_category_nav())
        layout.addWidget(self._build_content_panel(), 1)
        return self.settings_shell

    def _build_category_nav(self) -> QWidget:
        self.category_nav = QFrame()
        self.category_nav.setObjectName("SettingsCategoryNav")
        self.category_nav.setMinimumWidth(220)
        self.category_nav.setMaximumWidth(240)

        layout = QVBoxLayout(self.category_nav)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        nav_title = QLabel("Categories")
        nav_title.setObjectName("SettingsLabel")
        nav_subtitle = QLabel("Choose a settings area.")
        nav_subtitle.setObjectName("SettingsDescription")
        nav_subtitle.setWordWrap(True)

        layout.addWidget(nav_title)
        layout.addWidget(nav_subtitle)
        layout.addSpacing(4)

        self.category_button_group = QButtonGroup(self)
        self.category_button_group.setExclusive(True)

        for category_id, label in self.CATEGORY_OPTIONS:
            button = QPushButton(label)
            button.setObjectName("SettingsCategoryButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, key=category_id: self._switch_category(key))
            self.category_button_group.addButton(button)
            self.category_buttons[category_id] = button
            layout.addWidget(button)

        layout.addStretch(1)
        return self.category_nav

    def _build_content_panel(self) -> QWidget:
        self.content_panel = QFrame()
        self.content_panel.setObjectName("SettingsContentPanel")

        layout = QVBoxLayout(self.content_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("SettingsContentStack")
        layout.addWidget(self.content_stack)

        self._add_category_page("general", self._build_general_page())
        self._add_category_page("transfers", self._build_transfers_page())
        self._add_category_page("speed", self._build_speed_limits_page())
        self._add_category_page("connection", self._build_connection_page())
        self._add_category_page("profiles", self._build_profiles_page())
        self._add_category_page("advanced", self._build_advanced_page())
        self._add_category_page("updates", self._build_updates_page())

        return self.content_panel

    def _add_category_page(self, category_id: str, page: QWidget) -> None:
        self.category_pages[category_id] = page
        self.content_stack.addWidget(page)

    def _build_general_page(self) -> QWidget:
        self.accent_picker = ColorSwatchPicker(list(self.ACCENT_OPTIONS))
        self.remember_last = ToggleSwitch()
        self.log_retention = QSpinBox()
        self.log_retention.setRange(1, 120)
        self.log_retention.setMaximumWidth(96)

        log_widget = QWidget()
        log_layout = QHBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(8)
        log_layout.addWidget(self.log_retention)
        log_days = QLabel("days")
        log_days.setObjectName("SettingsDescription")
        log_layout.addWidget(log_days)
        log_layout.addStretch(1)

        preferences_card = SettingsCard("Local preferences", "Everyday defaults stored on this device.")
        preferences_card.add_widget(
            SettingsRow("Accent color", "Choose the highlight color used across CrocDrop.", self.accent_picker)
        )
        preferences_card.add_widget(
            SettingsRow("Remember last folders", "Reuse the most recent send and receive folders.", self.remember_last)
        )
        preferences_card.add_widget(
            SettingsRow("Log retention", "Remove old logs automatically after the selected number of days.", log_widget)
        )

        preview_card = SettingsCard("Accent preview", "A quick preview of the current accent selection.")
        self.accent_preview = QFrame()
        self.accent_preview.setObjectName("AccentPreviewPanel")
        preview_layout = QVBoxLayout(self.accent_preview)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(10)

        preview_header = QHBoxLayout()
        preview_header.setContentsMargins(0, 0, 0, 0)
        preview_header.setSpacing(8)
        preview_title_col = QVBoxLayout()
        preview_title_col.setContentsMargins(0, 0, 0, 0)
        preview_title_col.setSpacing(2)

        self.accent_preview_title = QLabel("Accent preview")
        self.accent_preview_title.setObjectName("SettingsLabel")
        self.accent_preview_caption = QLabel("Used for highlights, selection states, and primary actions.")
        self.accent_preview_caption.setObjectName("SettingsDescription")
        self.accent_preview_caption.setWordWrap(True)
        preview_title_col.addWidget(self.accent_preview_title)
        preview_title_col.addWidget(self.accent_preview_caption)

        self.accent_preview_pill = StatusPill("Accent", "accent")
        preview_header.addLayout(preview_title_col, 1)
        preview_header.addWidget(self.accent_preview_pill)

        self.accent_preview_strip = QFrame()
        self.accent_preview_strip.setObjectName("AccentPreviewStrip")
        self.accent_preview_strip.setFixedHeight(12)

        preview_layout.addLayout(preview_header)
        preview_layout.addWidget(self.accent_preview_strip)
        preview_card.add_widget(self.accent_preview)

        return self._build_subpage(
            "General",
            "Local appearance and housekeeping preferences.",
            [preferences_card, preview_card],
        )

    def _build_transfers_page(self) -> QWidget:
        self.download_path_row = PathInputRow(
            placeholder="Choose a default download folder",
            button_text="Browse",
        )
        self.ask_before = ToggleSwitch()
        self.auto_open = ToggleSwitch()

        receive_card = SettingsCard("Receiving defaults", "Set how incoming transfers should behave.")
        receive_card.add_widget(
            SettingsRow("Default download folder", "Destination used for incoming transfers.", self.download_path_row)
        )
        receive_card.add_widget(
            SettingsRow("Ask before receiving", "Require confirmation before CrocDrop accepts data.", self.ask_before)
        )
        receive_card.add_widget(
            SettingsRow("Auto-open received folder", "Open the destination folder after a successful receive.", self.auto_open)
        )

        return self._build_subpage(
            "Transfers",
            "Choose where incoming files go and how receive confirmations work.",
            [receive_card],
        )

    def _build_speed_limits_page(self) -> QWidget:
        (
            self.upload_limit_widget,
            self.upload_unlimited,
            self.upload_limit,
            self.upload_limit_unit,
        ) = self._create_bandwidth_control()
        (
            self.download_limit_widget,
            self.download_unlimited,
            self.download_limit,
            self.download_limit_unit,
        ) = self._create_bandwidth_control()

        limits_card = SettingsCard("Bandwidth", "Limit transfer bandwidth or keep CrocDrop unrestricted.")
        limits_card.add_widget(
            SettingsRow("Upload speed", "Unlimited saves as 0 kbps and disables manual entry.", self.upload_limit_widget)
        )
        limits_card.add_widget(
            SettingsRow("Download speed", "Displayed in Mbit/s while persisted internally as kbps.", self.download_limit_widget)
        )
        helper = QLabel("Unlimited is usually best for local transfers.")
        helper.setObjectName("SettingsDescription")
        helper.setWordWrap(True)
        limits_card.add_widget(helper)

        return self._build_subpage(
            "Speed Limits",
            "Control transfer bandwidth without changing Croc compatibility.",
            [limits_card],
        )

    def _build_connection_page(self) -> QWidget:
        self.relay_mode_control = SegmentedControl(
            [("public", "Public relay"), ("custom", "Custom relay")],
            current_value="public",
        )
        self.custom_relay = QLineEdit()
        self.custom_relay.setPlaceholderText("relay.example.com:9009")
        self.custom_relay.setClearButtonEnabled(True)

        relay_card = SettingsCard("Relay", "Choose the default relay mode used by transfers.")
        relay_card.add_widget(
            SettingsRow("Relay mode", "Use the public relay or point CrocDrop at a custom endpoint.", self.relay_mode_control)
        )
        self.custom_relay_row = SettingsRow(
            "Custom relay",
            "Only used when custom relay mode is selected.",
            self.custom_relay,
        )
        relay_card.add_widget(self.custom_relay_row)

        self.binary_status = StatusPill()
        self.binary_status_label = QLabel()
        self.binary_status_label.setObjectName("SettingsDescription")
        binary_status_widget = QWidget()
        binary_status_layout = QHBoxLayout(binary_status_widget)
        binary_status_layout.setContentsMargins(0, 0, 0, 0)
        binary_status_layout.setSpacing(8)
        binary_status_layout.addWidget(self.binary_status)
        binary_status_layout.addWidget(self.binary_status_label, 1)

        self.binary_path_row = PathInputRow(
            placeholder="Select the croc executable path",
            button_text="Browse Binary",
            extra_button_text="Delete Binary",
        )
        if self.binary_path_row.extra_button is not None:
            self.binary_path_row.extra_button.setObjectName("DangerButton")

        self.auto_download = ToggleSwitch()

        binary_card = SettingsCard("Croc binary", "Manage the croc executable used by this installation.")
        binary_card.add_widget(
            SettingsRow("Binary status", "Current croc binary strategy for this device.", binary_status_widget)
        )
        binary_card.add_widget(
            SettingsRow("Croc binary path", "Manual executable path used by this installation.", self.binary_path_row)
        )
        binary_card.add_widget(
            SettingsRow("Auto-download croc", "Fetch croc automatically when a binary is missing.", self.auto_download)
        )

        return self._build_subpage(
            "Connection",
            "Relay routing and croc binary controls.",
            [relay_card, binary_card],
        )

    def _build_profiles_page(self) -> QWidget:
        self.current_profile_pill = StatusPill()
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(220)

        self.switch_profile_btn = QPushButton("Switch Profile")
        self.switch_profile_btn.setObjectName("SecondaryButton")
        self.guest_mode_btn = QPushButton("Use Guest Mode")
        self.guest_mode_btn.setObjectName("GhostButton")
        self.remove_profile_btn = QPushButton("Remove Current Profile")
        self.remove_profile_btn.setObjectName("DangerButton")

        profile_picker = QWidget()
        profile_picker_layout = QHBoxLayout(profile_picker)
        profile_picker_layout.setContentsMargins(0, 0, 0, 0)
        profile_picker_layout.setSpacing(8)
        profile_picker_layout.addWidget(self.profile_combo, 1)
        profile_picker_layout.addWidget(self.switch_profile_btn)

        profile_actions = QWidget()
        profile_actions_layout = QHBoxLayout(profile_actions)
        profile_actions_layout.setContentsMargins(0, 0, 0, 0)
        profile_actions_layout.setSpacing(8)
        profile_actions_layout.addWidget(self.guest_mode_btn)
        profile_actions_layout.addWidget(self.remove_profile_btn)
        profile_actions_layout.addStretch(1)

        profiles_card = SettingsCard("Profiles", "Profiles stay local to this installation.")
        profiles_card.add_widget(
            SettingsRow("Current profile", "The active local profile shown across the app.", self.current_profile_pill)
        )
        profiles_card.add_widget(
            SettingsRow("Profile selector", "Switch between saved local profiles.", profile_picker)
        )
        profiles_card.add_widget(profile_actions)

        return self._build_subpage(
            "Profiles",
            "Switch between saved profiles or return to guest mode.",
            [profiles_card],
        )

    def _build_advanced_page(self) -> QWidget:
        self.debug_state_pill = StatusPill()
        self.debug_state_label = QLabel()
        self.debug_state_label.setObjectName("SettingsDescription")
        debug_status_widget = QWidget()
        debug_status_layout = QHBoxLayout(debug_status_widget)
        debug_status_layout.setContentsMargins(0, 0, 0, 0)
        debug_status_layout.setSpacing(8)
        debug_status_layout.addWidget(self.debug_state_pill)
        debug_status_layout.addWidget(self.debug_state_label, 1)

        self.enable_debug_btn = QPushButton("Enable Debug Features")
        self.enable_debug_btn.setObjectName("SecondaryButton")
        self.disable_debug_btn = QPushButton("Disable Debug Features")
        self.disable_debug_btn.setObjectName("DangerButton")

        debug_actions = QWidget()
        debug_actions_layout = QHBoxLayout(debug_actions)
        debug_actions_layout.setContentsMargins(0, 0, 0, 0)
        debug_actions_layout.setSpacing(8)
        debug_actions_layout.addWidget(self.enable_debug_btn)
        debug_actions_layout.addWidget(self.disable_debug_btn)
        debug_actions_layout.addStretch(1)

        advanced_card = SettingsCard("Debug tools", "High-impact controls for local troubleshooting.")
        advanced_card.add_widget(
            SettingsRow("Debug status", "Changes take effect after the next CrocDrop launch.", debug_status_widget)
        )
        advanced_card.add_widget(debug_actions)

        return self._build_subpage(
            "Advanced",
            "Sensitive controls that should only be changed intentionally.",
            [advanced_card],
        )

    def _build_updates_page(self) -> QWidget:
        self.current_version_chip = StatusPill(APP_VERSION, "accent")
        self.update_status_chip = StatusPill("Ready", "success")
        self.update_status_label = QLabel("Ready to check for updates.")
        self.update_status_label.setObjectName("SettingsDescription")

        update_status_widget = QWidget()
        update_status_layout = QHBoxLayout(update_status_widget)
        update_status_layout.setContentsMargins(0, 0, 0, 0)
        update_status_layout.setSpacing(8)
        update_status_layout.addWidget(self.update_status_chip)
        update_status_layout.addWidget(self.update_status_label, 1)

        self.update_btn = QPushButton("Update App")
        self.update_btn.setObjectName("PrimaryButton")

        update_action_row = QWidget()
        update_action_layout = QHBoxLayout(update_action_row)
        update_action_layout.setContentsMargins(0, 0, 0, 0)
        update_action_layout.setSpacing(8)
        update_action_layout.addWidget(self.update_btn)
        update_action_layout.addStretch(1)

        updates_card = SettingsCard("Application updates", "Check the current build and download the latest release.")
        updates_card.add_widget(
            SettingsRow("Current version", "Version installed on this device.", self.current_version_chip)
        )
        updates_card.add_widget(
            SettingsRow("Update status", "Latest release downloads run in the background.", update_status_widget)
        )
        updates_card.add_widget(update_action_row)

        return self._build_subpage(
            "Updates",
            "Keep CrocDrop current without affecting your saved settings.",
            [updates_card],
        )

    def _build_subpage(self, title: str, subtitle: str, cards: list[QWidget]) -> QWidget:
        content = QWidget()
        content.setObjectName("SettingsSubpage")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("SettingsSubpageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("SettingsSubpageSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        for card in cards:
            layout.addWidget(card)

        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _build_action_bar(self) -> QWidget:
        self.action_bar = QFrame()
        self.action_bar.setObjectName("SettingsActionBar")

        layout = QHBoxLayout(self.action_bar)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)
        self.dirty_pill = StatusPill("All changes saved", "success")
        self.action_hint = QLabel("Settings are stored locally.")
        self.action_hint.setObjectName("SettingsDescription")
        text_col.addWidget(self.dirty_pill, 0, Qt.AlignmentFlag.AlignLeft)
        text_col.addWidget(self.action_hint)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setMinimumWidth(180)

        layout.addLayout(text_col, 1)
        layout.addWidget(self.save_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return self.action_bar

    def _connect_signals(self) -> None:
        self.download_path_row.primary_button.clicked.connect(self.pick_folder)
        self.binary_path_row.primary_button.clicked.connect(self.pick_binary)
        if self.binary_path_row.extra_button is not None:
            self.binary_path_row.extra_button.clicked.connect(self.delete_binary)

        self.save_btn.clicked.connect(self.save)
        self.update_btn.clicked.connect(self.update_app)

        self.switch_profile_btn.clicked.connect(self.switch_profile)
        self.remove_profile_btn.clicked.connect(self.remove_current_profile)
        self.guest_mode_btn.clicked.connect(self.set_guest_mode)
        self.enable_debug_btn.clicked.connect(self.enable_debug_features)
        self.disable_debug_btn.clicked.connect(self.disable_debug_features)

        self.accent_picker.valueChanged.connect(lambda _value: self._on_accent_changed())
        self.remember_last.toggled.connect(lambda _checked: self._mark_dirty())
        self.log_retention.valueChanged.connect(lambda _value: self._mark_dirty())

        self.download_path_row.line_edit.textChanged.connect(lambda _text: self._mark_dirty())
        self.ask_before.toggled.connect(lambda _checked: self._mark_dirty())
        self.auto_open.toggled.connect(lambda _checked: self._mark_dirty())

        self.relay_mode_control.valueChanged.connect(lambda _value: self._on_relay_changed())
        self.custom_relay.textChanged.connect(lambda _text: self._on_relay_changed())
        self.binary_path_row.line_edit.textChanged.connect(lambda _text: self._on_binary_controls_changed())
        self.auto_download.toggled.connect(lambda _checked: self._on_binary_controls_changed())

        self.upload_unlimited.toggled.connect(lambda _checked: self._on_bandwidth_changed())
        self.upload_limit.textChanged.connect(lambda _text: self._on_bandwidth_changed())
        self.download_unlimited.toggled.connect(lambda _checked: self._on_bandwidth_changed())
        self.download_limit.textChanged.connect(lambda _text: self._on_bandwidth_changed())

    def _switch_category(self, category_id: str) -> None:
        if category_id not in self.category_pages:
            return
        self._current_category = category_id
        self.content_stack.setCurrentWidget(self.category_pages[category_id])
        self._refresh_category_button_states()

    def open_category(self, category_id: str) -> None:
        normalized = (category_id or "").strip().lower()
        aliases = {
            "general": "general",
            "transfer": "transfers",
            "transfers": "transfers",
            "speed": "speed",
            "speed_limits": "speed",
            "speed-limits": "speed",
            "connection": "connection",
            "profile": "profiles",
            "profiles": "profiles",
            "account": "profiles",
            "advanced": "advanced",
            "updates": "updates",
        }
        self._switch_category(aliases.get(normalized, normalized))

    @property
    def current_category(self) -> str:
        return self._current_category

    def _refresh_category_button_states(self) -> None:
        for category_id, button in self.category_buttons.items():
            selected = category_id == self._current_category
            button.blockSignals(True)
            button.setChecked(selected)
            button.blockSignals(False)
            button.setProperty("selected", selected)
            repolish(button)

    def _load_settings_into_controls(self) -> None:
        settings = self.context.settings_service.get()
        self._loading = True
        try:
            self.download_path_row.line_edit.setText(settings.default_download_folder)
            self.ask_before.setChecked(settings.ask_before_receiving)
            self.auto_open.setChecked(settings.auto_open_received_folder)
            self.remember_last.setChecked(settings.remember_last_folders)

            accent = settings.accent_color if settings.accent_color in {color for _name, color in self.ACCENT_OPTIONS} else self.ACCENT_OPTIONS[0][1]
            self.accent_picker.set_current_value(accent, emit_signal=False)

            self.relay_mode_control.set_current_value(settings.relay_mode or "public", emit_signal=False)
            self.custom_relay.setText(settings.custom_relay)
            self.binary_path_row.line_edit.setText(settings.croc_binary_path)
            self.auto_download.setChecked(settings.auto_download_croc)

            self.log_retention.setValue(settings.log_retention_days)

            self._set_bandwidth_control(settings.upload_limit_kbps, self.upload_unlimited, self.upload_limit)
            self._set_bandwidth_control(settings.download_limit_kbps, self.download_unlimited, self.download_limit)

            self.current_version_chip.setText(APP_VERSION)
            self.update_status_chip.setText("Ready")
            self.update_status_chip.set_variant("success")
            self.update_status_label.setText("Ready to check for updates.")
            self._apply_pending_accent()
        finally:
            self._loading = False
        self._capture_saved_settings_snapshot()

    def _collect_settings_from_controls(self):
        settings = self.context.settings_service.get()
        updated = deepcopy(settings.to_dict())
        updated["default_download_folder"] = self.download_path_row.line_edit.text().strip()
        updated["ask_before_receiving"] = self.ask_before.isChecked()
        updated["auto_open_received_folder"] = self.auto_open.isChecked()
        updated["remember_last_folders"] = self.remember_last.isChecked()
        updated["accent_color"] = self.accent_picker.current_value()
        updated["relay_mode"] = self.relay_mode_control.current_value()
        updated["custom_relay"] = self.custom_relay.text().strip()
        updated["croc_binary_path"] = self.binary_path_row.line_edit.text().strip()
        updated["auto_download_croc"] = self.auto_download.isChecked()
        updated["upload_limit_kbps"] = self._read_bandwidth_limit_kbps(self.upload_unlimited, self.upload_limit)
        updated["download_limit_kbps"] = self._read_bandwidth_limit_kbps(self.download_unlimited, self.download_limit)
        updated["log_retention_days"] = self.log_retention.value()
        return settings.from_dict(updated)

    def _capture_saved_settings_snapshot(self) -> None:
        self._saved_settings_snapshot = self._settings_snapshot(self.context.settings_service.get())

    def _settings_snapshot(self, settings) -> dict[str, object]:
        return {
            "default_download_folder": settings.default_download_folder.strip(),
            "ask_before_receiving": bool(settings.ask_before_receiving),
            "auto_open_received_folder": bool(settings.auto_open_received_folder),
            "remember_last_folders": bool(settings.remember_last_folders),
            "accent_color": settings.accent_color,
            "relay_mode": settings.relay_mode or "public",
            "custom_relay": settings.custom_relay.strip(),
            "croc_binary_path": settings.croc_binary_path.strip(),
            "auto_download_croc": bool(settings.auto_download_croc),
            "upload_limit_kbps": int(settings.upload_limit_kbps),
            "download_limit_kbps": int(settings.download_limit_kbps),
            "log_retention_days": int(settings.log_retention_days),
        }

    def _current_settings_snapshot(self) -> dict[str, object]:
        return {
            "default_download_folder": self.download_path_row.line_edit.text().strip(),
            "ask_before_receiving": self.ask_before.isChecked(),
            "auto_open_received_folder": self.auto_open.isChecked(),
            "remember_last_folders": self.remember_last.isChecked(),
            "accent_color": self.accent_picker.current_value(),
            "relay_mode": self.relay_mode_control.current_value(),
            "custom_relay": self.custom_relay.text().strip(),
            "croc_binary_path": self.binary_path_row.line_edit.text().strip(),
            "auto_download_croc": self.auto_download.isChecked(),
            "upload_limit_kbps": self._read_bandwidth_limit_kbps(self.upload_unlimited, self.upload_limit),
            "download_limit_kbps": self._read_bandwidth_limit_kbps(self.download_unlimited, self.download_limit),
            "log_retention_days": self.log_retention.value(),
        }

    def _create_bandwidth_control(self) -> tuple[QWidget, ToggleSwitch, QLineEdit, QLabel]:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        unlimited = ToggleSwitch()
        unlimited_label = QLabel("Unlimited")
        unlimited_label.setObjectName("SettingsDescription")

        value_input = QLineEdit()
        value_input.setPlaceholderText("Enter Mbit/s")
        value_input.setValidator(QDoubleValidator(0.01, 1_000_000.0, 2, value_input))
        value_input.setClearButtonEnabled(True)
        value_input.setMaximumWidth(120)

        unit_label = QLabel("Mbit/s")
        unit_label.setObjectName("SettingsDescription")

        layout.addWidget(unlimited)
        layout.addWidget(unlimited_label)
        layout.addSpacing(4)
        layout.addWidget(value_input)
        layout.addWidget(unit_label)
        layout.addStretch(1)
        return widget, unlimited, value_input, unit_label

    def _set_bandwidth_control(self, limit_kbps: int, toggle: ToggleSwitch, value_input: QLineEdit) -> None:
        toggle.setChecked(limit_kbps <= 0)
        value_input.setText(self._format_limit_mbit(limit_kbps))

    def _sync_bandwidth_controls(self) -> None:
        for toggle, input_widget, unit_label in (
            (self.upload_unlimited, self.upload_limit, self.upload_limit_unit),
            (self.download_unlimited, self.download_limit, self.download_limit_unit),
        ):
            enabled = not toggle.isChecked()
            input_widget.setEnabled(enabled)
            unit_label.setEnabled(enabled)

    def _sync_relay_controls(self) -> None:
        is_custom = self.relay_mode_control.current_value() == "custom"
        self.custom_relay.setEnabled(is_custom)
        self.custom_relay.setPlaceholderText("relay.example.com:9009" if is_custom else "Public relay mode is active")

    def _refresh_status_pills(self) -> None:
        accent_name = self._accent_name(self.accent_picker.current_value())
        relay_mode = self.relay_mode_control.current_value()
        current_profile = self.context.settings_service.get().current_profile.strip() or "Guest"
        debug_enabled = self.context.settings_service.get().debug_mode

        self.accent_status_pill.set_variant("accent")
        self.accent_status_pill.setText(f"Accent {accent_name}")

        if relay_mode == "custom":
            relay_variant = "warning" if not self.custom_relay.text().strip() else "accent"
            relay_text = "Relay Custom"
        else:
            relay_variant = "success"
            relay_text = "Relay Public"
        self.relay_status_pill.set_variant(relay_variant)
        self.relay_status_pill.setText(relay_text)

        self.profile_status_pill.set_variant("accent" if current_profile != "Guest" else "neutral")
        self.profile_status_pill.setText(f"Profile {current_profile}")

        self.debug_status_pill.set_variant("danger" if debug_enabled else "success")
        self.debug_status_pill.setText(f"Debug {'On' if debug_enabled else 'Off'}")

        self.version_status_pill.set_variant("accent")
        self.version_status_pill.setText(f"Version {APP_VERSION}")

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = bool(dirty)
        if self._dirty:
            self.dirty_pill.set_variant("warning")
            self.dirty_pill.setText("Unsaved changes")
            self.action_hint.setText("Review your changes and save when you're ready.")
        else:
            self.dirty_pill.set_variant("success")
            self.dirty_pill.setText("All changes saved")
            self.action_hint.setText("Settings are stored locally.")

    def _mark_dirty(self) -> None:
        if self._loading:
            return
        self._set_dirty(self._current_settings_snapshot() != self._saved_settings_snapshot)
        self._refresh_status_pills()

    def _apply_pending_accent(self) -> None:
        accent = self.accent_picker.current_value()
        for toggle in (
            self.remember_last,
            self.ask_before,
            self.auto_open,
            self.auto_download,
            self.upload_unlimited,
            self.download_unlimited,
        ):
            toggle.set_accent_color(accent)
        self._refresh_accent_preview()

    def _refresh_accent_preview(self) -> None:
        accent = self.accent_picker.current_value()
        accent_name = self._accent_name(accent)
        soft = self._rgba(accent, 42)
        line = self._rgba(accent, 92)
        glow = self._rgba(accent, 190)

        self.accent_preview_title.setText(f"{accent_name} accent")
        self.accent_preview_pill.setText(f"Accent {accent_name}")
        self.accent_preview.setStyleSheet(
            f"""
            QFrame#AccentPreviewPanel {{
                border-radius: 16px;
                border: 1px solid {line};
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {soft},
                    stop:1 rgba(255, 255, 255, 0)
                );
            }}
            QFrame#AccentPreviewStrip {{
                border-radius: 6px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent},
                    stop:1 {glow}
                );
            }}
            """
        )

    def _refresh_binary_status(self) -> None:
        path = self.binary_path_row.line_edit.text().strip()
        if path:
            self.binary_status.set_variant("success")
            self.binary_status.setText("Binary set")
            self.binary_status_label.setText("Using a manual croc executable path.")
        elif self.auto_download.isChecked():
            self.binary_status.set_variant("accent")
            self.binary_status.setText("Auto-managed")
            self.binary_status_label.setText("CrocDrop will fetch croc automatically when needed.")
        else:
            self.binary_status.set_variant("warning")
            self.binary_status.setText("Missing path")
            self.binary_status_label.setText("Set a binary path or re-enable auto-download.")

    def _on_accent_changed(self) -> None:
        self._apply_pending_accent()
        self._refresh_status_pills()
        self._mark_dirty()

    def _on_relay_changed(self) -> None:
        self._sync_relay_controls()
        self._refresh_status_pills()
        self._mark_dirty()

    def _on_binary_controls_changed(self) -> None:
        self._refresh_binary_status()
        self._refresh_status_pills()
        self._mark_dirty()

    def _on_bandwidth_changed(self) -> None:
        self._sync_bandwidth_controls()
        self._mark_dirty()

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose default download folder",
            self.download_path_row.line_edit.text(),
        )
        if folder:
            self.download_path_row.line_edit.setText(folder)

    def pick_binary(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select croc binary",
            self.binary_path_row.line_edit.text() or "",
            "Executable (*.exe);;All Files (*)",
        )
        if path:
            self.binary_path_row.line_edit.setText(path)

    def save(self):
        settings = self._collect_settings_from_controls()
        apply_theme(self.app, settings)
        self.context.settings_service.save(settings)
        self._capture_saved_settings_snapshot()
        self.context.log_service.prune_old_logs(settings.log_retention_days)
        self.refresh_account_section()
        self.refresh_debug_controls()
        self._refresh_binary_status()
        self._refresh_status_pills()
        self._set_dirty(False)
        self.settings_changed.emit()

    def refresh_theme_mode_control(self) -> None:
        self._refresh_status_pills()

    def delete_binary(self):
        path_text = self.binary_path_row.line_edit.text().strip()
        display_target = path_text or "(auto-detected current croc)"
        answer = QMessageBox.question(
            self,
            "Delete Croc Binary",
            f"Delete croc binary at:\n{display_target}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        ok, message = self.context.croc_manager.delete_binary(path_text or None)
        if ok:
            self.binary_path_row.line_edit.setText("")
            settings = self.context.settings_service.get()
            settings.croc_binary_path = ""
            self.context.settings_service.save(settings)
            self._capture_saved_settings_snapshot()
            self._refresh_binary_status()
            self._refresh_status_pills()
            self._set_dirty(self._current_settings_snapshot() != self._saved_settings_snapshot)
            QMessageBox.information(self, "Delete Croc Binary", message)
            self.settings_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Croc Binary", message)

    def refresh_account_section(self):
        settings = self.context.settings_service.get()
        current = settings.current_profile.strip()
        display_current = current if current else "Guest"

        self.current_profile_pill.set_variant("accent" if current else "neutral")
        self.current_profile_pill.setText(display_current)

        self.profile_combo.clear()
        self.profile_combo.addItems(settings.profiles)
        if current and current in settings.profiles:
            self.profile_combo.setCurrentText(current)

        self.remove_profile_btn.setEnabled(bool(current))
        self.switch_profile_btn.setEnabled(self.profile_combo.count() > 0)
        self._refresh_status_pills()

    def switch_profile(self):
        selected = self.profile_combo.currentText().strip()
        if not selected:
            return
        self.context.settings_service.set_current_profile(selected)
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", f"Switched profile to '{selected}'.")

    def remove_current_profile(self):
        settings = self.context.settings_service.get()
        current = settings.current_profile.strip()
        if not current:
            QMessageBox.information(self, "Profile", "You are already in guest mode.")
            return
        answer = QMessageBox.question(
            self,
            "Remove Profile",
            f"Remove account profile '{current}'?\n\nYou will return to guest mode.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.context.settings_service.remove_profile(current)
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", f"Removed '{current}'.")

    def set_guest_mode(self):
        self.context.settings_service.use_guest_mode()
        self.refresh_account_section()
        self.settings_changed.emit()
        QMessageBox.information(self, "Profile", "Guest mode enabled. You will be asked at startup next launch.")

    def enable_debug_features(self):
        password, ok = QInputDialog.getText(self, "Enable Debug", "Enter admin password:", QLineEdit.Password)
        if not ok:
            return
        if password != "admin":
            QMessageBox.warning(self, "Enable Debug", "Wrong password.")
            return

        settings = self.context.settings_service.get()
        settings.debug_mode = True
        self.context.settings_service.save(settings)
        self.refresh_debug_controls()
        self.settings_changed.emit()
        QMessageBox.information(self, "Enable Debug", "Debug features enabled. Restart CrocDrop to show the Debug page.")

    def disable_debug_features(self):
        settings = self.context.settings_service.get()
        if not settings.debug_mode:
            self.refresh_debug_controls()
            return
        settings.debug_mode = False
        self.context.settings_service.save(settings)
        self.refresh_debug_controls()
        self.settings_changed.emit()
        QMessageBox.information(self, "Disable Debug", "Debug features disabled. Restart CrocDrop to hide the Debug page.")

    def refresh_debug_controls(self):
        enabled = self.context.settings_service.get().debug_mode
        self.debug_state_pill.set_variant("danger" if enabled else "success")
        self.debug_state_pill.setText("Debug enabled" if enabled else "Debug disabled")
        self.debug_state_label.setText(
            "The Debug page will stay visible after restart." if enabled else "Hidden by default until explicitly enabled."
        )
        self.enable_debug_btn.setEnabled(not enabled)
        self.disable_debug_btn.setEnabled(enabled)
        self._refresh_status_pills()

    def update_app(self):
        if self.update_thread is not None:
            QMessageBox.information(self, "Update App", "An update check is already running.")
            return

        self.update_btn.setEnabled(False)
        self.update_status_chip.set_variant("warning")
        self.update_status_chip.setText("Checking")
        self.update_status_label.setText("Checking GitHub releases ...")

        self.update_dialog = UpdateProgressDialog(self)
        self.update_dialog.set_status("Checking GitHub releases ...")
        self.update_dialog.show()

        self.update_thread = QThread(self)
        self.update_worker = UpdateWorker(self.context.update_service)
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.progress.connect(self._on_update_progress)
        self.update_worker.status.connect(self._on_update_status)
        self.update_worker.finished.connect(self._on_update_finished)
        self.update_worker.failed.connect(self._on_update_failed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self._cleanup_update_thread)
        self.update_thread.start()

    def _cleanup_update_thread(self):
        if self.update_worker is not None:
            self.update_worker.deleteLater()
            self.update_worker = None
        if self.update_thread is not None:
            self.update_thread.deleteLater()
            self.update_thread = None
        self.update_btn.setEnabled(True)

    def _on_update_progress(self, downloaded: int, total: int):
        if self.update_dialog is not None:
            self.update_dialog.set_progress(downloaded, total)
        self.update_status_chip.set_variant("warning")
        self.update_status_chip.setText("Downloading")
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.update_status_label.setText(f"Downloading update ... {percent}%")
        else:
            self.update_status_label.setText("Downloading update ...")

    def _on_update_status(self, text: str):
        if self.update_dialog is not None:
            self.update_dialog.set_status(text)
        self.update_status_chip.set_variant("warning")
        self.update_status_chip.setText("Working")
        self.update_status_label.setText(text)

    def _on_update_failed(self, message: str):
        if self.update_dialog is not None:
            self.update_dialog.close()
            self.update_dialog.deleteLater()
            self.update_dialog = None
        self.update_status_chip.set_variant("danger")
        self.update_status_chip.setText("Failed")
        self.update_status_label.setText(message)
        QMessageBox.warning(self, "Update App", f"Update failed:\n{message}")

    def _on_update_finished(self, result):
        if self.update_dialog is not None:
            self.update_dialog.close()
            self.update_dialog.deleteLater()
            self.update_dialog = None

        if result.status == "up-to-date":
            self.update_status_chip.set_variant("success")
            self.update_status_chip.setText("Up to date")
            self.update_status_label.setText(result.message)
            QMessageBox.information(self, "Update App", result.message)
            return

        if result.status != "downloaded" or not result.archive_path:
            self.update_status_chip.set_variant("warning")
            self.update_status_chip.setText("Unexpected")
            self.update_status_label.setText("Update completed with an unexpected result.")
            QMessageBox.warning(self, "Update App", "Update completed with an unexpected result.")
            return

        self.update_status_chip.set_variant("success")
        self.update_status_chip.setText("Ready to install")
        self.update_status_label.setText(f"Update {result.latest_version} downloaded.")

        answer = QMessageBox.information(
            self,
            "Update Ready",
            (
                f"Update {result.latest_version} downloaded.\n\n"
                "CrocDrop will now close, apply the update, and start again automatically."
            ),
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Ok,
        )
        if answer != QMessageBox.Ok:
            return

        try:
            self.context.update_service.apply_update_and_restart(result.archive_path)
        except Exception as exc:
            self.update_status_chip.set_variant("danger")
            self.update_status_chip.setText("Install failed")
            self.update_status_label.setText(str(exc))
            QMessageBox.warning(self, "Update App", f"Could not start updater:\n{exc}")
            return
        QApplication.quit()

    @staticmethod
    def _format_limit_mbit(limit_kbps: int) -> str:
        if limit_kbps <= 0:
            return ""
        value = limit_kbps / 125.0
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _read_bandwidth_limit_kbps(unlimited: ToggleSwitch, value_input: QLineEdit) -> int:
        if unlimited.isChecked():
            return 0
        text = value_input.text().strip().replace(",", ".")
        if not text:
            return 0
        try:
            value_mbit = float(text)
        except ValueError:
            return 0
        if value_mbit <= 0:
            return 0
        return max(1, int(round(value_mbit * 125.0)))

    @classmethod
    def _accent_name(cls, color: str) -> str:
        for name, hex_value in cls.ACCENT_OPTIONS:
            if hex_value == color:
                return name
        return "Accent"

    @staticmethod
    def _rgba(color: str, alpha: int) -> str:
        channel = color.lstrip("#")
        if len(channel) != 6:
            return f"rgba(143, 92, 255, {alpha})"
        red = int(channel[0:2], 16)
        green = int(channel[2:4], 16)
        blue = int(channel[4:6], 16)
        return f"rgba({red}, {green}, {blue}, {alpha})"
