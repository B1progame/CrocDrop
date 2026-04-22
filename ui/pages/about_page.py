from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from ui.components.common import Card, PageHeader


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        root.addWidget(PageHeader("About CrocDrop", "A Windows-first transfer shell for the official croc backend."))

        card = Card("Project")
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "CrocDrop is a Windows-first desktop GUI for the official croc transfer tool.\n\n"
            "Backend engine: https://github.com/schollz/croc\n"
            "GUI stack: Python + PySide6\n\n"
            "UI author: B1progame\n\n"
            "License: MIT (see LICENSE file)\n"
            "Warranty: Provided AS IS, without warranty or liability.\n\n"
            "Security note:\n"
            "CrocDrop does not invent cryptographic guarantees. It relies on croc's protocol and behavior."
        )
        card.layout.addWidget(text)
        root.addWidget(card, 1)
