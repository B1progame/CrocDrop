from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication

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
            "danger": "#ff6f6f",
            "theme_shell": "rgba(28, 39, 57, 0.78)",
            "theme_shell_border": "rgba(166, 186, 214, 0.12)",
            "theme_track": "rgba(10, 15, 24, 0.88)",
            "theme_border": "rgba(166, 186, 214, 0.10)",
            "theme_button_hover": "rgba(255, 255, 255, 0.045)",
            "theme_button_pressed": "rgba(255, 255, 255, 0.07)",
        }
        accent_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f2a90, stop:0.55 #8c45ff, stop:1 #f58bc6)"
        accent_gradient_soft = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(79,42,144,140), stop:1 rgba(245,139,198,140))"
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
            "danger": "#c23d3d",
            "theme_shell": "rgba(255, 255, 255, 0.96)",
            "theme_shell_border": "rgba(124, 144, 168, 0.16)",
            "theme_track": "rgba(244, 247, 252, 0.96)",
            "theme_border": "rgba(124, 144, 168, 0.12)",
            "theme_button_hover": "rgba(89, 108, 132, 0.08)",
            "theme_button_pressed": "rgba(89, 108, 132, 0.12)",
        }
        accent_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6a45cc, stop:0.6 #9b5cff, stop:1 #e873b4)"
        accent_gradient_soft = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(106,69,204,90), stop:1 rgba(232,115,180,90))"

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
            border-radius: 8px;
            padding: 8px 12px;
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
            border-radius: 8px;
            padding: 6px;
            selection-background-color: {accent};
            selection-color: #071118;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: {accent};
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
