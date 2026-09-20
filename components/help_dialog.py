"""
help_dialog.py - Comprehensive Help, Keyboard Shortcuts, and About Dialog for Sticky Notes.
Provides in-app navigation guidance, markdown syntax reference, and diagnostic file paths.
Theme-adaptive with full WCAG contrast and Antigravity 2.0 dark palette support.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QWidget, QScrollArea,
    QGridLayout, QFrame, QLineEdit, QApplication
)
from PySide6.QtGui import QDesktopServices, QCursor, QFont

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
    from ..icons import get_themed_icon, get_icon
    from ..database import get_db_path
    from ..media_manager import get_attachments_dir
    from ..version import __version__, AUTHOR, LICENSE, HOMEPAGE
    from .update_dialog import UpdateDialog
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES
    from icons import get_themed_icon, get_icon
    from database import get_db_path
    from media_manager import get_attachments_dir
    from version import __version__, AUTHOR, LICENSE, HOMEPAGE, APP_NAME, APP_DESCRIPTION
    from components.update_dialog import UpdateDialog


class HelpAboutDialog(QDialog):
    """
    Modal Help and About center featuring keyboard shortcuts cheatsheet,
    markdown formatting guide, and application storage diagnostics.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Help & About (v{__version__})")
        self.resize(680, 560)
        self.setMinimumSize(560, 440)
        
        self.theme_mgr = get_theme_manager()
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Tab Widget
        self.tabs = QTabWidget(self)
        self._populate_tabs()
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

    def _populate_tabs(self):
        """Build or rebuild all 3 tabs with current theme colors."""
        self.tabs.clear()
        self.tabs.addTab(self._create_shortcuts_tab(), "Keyboard Shortcuts")
        self.tabs.addTab(self._create_markdown_tab(), "Markdown & Media")
        self.tabs.addTab(self._create_about_tab(), "About & Storage")

    def _create_shortcuts_tab(self) -> QWidget:
        """Tab 1: Visual Keyboard Shortcuts Cheatsheet."""
        theme = self.theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])
        is_dark = self.theme_mgr.is_dark_mode()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        intro = QLabel("Navigate, select, and organize your sticky notes with fluid keyboard shortcuts:")
        intro.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {pal['text_primary']};")
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

        if is_dark:
            badge_style = """
                background-color: rgba(138, 180, 248, 0.15);
                color: #8AB4F8;
                border: 1px solid rgba(138, 180, 248, 0.35);
                border-radius: 5px;
                padding: 3px 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-weight: 700;
                font-size: 11px;
            """
        elif theme == "sepia":
            badge_style = """
                background-color: rgba(140, 90, 43, 0.12);
                color: #8C5A2B;
                border: 1px solid rgba(140, 90, 43, 0.35);
                border-radius: 5px;
                padding: 3px 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-weight: 700;
                font-size: 11px;
            """
        else:
            badge_style = """
                background-color: rgba(37, 99, 235, 0.10);
                color: #2563EB;
                border: 1px solid rgba(37, 99, 235, 0.35);
                border-radius: 5px;
                padding: 3px 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-weight: 700;
                font-size: 11px;
            """

        for section_title, items in shortcuts:
            sec_lbl = QLabel(section_title)
            sec_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {pal['accent']}; margin-top: 6px;")
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
                badge.setStyleSheet(badge_style)

                desc_lbl = QLabel(desc)
                desc_lbl.setStyleSheet(f"font-size: 12px; color: {pal['text_primary']};")

                grid.addWidget(badge, row, 0, Qt.AlignmentFlag.AlignLeft)
                grid.addWidget(desc_lbl, row, 1, Qt.AlignmentFlag.AlignLeft)

            grid.setColumnStretch(1, 1)
            layout.addLayout(grid)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_markdown_tab(self) -> QWidget:
        """Tab 2: Markdown & Media Attachments Guide."""
        theme = self.theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

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
            t_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {pal['text_primary']}; margin-top: 4px;")
            layout.addWidget(t_lbl)

            syn_box = QLabel(syntax)
            syn_box.setStyleSheet(f"""
                background-color: {pal['bg_main']};
                color: {pal['text_primary']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
            """)
            syn_box.setWordWrap(True)
            layout.addWidget(syn_box)

            n_lbl = QLabel(notes)
            n_lbl.setStyleSheet(f"font-size: 12px; color: {pal['text_secondary']}; margin-bottom: 4px;")
            n_lbl.setWordWrap(True)
            layout.addWidget(n_lbl)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_about_tab(self) -> QWidget:
        """Tab 3: App metadata and storage directory paths with scroll area and copyable inputs."""
        theme = self.theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel(f"{APP_NAME} v{__version__}")
        title.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {pal['accent']};")
        layout.addWidget(title)

        subtitle = QLabel(APP_DESCRIPTION)
        subtitle.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {pal['text_secondary']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        info_box = QFrame()
        info_box.setStyleSheet(f"""
            QFrame {{
                background-color: {pal['bg_main']};
                border: 1px solid {pal['border']};
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(12)

        db_path = str(get_db_path().resolve())
        attach_path = str(get_attachments_dir().resolve())

        # Metadata info
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(20)
        lbl_author = QLabel(f"<span style='color: {pal['text_primary']};'><b>Author:</b> {AUTHOR}</span>")
        lbl_license = QLabel(f"<span style='color: {pal['text_primary']};'><b>License:</b> {LICENSE}</span>")
        meta_layout.addWidget(lbl_author)
        meta_layout.addWidget(lbl_license)
        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        # Helper for copyable, clickable path entries
        def _make_path_entry(label_text: str, path_val: str, is_dir: bool = False):
            vbox = QVBoxLayout()
            vbox.setSpacing(4)
            lbl = QLabel(f"<span style='color: {pal['text_primary']}; font-weight: 700; font-size: 12px;'>{label_text}</span>")
            vbox.addWidget(lbl)

            row = QHBoxLayout()
            row.setSpacing(6)

            line_edit = QLineEdit(path_val)
            line_edit.setReadOnly(True)
            line_edit.setCursorPosition(0)
            line_edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {pal['input_bg']};
                    color: {pal['text_primary']};
                    border: 1px solid {pal['border']};
                    border-radius: 6px;
                    padding: 5px 8px;
                    font-family: 'Cascadia Code', 'Consolas', monospace;
                    font-size: 11px;
                }}
            """)
            row.addWidget(line_edit, 1)

            copy_btn = QPushButton("📋 Copy")
            copy_btn.setObjectName("SelectModeButton")
            copy_btn.setToolTip("Copy path to clipboard")
            copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            def _on_copy(p=path_val, btn=copy_btn):
                QApplication.clipboard().setText(p)
                btn.setText("✓ Copied!")
                QTimer.singleShot(1500, lambda: btn.setText("📋 Copy"))
            copy_btn.clicked.connect(_on_copy)
            row.addWidget(copy_btn)

            open_btn = QPushButton("📂 Open")
            open_btn.setObjectName("SelectModeButton")
            open_btn.setToolTip("Open folder in Windows Explorer")
            open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            folder_target = path_val if is_dir else str(Path(path_val).parent)
            open_btn.clicked.connect(lambda _, f=folder_target: QDesktopServices.openUrl(QUrl.fromLocalFile(f)))
            row.addWidget(open_btn)

            vbox.addLayout(row)
            return vbox

        info_layout.addLayout(_make_path_entry("Database SQLite File:", db_path, is_dir=False))
        info_layout.addLayout(_make_path_entry("Attachments Vault Directory:", attach_path, is_dir=True))

        layout.addWidget(info_box)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        github_btn = QPushButton(" GitHub Repository", self)
        github_btn.setIcon(get_themed_icon("external_link", role="btn_text", theme=theme, size=16))
        github_btn.setObjectName("SelectModeButton")
        github_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(HOMEPAGE)))
        btn_layout.addWidget(github_btn)

        update_btn = QPushButton(" Check for Updates...", self)
        update_btn.setIcon(get_themed_icon("clock", role="btn_text", theme=theme, size=16))
        update_btn.setObjectName("SelectModeButton")
        update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        update_btn.clicked.connect(self._open_update_dialog)
        btn_layout.addWidget(update_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _open_update_dialog(self):
        """Displays the Software Update Center."""
        dialog = UpdateDialog(self, auto_check=True)
        dialog.exec()

    def _update_tab_icons(self):
        theme = self.theme_mgr.current_theme
        self.tabs.setTabIcon(0, get_themed_icon("keyboard", role="primary", theme=theme, size=16))
        self.tabs.setTabIcon(1, get_themed_icon("edit", role="primary", theme=theme, size=16))
        self.tabs.setTabIcon(2, get_themed_icon("info", role="primary", theme=theme, size=16))

    def _on_theme_changed(self, new_theme: str):
        current_tab = self.tabs.currentIndex()
        self._populate_tabs()
        if current_tab >= 0:
            self.tabs.setCurrentIndex(current_tab)
        self._update_tab_icons()
