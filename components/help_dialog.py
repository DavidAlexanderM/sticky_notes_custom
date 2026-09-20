"""
help_dialog.py - Comprehensive Help, Keyboard Shortcuts, and About Dialog for Sticky Notes.
Provides in-app navigation guidance, markdown syntax reference, and diagnostic file paths.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QWidget, QScrollArea,
    QGridLayout, QFrame
)
from PySide6.QtGui import QDesktopServices, QCursor, QFont

try:
    from ..theme_manager import get_theme_manager
    from ..icons import get_themed_icon, get_icon
    from ..database import get_db_path
    from ..media_manager import get_attachments_dir
    from ..version import __version__, AUTHOR, LICENSE, HOMEPAGE
except ImportError:
    from theme_manager import get_theme_manager
    from icons import get_themed_icon, get_icon
    from database import get_db_path
    from media_manager import get_attachments_dir
    from version import __version__, AUTHOR, LICENSE, HOMEPAGE


class HelpAboutDialog(QDialog):
    """
    Modal Help and About center featuring keyboard shortcuts cheatsheet,
    markdown formatting guide, and application storage diagnostics.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sticky Notes - Help & About (v{__version__})")
        self.resize(640, 520)
        self.setMinimumSize(540, 420)
        
        self.theme_mgr = get_theme_manager()
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Tab Widget
        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._create_shortcuts_tab(), "Keyboard Shortcuts")
        self.tabs.addTab(self._create_markdown_tab(), "Markdown & Media")
        self.tabs.addTab(self._create_about_tab(), "About & Storage")
        layout.addWidget(self.tabs, 1)

        # Bottom row (Close button)
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        
        self.close_btn = QPushButton("Close", self)
        self.close_btn.setObjectName("SelectModeButton")
        self.close_btn.setFixedSize(90, 32)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(self.close_btn)

        layout.addLayout(bottom_row)

        self._update_tab_icons()

    def _create_shortcuts_tab(self) -> QWidget:
        """Tab 1: Visual Keyboard Shortcuts Cheatsheet."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        intro = QLabel("Navigate, select, and organize your sticky notes with fluid keyboard shortcuts:")
        intro.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(intro)

        shortcuts = [
            ("Selection & Navigation", [
                ("Shift + Click", "Extend range selection from last selected note"),
                ("Ctrl + Click", "Toggle individual note selection in a group"),
                ("↑  ↓  ←  →", "Navigate and focus note cards across the grid"),
                ("Shift + Arrows", "Expand or shrink selection range via keyboard"),
                ("Enter / Return", "Open currently focused note in full editor"),
                ("Delete / Backspace", "Delete selected note(s) with confirmation"),
                ("Ctrl + A", "Select all notes currently visible in the grid"),
                ("Escape", "Clear active selection or cancel operation"),
            ]),
            ("App Actions", [
                ("Ctrl + N", "Create a new blank sticky note"),
                ("Ctrl + F", "Jump focus directly to search bar"),
                ("F1 / Ctrl + H", "Open this Help & Keyboard Shortcuts guide"),
            ]),
            ("Writing & Formatting (Editor)", [
                ("Ctrl + B", "Toggle **Bold** syntax"),
                ("Ctrl + I", "Toggle *Italic* syntax"),
                ("Ctrl + U", "Toggle <u>Underline</u> syntax"),
                ("Ctrl + K", "Insert or wrap selection with a hyperlink"),
                ("Drag & Drop", "Drop images, audio, or video files straight into note"),
            ])
        ]

        for section_title, items in shortcuts:
            sec_lbl = QLabel(section_title)
            sec_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #2563EB; margin-top: 6px;")
            layout.addWidget(sec_lbl)

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(8)
            grid.setContentsMargins(4, 0, 4, 6)

            for row, (key_combo, desc) in enumerate(items):
                badge = QLabel(key_combo)
                badge.setProperty("class", "KbdBadge")
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setMinimumWidth(130)
                badge.setStyleSheet("""
                    background-color: rgba(37, 99, 235, 0.10);
                    color: #2563EB;
                    border: 1px solid rgba(37, 99, 235, 0.35);
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-family: 'Cascadia Code', 'Consolas', monospace;
                    font-weight: 700;
                    font-size: 11px;
                """)

                desc_lbl = QLabel(desc)
                desc_lbl.setStyleSheet("font-size: 12px;")

                grid.addWidget(badge, row, 0, Qt.AlignmentFlag.AlignLeft)
                grid.addWidget(desc_lbl, row, 1, Qt.AlignmentFlag.AlignLeft)

            grid.setColumnStretch(1, 1)
            layout.addLayout(grid)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_markdown_tab(self) -> QWidget:
        """Tab 2: Markdown & Media Attachments Guide."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        sections = [
            ("Headings", "# Heading 1\n## Heading 2\n### Heading 3", "Creates crisp hierarchical headings with visual divider lines."),
            ("Bold & Italic", "**Bold text** or __Bold__\n*Italic text* or _Italic_\n~~Strikethrough~~", "Emphasizes important phrases inline."),
            ("Interactive Task Lists", "- [ ] Incomplete task item\n- [x] Completed task item", "Rendered as interactive clickable checkboxes in preview."),
            ("Code & Snippets", "`inline_code()`\n\n```python\ndef greet():\n    return 'Hello World'\n```", "Styled in monospace font with subtle tinted code blocks."),
            ("Drag & Drop Media", "Drag images, voice memos, or video clips directly from Windows Explorer into the editor.", "Files are automatically copied into the local attachment vault without altering your originals."),
            ("Audio Playback", "🎵 [Play Voice Note: audio.m4a](file:///...)", "Click audio links to launch the integrated in-app player bar with position scrubbing.")
        ]

        for title, syntax, notes in sections:
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 13px; font-weight: 700; margin-top: 4px;")
            layout.addWidget(t_lbl)

            syn_box = QLabel(syntax)
            syn_box.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
            """)
            syn_box.setWordWrap(True)
            layout.addWidget(syn_box)

            n_lbl = QLabel(notes)
            n_lbl.setStyleSheet("font-size: 12px; color: #64748B; margin-bottom: 4px;")
            n_lbl.setWordWrap(True)
            layout.addWidget(n_lbl)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_about_tab(self) -> QWidget:
        """Tab 3: App metadata and storage directory paths."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel(f"Sticky Notes v{__version__}")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #2563EB;")
        layout.addWidget(title)

        subtitle = QLabel("Minimal Single-Window Markdown Desktop App with Offline Local Storage.")
        subtitle.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(subtitle)

        info_box = QFrame()
        info_box.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.03);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(6)

        db_path = str(get_db_path().resolve())
        attach_path = str(get_attachments_dir().resolve())

        info_layout.addWidget(QLabel(f"<b>Author:</b> {AUTHOR}"))
        info_layout.addWidget(QLabel(f"<b>License:</b> {LICENSE}"))
        info_layout.addWidget(QLabel(f"<b>Database File:</b> <span style='font-family: monospace;'>{db_path}</span>"))
        info_layout.addWidget(QLabel(f"<b>Attachments Folder:</b> <span style='font-family: monospace;'>{attach_path}</span>"))
        layout.addWidget(info_box)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        open_folder_btn = QPushButton(" Open Attachments Folder", self)
        open_folder_btn.setIcon(get_themed_icon("folder", role="btn_text", size=16))
        open_folder_btn.setObjectName("SelectModeButton")
        open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(attach_path)))
        btn_layout.addWidget(open_folder_btn)

        github_btn = QPushButton(" GitHub Repository", self)
        github_btn.setIcon(get_themed_icon("external_link", role="btn_text", size=16))
        github_btn.setObjectName("SelectModeButton")
        github_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(HOMEPAGE)))
        btn_layout.addWidget(github_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        return container

    def _update_tab_icons(self):
        theme = self.theme_mgr.current_theme
        self.tabs.setTabIcon(0, get_themed_icon("keyboard", role="primary", theme=theme, size=16))
        self.tabs.setTabIcon(1, get_themed_icon("edit", role="primary", theme=theme, size=16))
        self.tabs.setTabIcon(2, get_themed_icon("info", role="primary", theme=theme, size=16))

    def _on_theme_changed(self, new_theme: str):
        self._update_tab_icons()
