from __future__ import annotations

from models.settings import AppSettings


def apply_theme(app, settings: AppSettings) -> None:
    accent = settings.accent_color or "#35c9a5"
    if settings.dark_mode:
        base_bg = "#0f1115"
        panel_bg = "#171a21"
        card_bg = "#1c212b"
        text = "#e7ecf3"
        subtext = "#9aa8bd"
    else:
        base_bg = "#f2f5f8"
        panel_bg = "#ffffff"
        card_bg = "#ffffff"
        text = "#17202b"
        subtext = "#526172"

    app.setStyleSheet(
        f"""
        QWidget {{
            background: {base_bg};
            color: {text};
            font-family: 'Segoe UI';
            font-size: 13px;
        }}
        QMainWindow, QFrame#MainPanel {{
            background: {base_bg};
        }}
        QFrame#Sidebar {{
            background: {panel_bg};
            border-right: 1px solid #2a3140;
        }}
        QFrame#BrandShell {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(42, 55, 75, 0.9), stop:1 rgba(20, 27, 38, 0.9));
            border: 1px solid #2b3d52;
            border-radius: 16px;
        }}
        QLabel#BrandTitle {{
            font-size: 23px;
            font-weight: 800;
            letter-spacing: 0.4px;
        }}
        QListWidget#NavList {{
            background: transparent;
            border: 0;
            padding: 8px;
            outline: 0;
        }}
        QListWidget#NavList::item {{
            padding: 10px 12px;
            border-radius: 8px;
            margin-bottom: 4px;
        }}
        QListWidget#NavList::item:selected {{
            background: {accent};
            color: #0d1218;
            font-weight: 700;
        }}
        QFrame#Card {{
            background: {card_bg};
            border-radius: 12px;
            border: 1px solid #263042;
        }}
        QPushButton {{
            background: #253247;
            border: 1px solid #314159;
            border-radius: 8px;
            padding: 8px 12px;
        }}
        QPushButton:hover {{
            border-color: {accent};
        }}
        QPushButton#PrimaryButton {{
            background: {accent};
            color: #091015;
            font-weight: 700;
            border: 0;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {{
            background: #111722;
            border: 1px solid #2d3b54;
            border-radius: 8px;
            padding: 6px;
        }}
        QTableWidget {{
            background: #111722;
            border: 1px solid #29344a;
            gridline-color: #253044;
        }}
        QLabel[role="muted"] {{ color: {subtext}; }}
        """
    )
