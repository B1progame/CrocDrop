from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication

from models.settings import AppSettings

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_SYSTEM = "system"
THEME_MODE_OPTIONS: tuple[tuple[str, str], ...] = (
    (THEME_DARK, "Dark"),
    (THEME_LIGHT, "Light"),
    (THEME_SYSTEM, "System"),
)


def normalize_theme_mode(theme_mode: str | None, dark_mode: bool = True) -> str:
    if theme_mode in {THEME_DARK, THEME_LIGHT, THEME_SYSTEM}:
        return theme_mode
    return THEME_DARK if dark_mode else THEME_LIGHT


def system_prefers_dark(app=None) -> bool:
    try:
        candidate = app or QGuiApplication.instance()
        if candidate is not None:
            scheme = candidate.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return False
            if scheme == Qt.ColorScheme.Dark:
                return True
    except Exception:
        pass
    return True


def resolve_dark_mode(settings: AppSettings, app=None) -> bool:
    mode = normalize_theme_mode(settings.theme_mode, settings.dark_mode)
    if mode == THEME_DARK:
        return True
    if mode == THEME_LIGHT:
        return False
    return system_prefers_dark(app)


def _blend_colors(color_a: str, color_b: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    first = QColor(color_a)
    second = QColor(color_b)
    red = round(first.red() * (1.0 - ratio) + second.red() * ratio)
    green = round(first.green() * (1.0 - ratio) + second.green() * ratio)
    blue = round(first.blue() * (1.0 - ratio) + second.blue() * ratio)
    return QColor(red, green, blue).name()


def _with_alpha(color: str, alpha: int) -> str:
    candidate = QColor(color)
    return f"rgba({candidate.red()}, {candidate.green()}, {candidate.blue()}, {max(0, min(255, alpha))})"


def apply_theme(app, settings: AppSettings) -> None:
    # Some systems can surface a default font with no point/pixel size set,
    # which can trigger QFont::setPointSize warnings during style updates.
    base_font = app.font()
    if base_font.pointSize() <= 0 and base_font.pixelSize() <= 0:
        fallback = QFont(base_font)
        fallback.setPointSize(10)
        app.setFont(fallback)

    settings.theme_mode = normalize_theme_mode(settings.theme_mode, settings.dark_mode)
    settings.dark_mode = resolve_dark_mode(settings, app)

    accent = settings.accent_color or "#8f5cff"
    if settings.dark_mode:
        palette = {
            "base_bg": "#0c1118",
            "surface_0": "#121923",
            "surface_1": "#171f2c",
            "surface_2": "#1d2736",
            "line": "#2a374b",
            "line_soft": "#212d3f",
            "text": "#e6edf7",
            "text_soft": "#a0afc5",
            "selected_text": "#ffffff",
            "input_bg": "#101722",
            "input_bg_alt": "#0f1621",
            "hover": "#22334a",
            "pressed": "#1a2a3f",
            "success": "#49d59e",
            "warning": "#ffb457",
            "danger": "#ff6f6f",
            "theme_shell": "rgba(28, 39, 57, 0.78)",
            "theme_shell_border": "rgba(166, 186, 214, 0.12)",
            "theme_track": "rgba(10, 15, 24, 0.88)",
            "theme_border": "rgba(166, 186, 214, 0.10)",
            "theme_button_hover": "rgba(255, 255, 255, 0.045)",
            "theme_button_pressed": "rgba(255, 255, 255, 0.07)",
        }
    else:
        palette = {
            "base_bg": "#eef3f8",
            "surface_0": "#f6f9fc",
            "surface_1": "#ffffff",
            "surface_2": "#f4f7fb",
            "line": "#cfd8e4",
            "line_soft": "#dbe2ec",
            "text": "#0f1726",
            "text_soft": "#2c3d52",
            "selected_text": "#0f1726",
            "input_bg": "#ffffff",
            "input_bg_alt": "#f8fbff",
            "hover": "#ecf3fb",
            "pressed": "#dfebf8",
            "success": "#1f9768",
            "warning": "#c47a1d",
            "danger": "#c23d3d",
            "theme_shell": "rgba(255, 255, 255, 0.96)",
            "theme_shell_border": "rgba(124, 144, 168, 0.16)",
            "theme_track": "rgba(244, 247, 252, 0.96)",
            "theme_border": "rgba(124, 144, 168, 0.12)",
            "theme_button_hover": "rgba(89, 108, 132, 0.08)",
            "theme_button_pressed": "rgba(89, 108, 132, 0.12)",
        }
    accent_start = _blend_colors(accent, "#09121d" if settings.dark_mode else "#ffffff", 0.24 if settings.dark_mode else 0.08)
    accent_end = _blend_colors(accent, "#ffffff", 0.26 if settings.dark_mode else 0.34)
    accent_gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {accent_start}, stop:0.58 {accent}, stop:1 {accent_end})"
    accent_gradient_soft = (
        "qlineargradient("
        f"x1:0, y1:0, x2:1, y2:1, stop:0 {_with_alpha(accent_start, 120 if settings.dark_mode else 82)}, "
        f"stop:1 {_with_alpha(accent_end, 132 if settings.dark_mode else 92)})"
    )
    accent_soft = _with_alpha(accent, 40 if settings.dark_mode else 22)
    accent_border = _with_alpha(accent, 120 if settings.dark_mode else 92)
    success_surface = _blend_colors(palette["success"], palette["surface_1"], 0.82 if settings.dark_mode else 0.9)
    warning_surface = _blend_colors(palette["warning"], palette["surface_1"], 0.82 if settings.dark_mode else 0.9)
    danger_surface = _blend_colors(palette["danger"], palette["surface_1"], 0.82 if settings.dark_mode else 0.9)

    app.setStyleSheet(
        f"""
        QWidget {{
            background: {palette['base_bg']};
            color: {palette['text']};
            font-family: "Segoe UI";
            font-size: 13px;
        }}
        QLabel {{
            background: transparent;
        }}
        QMainWindow, QFrame#MainPanel {{
            background: {palette['base_bg']};
        }}
        QFrame#Sidebar {{
            background: {palette['surface_1']};
            border-right: 1px solid {palette['line']};
        }}
        QFrame#BrandShell {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 14px;
        }}
        QWidget#SidebarFooterCluster {{
            background: transparent;
        }}
        QFrame#SidebarThemeSwitcher {{
            background: {palette['theme_shell']};
            border: 1px solid {palette['theme_shell_border']};
            border-radius: 24px;
        }}
        QFrame#SidebarThemeTrack {{
            background: {palette['theme_track']};
            border: 1px solid {palette['theme_border']};
            border-radius: 20px;
        }}
        QPushButton#SidebarThemeButton {{
            min-width: 44px;
            max-width: 44px;
            min-height: 44px;
            max-height: 44px;
            padding: 0;
            border: 0;
            border-radius: 22px;
            background: transparent;
        }}
        QPushButton#SidebarThemeButton:hover {{
            background: {palette['theme_button_hover']};
            border: 0;
        }}
        QPushButton#SidebarThemeButton:pressed {{
            background: {palette['theme_button_pressed']};
            border: 0;
        }}
        QPushButton#SidebarThemeButton:checked {{
            background: transparent;
            border: 0;
        }}
        QPushButton#SidebarThemeButton:focus {{
            border: 1px solid {accent};
        }}
        QFrame#SidebarFooter {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 18px;
        }}
        QPushButton#SidebarFooterButton {{
            min-width: 46px;
            max-width: 46px;
            min-height: 46px;
            max-height: 46px;
            border-radius: 23px;
            padding: 0;
            background: {palette['surface_0']};
            border: 1px solid {palette['line_soft']};
        }}
        QPushButton#SidebarFooterButton:hover {{
            background: {palette['hover']};
            border: 1px solid {accent};
        }}
        QPushButton#SidebarFooterButton:pressed {{
            background: {palette['pressed']};
            border: 1px solid {accent};
        }}
        QPushButton#SidebarFooterButton:checked {{
            background: {palette['surface_0']};
            border: 1px solid {palette['line_soft']};
        }}
        QPushButton#SidebarFooterButton:focus {{
            border: 1px solid {accent};
        }}
        QFrame#LogoPill {{
            background: {palette['surface_0']};
            border: 1px solid {palette['line']};
            border-radius: 10px;
        }}
        QLabel#BrandTitle {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 0.3px;
        }}
        QLabel#SidebarBadge {{
            color: {palette['text_soft']};
            background: {palette['surface_0']};
            border: 1px solid {palette['line']};
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: 600;
        }}
        QLabel#PageTitle {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0.2px;
        }}
        QLabel#PageSubtitle {{
            font-size: 13px;
        }}
        QFrame#HeaderBar {{
            background: {palette['surface_1']};
            border-radius: 12px;
            border: 1px solid {palette['line']};
        }}
        QLabel#HeaderTitle {{
            font-size: 16px;
            font-weight: 700;
        }}
        QLabel#HeaderStatus {{
            color: {palette['text_soft']};
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 8px;
            padding: 4px 8px;
        }}
        QListWidget#NavList {{
            background: transparent;
            border: 0;
            padding: 2px;
            outline: 0;
        }}
        QListWidget#NavList::item {{
            min-height: 30px;
            padding: 10px 12px;
            border-radius: 9px;
            margin-bottom: 4px;
            color: {palette['text_soft']};
            background: transparent;
        }}
        QListWidget#NavList::item:hover {{
            background: {palette['hover']};
            color: {palette['text']};
        }}
        QListWidget#NavList::item:selected {{
            background: transparent;
            color: {palette['selected_text']};
            font-weight: 700;
        }}
        QFrame#NavIndicator {{
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.12);
            background: {accent_gradient_soft};
        }}
        QFrame#Card {{
            background: {palette['surface_1']};
            border-radius: 12px;
            border: 1px solid {palette['line']};
        }}
        QWidget#SettingsPageRoot {{
            background: transparent;
        }}
        QFrame#SettingsShell {{
            background: transparent;
            border: 0;
        }}
        QFrame#SettingsCategoryNav {{
            background: {palette['surface_2']};
            border-radius: 18px;
            border: 1px solid {palette['line']};
        }}
        QPushButton#SettingsCategoryButton {{
            text-align: left;
            min-height: 40px;
            padding: 9px 14px 9px 16px;
            border-radius: 12px;
            border: 1px solid transparent;
            border-left: 4px solid transparent;
            background: transparent;
            color: {palette['text_soft']};
            font-weight: 600;
        }}
        QPushButton#SettingsCategoryButton:hover {{
            background: {palette['hover']};
            color: {palette['text']};
            border-color: {palette['line_soft']};
        }}
        QPushButton#SettingsCategoryButton[selected="true"] {{
            background: {accent_soft};
            color: {palette['text']};
            font-weight: 700;
            border-color: {accent_border};
            border-left: 4px solid {accent};
        }}
        QPushButton#SettingsCategoryButton:focus {{
            border-color: {accent_border};
        }}
        QFrame#SettingsContentPanel {{
            background: {palette['surface_1']};
            border-radius: 22px;
            border: 1px solid {palette['line']};
        }}
        QStackedWidget#SettingsContentStack {{
            background: transparent;
            border: 0;
        }}
        QWidget#SettingsSubpage {{
            background: transparent;
        }}
        QLabel#SettingsSubpageTitle {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 0.15px;
        }}
        QLabel#SettingsSubpageSubtitle {{
            color: {palette['text_soft']};
            font-size: 12px;
            line-height: 1.35em;
        }}
        QFrame#SettingsHero {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {palette['surface_1']},
                stop:1 {palette['surface_2']}
            );
            border-radius: 22px;
            border: 1px solid {palette['line']};
        }}
        QLabel#SettingsHeroTitle {{
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 0.2px;
        }}
        QLabel#SettingsHeroSubtitle {{
            color: {palette['text_soft']};
            font-size: 13px;
            line-height: 1.35em;
        }}
        QWidget#SettingsStatusStrip {{
            background: transparent;
        }}
        QFrame#ProfileHero, QFrame#AboutHero {{
            background: {palette['surface_1']};
            border-radius: 18px;
            border: 1px solid {palette['line']};
        }}
        QLabel#ProfileAvatar {{
            color: #ffffff;
            background: {accent_gradient};
            border-radius: 29px;
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 0.5px;
        }}
        QLabel#AboutLogoMark {{
            color: #ffffff;
            background: {accent_gradient};
            border-radius: 32px;
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 0.5px;
        }}
        QLabel#ProfileName, QLabel#AboutTitle {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 0.2px;
        }}
        QLabel#AboutDescription {{
            color: {palette['text_soft']};
            font-size: 13px;
        }}
        QLabel#AboutVersionPill, QLabel#ProfileCurrentLabel {{
            color: {palette['text']};
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 10px;
            padding: 5px 10px;
            font-weight: 700;
        }}
        QLabel#CardTitle {{
            font-size: 14px;
            font-weight: 700;
        }}
        QFrame#SettingsCard {{
            background: {palette['surface_1']};
            border-radius: 18px;
            border: 1px solid {palette['line']};
        }}
        QLabel#SettingsCardTitle {{
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 0.1px;
        }}
        QLabel#SettingsCardSubtitle {{
            color: {palette['text_soft']};
            font-size: 12px;
        }}
        QFrame#SettingsRow {{
            background: transparent;
            border-bottom: 1px solid {palette['line_soft']};
            padding-bottom: 9px;
            margin-bottom: 1px;
        }}
        QLabel#SettingsLabel {{
            color: {palette['text']};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
        }}
        QLabel#SettingsDescription {{
            color: {palette['text_soft']};
            font-size: 12px;
            background: transparent;
        }}
        QLabel#SettingLabel {{
            color: {palette['text']};
            font-size: 13px;
            font-weight: 700;
            background: transparent;
        }}
        QLabel#SettingDescription {{
            color: {palette['text_soft']};
            font-size: 12px;
            background: transparent;
        }}
        QWidget#SettingInfo {{
            background: transparent;
        }}
        QPushButton {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 10px;
            padding: 9px 14px;
        }}
        QPushButton:hover {{
            background: {palette['hover']};
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background: {palette['pressed']};
        }}
        QPushButton#PrimaryButton {{
            background: {accent_gradient};
            color: #ffffff;
            font-weight: 700;
            border: 0;
        }}
        QPushButton#PrimaryButton:hover {{
            background: {accent_gradient};
            border: 0;
        }}
        QPushButton#PrimaryButton:pressed {{
            background: {accent_gradient};
            border: 0;
        }}
        QPushButton#SecondaryButton {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            font-weight: 700;
        }}
        QPushButton#SecondaryButton:hover {{
            background: {palette['hover']};
            border-color: {accent};
        }}
        QPushButton#GhostButton {{
            background: transparent;
            border: 1px solid {palette['line_soft']};
            color: {palette['text_soft']};
            font-weight: 600;
        }}
        QPushButton#GhostButton:hover {{
            background: {accent_soft};
            border-color: {accent_border};
            color: {palette['text']};
        }}
        QPushButton#DangerButton {{
            background: {danger_surface};
            border: 1px solid {_with_alpha(palette['danger'], 120 if settings.dark_mode else 90)};
            color: {palette['danger'] if not settings.dark_mode else '#ffd9d9'};
            font-weight: 700;
        }}
        QPushButton#DangerButton:hover {{
            background: {_with_alpha(palette['danger'], 54 if settings.dark_mode else 28)};
            border-color: {palette['danger']};
        }}
        QFrame#CollapsibleHeader {{
            background: transparent;
            border: 0;
        }}
        QWidget#CollapsibleBody, QWidget#DebugInlineOptions {{
            background: transparent;
            border: 0;
        }}
        QPushButton#SectionToggleButton {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line_soft']};
            border-radius: 8px;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton#SectionToggleButton:hover {{
            background: {palette['hover']};
            border-color: {accent};
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QListWidget, QTableWidget {{
            background: {palette['input_bg']};
            border: 1px solid {palette['line_soft']};
            border-radius: 10px;
            padding: 7px 8px;
            selection-background-color: {accent};
            selection-color: #071118;
        }}
        QLineEdit#PathInput {{
            background: {palette['input_bg_alt']};
            border-radius: 12px;
            padding: 8px 10px;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: {accent};
        }}
        QFrame#SegmentedControl {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 16px;
        }}
        QPushButton#SegmentedButton, QPushButton#SegmentedButtonSelected {{
            min-height: 32px;
            padding: 7px 14px;
            border-radius: 12px;
            border: 0;
            font-weight: 700;
        }}
        QPushButton#SegmentedButton {{
            background: transparent;
            color: {palette['text_soft']};
        }}
        QPushButton#SegmentedButton:hover {{
            background: {palette['hover']};
            color: {palette['text']};
        }}
        QPushButton#SegmentedButtonSelected {{
            background: {accent_gradient};
            color: #ffffff;
        }}
        QPushButton#ColorSwatch, QPushButton#ColorSwatchSelected {{
            background: transparent;
            border: 0;
            padding: 0;
        }}
        QCheckBox#ToggleSwitch {{
            background: transparent;
            border: 0;
            padding: 0;
            min-width: 54px;
            max-width: 54px;
            min-height: 30px;
            max-height: 30px;
        }}
        QLabel#StatusPill,
        QLabel#StatusPillAccent,
        QLabel#StatusPillSuccess,
        QLabel#StatusPillWarning,
        QLabel#StatusPillDanger {{
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid {palette['line']};
        }}
        QLabel#StatusPill {{
            color: {palette['text_soft']};
            background: {palette['surface_2']};
        }}
        QLabel#StatusPillAccent {{
            color: {palette['text'] if not settings.dark_mode else '#f8fbff'};
            background: {accent_soft};
            border: 1px solid {accent_border};
        }}
        QLabel#StatusPillSuccess {{
            color: {palette['success']};
            background: {success_surface};
            border: 1px solid {_with_alpha(palette['success'], 96 if settings.dark_mode else 82)};
        }}
        QLabel#StatusPillWarning {{
            color: {palette['warning']};
            background: {warning_surface};
            border: 1px solid {_with_alpha(palette['warning'], 96 if settings.dark_mode else 82)};
        }}
        QLabel#StatusPillDanger {{
            color: {palette['danger'] if not settings.dark_mode else '#ffd9d9'};
            background: {danger_surface};
            border: 1px solid {_with_alpha(palette['danger'], 96 if settings.dark_mode else 82)};
        }}
        QFrame#AccentPreviewPanel {{
            background: {palette['surface_2']};
            border: 1px solid {palette['line']};
            border-radius: 16px;
        }}
        QFrame#AccentPreviewStrip {{
            background: {accent_gradient};
            border-radius: 6px;
        }}
        QFrame#SettingsActionBar {{
            background: {palette['surface_1']};
            border-radius: 18px;
            border: 1px solid {palette['line']};
        }}
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
            background: transparent;
            border: 0;
        }}
        QHeaderView::section {{
            background: {palette['surface_2']};
            color: {palette['text_soft']};
            border: 0;
            border-bottom: 1px solid {palette['line']};
            padding: 7px 8px;
            font-weight: 600;
        }}
        QProgressBar {{
            border: 1px solid {palette['line_soft']};
            border-radius: 8px;
            text-align: center;
            background: {palette['input_bg_alt']};
            color: {palette['text_soft']};
            min-height: 18px;
        }}
        QProgressBar::chunk {{
            border-radius: 7px;
            background: {accent};
        }}
        QDialog#UpdateProgressDialog {{
            background: {palette['surface_1']};
            border: 1px solid {palette['line']};
            border-radius: 18px;
        }}
        QLabel#UpdateDialogTitle {{
            font-size: 16px;
            font-weight: 800;
        }}
        QLabel#UpdateDialogSubtitle {{
            color: {palette['text_soft']};
            font-size: 12px;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {palette['line']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QLabel[role="muted"] {{
            color: {palette['text_soft']};
            background: transparent;
        }}
        """
    )
