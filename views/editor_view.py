import os
import sys
import subprocess
import re
import uuid
import time
from datetime import datetime
from pathlib import Path
import markdown2
from PySide6.QtCore import Qt, Signal, QTimer, QUrl, QRect, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QTextBrowser, QPushButton,
    QFrame, QSplitter, QMessageBox, QFileDialog, QMenu, QApplication, QSlider, QDialog
)
from PySide6.QtGui import QCursor, QDesktopServices, QGuiApplication, QPainter, QPen, QColor, QPixmap, QTextCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
try:
    from ..components.color_picker_flyout import ColorPickerFlyout
    from ..components.format_toolbar import FormatToolbar
    from ..components.voice_recorder_dialog import VoiceRecorderDialog
    from ..components.screen_recorder_dialog import ScreenRecorderDialog, RecordingCompleteDialog
    from ..components.help_dialog import HelpAboutDialog
    from ..components.share_dialog import ShareNoteDialog
    from ..media_manager import copy_to_attachments, get_attachments_dir
    from ..styles import MARKDOWN_PREVIEW_CSS, is_dark_color, get_markdown_preview_css, THEME_PALETTES
    from ..security import is_safe_url, sanitize_markdown_html
    from ..theme_manager import get_theme_manager
    from ..icons import get_themed_icon
    from ..markdown_highlighter import MarkdownHighlighter
    from ..components.tag_selector_flyout import TagSelectorFlyout
    from ..i18n import tr, get_translation_manager
    from ..proofing_engine import get_proofing_engine
    from .. import database
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from components.format_toolbar import FormatToolbar
    from components.voice_recorder_dialog import VoiceRecorderDialog
    from components.screen_recorder_dialog import ScreenRecorderDialog, RecordingCompleteDialog
    from components.help_dialog import HelpAboutDialog
    from components.share_dialog import ShareNoteDialog
    from components.tag_selector_flyout import TagSelectorFlyout
    from i18n import tr, get_translation_manager
    from media_manager import copy_to_attachments, get_attachments_dir
    from styles import MARKDOWN_PREVIEW_CSS, is_dark_color, get_markdown_preview_css, THEME_PALETTES
    from security import is_safe_url, sanitize_markdown_html
    from theme_manager import get_theme_manager
    from icons import get_themed_icon
    from markdown_highlighter import MarkdownHighlighter
    from proofing_engine import get_proofing_engine
    import database


class MarkdownTextEdit(QTextEdit):
    """
    Enhanced QTextEdit supporting Drag & Drop of image, audio, and video files.
    """
    media_dropped = Signal(str, str)  # (media_type, local_file_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def is_supported_media_mime(self, mime_data) -> bool:
        """Returns True if mime data contains supported local media file URLs."""
        if mime_data and mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    suffix = Path(url.toLocalFile()).suffix.lower()
                    if suffix in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
                                  '.wav', '.m4a', '.mp3', '.ogg', '.flac', '.aac',
                                  '.mp4', '.webm', '.mov', '.mkv', '.avi'):
                        return True
        return False

    def dragEnterEvent(self, event):
        if self.is_supported_media_mime(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            handled = False
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    suffix = Path(local_path).suffix.lower()
                    if suffix in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'):
                        self.media_dropped.emit("image", local_path)
                        handled = True
                    elif suffix in ('.wav', '.m4a', '.mp3', '.ogg', '.flac', '.aac'):
                        self.media_dropped.emit("audio", local_path)
                        handled = True
                    elif suffix in ('.mp4', '.webm', '.mov', '.mkv', '.avi'):
                        self.media_dropped.emit("video", local_path)
                        handled = True
            if handled:
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def contextMenuEvent(self, event):
        """Displays spell checking suggestions, personal dictionary actions, or standard edit actions."""
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        raw_word = cursor.selectedText()
        word = raw_word.strip().strip("'\"`.,!?:;()[]{}*~_#")

        engine = get_proofing_engine()

        if engine.is_enabled and word and engine.is_misspelled(word):
            menu = QMenu(self)

            # Top spelling suggestions
            suggs = engine.get_suggestions(word, max_candidates=5)
            if suggs:
                for sugg in suggs:
                    action = menu.addAction(f"💡 {sugg}")
                    def _make_replace(s=sugg, cur=QTextCursor(cursor)):
                        return lambda: (cur.insertText(s), self.setTextCursor(cur))
                    action.triggered.connect(_make_replace())
            else:
                disabled_act = menu.addAction(f"({tr('no_spelling_suggestions')})")
                disabled_act.setEnabled(False)

            menu.addSeparator()

            # Add to personal dictionary
            def _add_to_dict():
                engine.add_to_personal_dictionary(word)
            add_act = menu.addAction(f"➕ {tr('add_to_dictionary')}")
            add_act.triggered.connect(_add_to_dict)

            # Ignore for this session
            def _ignore():
                engine.ignore_word(word)
            ignore_act = menu.addAction(f"🚫 {tr('ignore_word')}")
            ignore_act.triggered.connect(_ignore)

            menu.addSeparator()

            # Standard context menu actions
            std_menu = self.createStandardContextMenu()
            for a in std_menu.actions():
                menu.addAction(a)

            menu.exec(event.globalPos())
            return

        super().contextMenuEvent(event)



class SnippingOverlay(QDialog):
    """
    Interactive full-screen desktop snipping tool overlay.
    Darkens the desktop and lets the user click-and-drag to select a region.
    Pressing Enter captures full screen; Esc cancels.
    """
    def __init__(self, full_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.full_pixmap = full_pixmap
        self.result_pixmap = None
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setWindowState(Qt.WindowState.WindowFullScreen)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._current_pos = event.pos()
            rect = QRect(self._start_pos, self._current_pos).normalized()
            if rect.width() >= 8 and rect.height() >= 8:
                dpr = self.full_pixmap.devicePixelRatio()
                crop_rect = QRect(
                    int(rect.x() * dpr),
                    int(rect.y() * dpr),
                    int(rect.width() * dpr),
                    int(rect.height() * dpr)
                )
                self.result_pixmap = self.full_pixmap.copy(crop_rect)
                self.accept()
            else:
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.result_pixmap = self.full_pixmap
            self.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.full_pixmap)

        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        if self._start_pos and self._current_pos:
            rect = QRect(self._start_pos, self._current_pos).normalized()
            if rect.width() > 0 and rect.height() > 0:
                dpr = self.full_pixmap.devicePixelRatio()
                src_rect = QRect(
                    int(rect.x() * dpr),
                    int(rect.y() * dpr),
                    int(rect.width() * dpr),
                    int(rect.height() * dpr)
                )
                painter.drawPixmap(rect, self.full_pixmap, src_rect)

                # Accent border around selection
                painter.setPen(QPen(QColor(0, 120, 215), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect)

                # Dimensions badge
                badge_text = f"{rect.width()} × {rect.height()} px"
                painter.setPen(QColor(255, 255, 255))
                painter.setBrush(QColor(0, 0, 0, 180))
                badge_rect = QRect(rect.x(), max(0, rect.y() - 24), 100, 20)
                painter.drawRoundedRect(badge_rect, 3, 3)
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)


class NoteEditorView(QWidget):
    """
    Minimal note editor with Markdown support, live preview, and return arrow.
    """
    back_requested = Signal()  # Emits when the back arrow is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EditorViewContainer")
        self.current_note_id = None
        self.current_color_hex = "#FFF9C4"
        self.current_project_id = "default"

        # Timer for debounced auto-save
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(600)  # Save after 600ms of inactivity
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self._auto_save)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Back Navigation Arrow Button
        self.back_btn = QPushButton(self)
        self.back_btn.setObjectName("BackButton")
        self.back_btn.setToolTip("Return to Notes (Esc)")
        self.back_btn.setFixedSize(38, 34)
        self.back_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.back_btn.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self.back_btn)

        # Title Input Field
        self.title_input = QLineEdit(self)
        self.title_input.setObjectName("NoteTitleInput")
        self.title_input.setPlaceholderText("Title")
        self.title_input.textChanged.connect(self._on_content_changed)
        header_layout.addWidget(self.title_input, 1)

        # Project Stack Badge & Switcher Button
        self.project_badge_btn = QPushButton(self)
        self.project_badge_btn.setObjectName("EditorProjectBtn")
        self.project_badge_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.project_badge_btn.setToolTip("Click to change project stack")
        self.project_badge_btn.clicked.connect(self._show_editor_project_menu)
        header_layout.addWidget(self.project_badge_btn)

        # Color Indicator & Selector Button
        self.color_badge = QPushButton(self)
        self.color_badge.setFixedSize(28, 28)
        self.color_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.color_badge.setToolTip("Change Note Color")
        self.color_badge.clicked.connect(self._open_color_picker)
        header_layout.addWidget(self.color_badge)

        # Tags Flyout Button
        self.tags_btn = QPushButton(self)
        self.tags_btn.setObjectName("EditorHeaderBtn")
        self.tags_btn.setFixedSize(36, 34)
        self.tags_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tags_btn.setToolTip(tr("manage_tags", "Manage Tags"))
        self.tags_btn.clicked.connect(self._open_tags_flyout)
        header_layout.addWidget(self.tags_btn)

        # Mode Selector Buttons [Edit | Split | Preview]
        mode_frame = QFrame(self)
        mode_frame.setObjectName("ModeSelectorFrame")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)

        self.btn_edit = QPushButton("Edit", mode_frame)
        self.btn_edit.setObjectName("ModeTabButton")
        self.btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_edit.clicked.connect(lambda: self.set_view_mode("edit"))

        self.btn_split = QPushButton("Split", mode_frame)
        self.btn_split.setObjectName("ModeTabButton")
        self.btn_split.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_split.clicked.connect(lambda: self.set_view_mode("split"))

        self.btn_preview = QPushButton("Preview", mode_frame)
        self.btn_preview.setObjectName("ModeTabButton")
        self.btn_preview.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_preview.clicked.connect(lambda: self.set_view_mode("preview"))

        mode_layout.addWidget(self.btn_edit)
        mode_layout.addWidget(self.btn_split)
        mode_layout.addWidget(self.btn_preview)
        header_layout.addWidget(mode_frame)

        # Quick Action Buttons (Duplicate & Share)
        self.dup_btn = QPushButton(self)
        self.dup_btn.setObjectName("EditorHeaderBtn")
        self.dup_btn.setToolTip("Duplicate Note")
        self.dup_btn.setFixedSize(36, 34)
        self.dup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dup_btn.clicked.connect(self._duplicate_current_note)
        header_layout.addWidget(self.dup_btn)

        self.share_btn = QPushButton(self)
        self.share_btn.setObjectName("EditorHeaderBtn")
        self.share_btn.setToolTip("Share / Export Note")
        self.share_btn.setFixedSize(36, 34)
        self.share_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.share_btn.clicked.connect(self._share_current_note)
        header_layout.addWidget(self.share_btn)

        # Help & Shortcuts Button (❓)
        self.help_btn = QPushButton(self)
        self.help_btn.setObjectName("EditorHeaderBtn")
        self.help_btn.setFixedSize(36, 34)
        self.help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.help_btn.setToolTip("Help & Keyboard Shortcuts (F1)")
        self.help_btn.clicked.connect(self._open_help_dialog)
        header_layout.addWidget(self.help_btn)

        # Theme Switcher Button (Sun / Moon)
        self.theme_mgr = get_theme_manager()
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("EditorHeaderBtn")
        self.theme_btn.setFixedSize(36, 34)
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.setToolTip("Toggle Light / Dark Theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_btn.customContextMenuRequested.connect(self._show_theme_context_menu)
        header_layout.addWidget(self.theme_btn)

        main_layout.addLayout(header_layout)

        # Dedicated Tags Bar beneath header
        self.tags_bar_widget = QWidget(self)
        self.tags_bar_widget.setObjectName("EditorTagsBar")
        self.tags_bar_layout = QHBoxLayout(self.tags_bar_widget)
        self.tags_bar_layout.setContentsMargins(4, 0, 4, 2)
        self.tags_bar_layout.setSpacing(6)
        main_layout.addWidget(self.tags_bar_widget)

        # Editor & Preview Splitter Area
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(0, 0, 0, 0.06);
                border-radius: 3px;
                margin: 4px 1px;
            }
            QSplitter::handle:hover {
                background-color: #0067C0;
            }
        """)

        # Raw Markdown Text Editor with Drag & Drop
        self.editor = MarkdownTextEdit(self.splitter)
        self.editor.setObjectName("MarkdownEditor")
        self.editor.setPlaceholderText("Write your note here in Markdown...\n\n# Heading\n- Bullet item\n**Bold text**\n`code`")
        self.editor.textChanged.connect(self._on_content_changed)
        self.editor.media_dropped.connect(self._on_media_dropped)

        # Attach Live In-Editor Markdown Highlighter
        self.highlighter = MarkdownHighlighter(self.editor.document(), theme=self.theme_mgr.current_theme)

        # Rendered Markdown Browser
        self.preview = QTextBrowser(self.splitter)
        self.preview.setObjectName("MarkdownPreview")
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self._on_anchor_clicked)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)

        # Formatting & Media Toolbar
        self.format_toolbar = FormatToolbar(self.editor, self)
        self.format_toolbar.add_picture_requested.connect(self._on_add_picture)
        self.format_toolbar.add_audio_requested.connect(self._on_add_audio)
        self.format_toolbar.add_video_requested.connect(self._on_add_video)
        self.format_toolbar.record_screen_requested.connect(self._on_record_screen)
        self.format_toolbar.screen_capture_requested.connect(self._on_screen_capture)
        self.format_toolbar.attach_audio_requested.connect(self._on_attach_audio_file)
        self.format_toolbar.open_attachments_requested.connect(self._open_attachments_folder)
        main_layout.addWidget(self.format_toolbar)

        main_layout.addWidget(self.splitter, 1)

        # In-App Audio Player Bar (Hidden by default, shown when playing audio)
        self.audio_player_frame = QFrame(self)
        self.audio_player_frame.setObjectName("AudioPlayerFrame")
        self.audio_player_frame.setVisible(False)
        player_layout = QHBoxLayout(self.audio_player_frame)
        player_layout.setContentsMargins(12, 6, 12, 6)
        player_layout.setSpacing(10)

        self.play_pause_btn = QPushButton(self.audio_player_frame)
        self.play_pause_btn.setFixedSize(32, 30)
        self.play_pause_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.play_pause_btn.clicked.connect(self._toggle_audio_playback)
        player_layout.addWidget(self.play_pause_btn)

        self.audio_title_label = QLabel("Audio", self.audio_player_frame)
        self.audio_title_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        player_layout.addWidget(self.audio_title_label)

        self.audio_slider = QSlider(Qt.Orientation.Horizontal, self.audio_player_frame)
        self.audio_slider.setRange(0, 0)
        self.audio_slider.sliderMoved.connect(self._on_seek_audio)
        player_layout.addWidget(self.audio_slider, 1)

        self.audio_time_label = QLabel("00:00 / 00:00", self.audio_player_frame)
        self.audio_time_label.setObjectName("AudioTimeLabel")
        player_layout.addWidget(self.audio_time_label)

        self.external_play_btn = QPushButton(self.audio_player_frame)
        self.external_play_btn.setToolTip("Open in external media player")
        self.external_play_btn.setFixedSize(30, 28)
        self.external_play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.external_play_btn.clicked.connect(self._open_audio_externally)
        player_layout.addWidget(self.external_play_btn)

        self.close_player_btn = QPushButton(self.audio_player_frame)
        self.close_player_btn.setToolTip("Close Player")
        self.close_player_btn.setFixedSize(28, 28)
        self.close_player_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_player_btn.clicked.connect(self._stop_and_hide_audio_player)
        player_layout.addWidget(self.close_player_btn)

        main_layout.addWidget(self.audio_player_frame)

        # QMediaPlayer setup
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.positionChanged.connect(self._on_player_position_changed)
        self.media_player.durationChanged.connect(self._on_player_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_player_state_changed)
        self._current_audio_url = None

        self._update_header_icons()
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)

        self.i18n = get_translation_manager()
        self.i18n.language_changed.connect(self._apply_language_change)
        self._apply_language_change()

        # Default Mode is Split View
        self.set_view_mode("split")

    def load_note(self, note_id: str):
        """Loads a note by ID into the editor."""
        self._stop_and_hide_audio_player()
        self.current_note_id = note_id
        note = database.get_note(note_id)
        if not note:
            return

        self.title_input.blockSignals(True)
        self.editor.blockSignals(True)

        self.title_input.setText(note.get("title", ""))
        self.editor.setPlainText(note.get("content", ""))
        self.current_color_hex = note.get("color_hex", "#FFF9C4")
        self.current_project_id = note.get("project_id", "default")
        self._update_color_badge()
        self._update_editor_project_btn()
        self._refresh_tags_bar()

        self.title_input.blockSignals(False)
        self.editor.blockSignals(False)

        self._render_markdown()
        self.editor.setFocus()

    def set_view_mode(self, mode: str):
        """Switches between 'edit', 'split', and 'preview' view modes."""
        self.btn_edit.setProperty("active", mode == "edit")
        self.btn_split.setProperty("active", mode == "split")
        self.btn_preview.setProperty("active", mode == "preview")

        for btn in [self.btn_edit, self.btn_split, self.btn_preview]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "edit":
            self.editor.show()
            self.preview.hide()
        elif mode == "preview":
            self.editor.hide()
            self.preview.show()
            self._render_markdown()
        else:  # split
            self.editor.show()
            self.preview.show()
            self.splitter.setSizes([self.width() // 2, self.width() // 2])
            self._render_markdown()

    def _on_content_changed(self):
        """Debounced auto-save & live update preview."""
        self.autosave_timer.start()
        if self.preview.isVisible():
            self._render_markdown()

    def _render_markdown(self):
        raw_text = self.editor.toPlainText()

        # Transform Voice/Audio and Video links into safe escaped markdown links
        # This prevents filenames like voice_note_abc.wav from turning into italics!
        def _safe_media_link(match):
            icon = match.group(1)
            action = match.group(2)
            name = match.group(3).strip()
            url = match.group(4).strip()
            return f"\n\n{icon} [{action} `{name}`]({url})\n\n"

        processed_text = re.sub(
            r'([🎵🎥])\s*\[(Play Voice Note:|Watch Video:)\s*([^\]]+)\]\(([^)]+)\)',
            _safe_media_link,
            raw_text
        )

        # Convert markdown to html using markdown2 with native task_list support
        html_body = markdown2.markdown(
            processed_text, 
            extras=["fenced-code-blocks", "tables", "task_list", "strike"]
        )

        # Post-process task checkboxes to render crisp Unicode ballot boxes without redundant bullet points
        def _replace_task_li(match):
            is_checked = 'checked' in match.group(1)
            text = match.group(2).strip()
            if text.startswith('<p>') and text.endswith('</p>'):
                text = text[3:-4].strip()
            check_char = "☑" if is_checked else "☐"
            check_color = "#38BDF8" if is_checked else "#94A3B8"
            return (
                f'<div style="margin: 3px 0 3px 6px; line-height: 1.5;">'
                f'<span style="font-size: 15px; color: {check_color}; font-weight: bold;">{check_char}</span> '
                f'<span>{text}</span></div>'
            )

        html_body = re.sub(
            r'<li>\s*(?:<p>)?<input type="checkbox"[^>]*class="task-list-item-checkbox"([^>]*)>\s*(.*?)(?:</p>)?\s*</li>',
            _replace_task_li,
            html_body,
            flags=re.DOTALL
        )
        html_body = re.sub(
            r'<ul>\s*((?:<div style="margin: 3px 0 3px 6px; line-height: 1.5;">.*?</div>\s*)+)</ul>',
            r'\1',
            html_body,
            flags=re.DOTALL
        )

        safe_html_body = sanitize_markdown_html(html_body)
        css = self.theme_mgr.get_markdown_css()
        full_html = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\">{css}</head><body>{safe_html_body}</body></html>"
        self.preview.setHtml(full_html)

    def _update_header_icons(self):
        """Updates all header and player button vector icons dynamically based on current theme."""
        theme = self.theme_mgr.current_theme
        if hasattr(self, 'back_btn'):
            self.back_btn.setIcon(get_themed_icon("arrow_left", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'dup_btn'):
            self.dup_btn.setIcon(get_themed_icon("copy", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'tags_btn'):
            self.tags_btn.setIcon(get_themed_icon("tag", role="btn_text", theme=theme, size=17))
            self.tags_btn.setToolTip(tr("manage_tags", "Manage Tags"))
        if hasattr(self, 'share_btn'):
            self.share_btn.setIcon(get_themed_icon("share", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'help_btn'):
            self.help_btn.setIcon(get_themed_icon("help_circle", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'theme_btn'):
            is_dark = self.theme_mgr.is_dark_mode()
            is_auto = self.theme_mgr.is_system_theme()
            mode_desc = f"Auto (Following Windows: {'Dark' if is_dark else 'Light'})" if is_auto else f"{'Dark' if is_dark else 'Light'} (Manual)"
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_themed_icon("sun" if is_dark else "moon", role="btn_text", theme=theme, size=18))
            self.theme_btn.setToolTip(f"Theme: {mode_desc}\nLeft-click: Cycle theme\nRight-click: Choose theme mode")

        # Audio player buttons
        if hasattr(self, 'play_pause_btn'):
            is_playing = hasattr(self, 'media_player') and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            self.play_pause_btn.setIcon(get_themed_icon("pause" if is_playing else "play", role="btn_text", theme=theme, size=16))
        if hasattr(self, 'external_play_btn'):
            self.external_play_btn.setIcon(get_themed_icon("external_link", role="btn_text", theme=theme, size=16))
        if hasattr(self, 'close_player_btn'):
            self.close_player_btn.setIcon(get_themed_icon("close", role="btn_text", theme=theme, size=16))

        if hasattr(self, 'project_badge_btn'):
            self._update_editor_project_btn()

    def _update_editor_project_btn(self):
        """Updates the project stack badge label and icon in editor header."""
        theme = self.theme_mgr.current_theme
        projects = database.get_all_projects()
        p = next((proj for proj in projects if proj["id"] == self.current_project_id), None)
        name = p["name"] if p else "General Notes"
        self.project_badge_btn.setText(f" {name} ▾")
        self.project_badge_btn.setIcon(get_themed_icon("folder", role="btn_text", theme=theme, size=14))

    def _show_editor_project_menu(self):
        """Shows menu allowing user to change the active note's project stack."""
        if not self.current_note_id:
            return
        menu = QMenu(self)
        theme = self.theme_mgr.current_theme
        is_dark = self.theme_mgr.is_dark_mode()
        try:
            from ..styles import THEME_PALETTES
        except ImportError:
            from styles import THEME_PALETTES
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {pal.get('menu_bg', '#1E1F20' if is_dark else '#FFFFFF')};
                border: 1px solid {pal.get('border', '#444746' if is_dark else '#CBD5E1')};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px 6px 10px;
                font-size: 13px;
                border-radius: 4px;
                color: {pal.get('text_primary', '#E3E3E3' if is_dark else '#0F172A')};
            }}
            QMenu::item:selected {{
                background-color: {pal.get('btn_hover', '#333537' if is_dark else '#F1F5F9')};
                color: {pal.get('accent', '#8AB4F8' if is_dark else '#2563EB')};
            }}
        """)

        projects = database.get_all_projects()
        project_actions = {}
        for p in projects:
            p_id = p["id"]
            p_name = p["name"]
            is_cur = (p_id == self.current_project_id)
            act = menu.addAction(get_themed_icon("folder", role="btn_text", theme=theme, size=15), f"{p_name}" + ("  ✓" if is_cur else ""))
            act.setCheckable(True)
            act.setChecked(is_cur)
            project_actions[act] = p_id

        pos = self.project_badge_btn.mapToGlobal(self.project_badge_btn.rect().bottomLeft())
        action = menu.exec(pos)
        if action in project_actions:
            self.current_project_id = project_actions[action]
            database.update_note(self.current_note_id, project_id=self.current_project_id)
            self._update_editor_project_btn()

    def _show_theme_context_menu(self, pos):
        """Right-click menu allowing direct selection of System/Dark/Light/Sepia themes."""
        menu = QMenu(self)
        theme = self.theme_mgr.current_theme
        is_dark = self.theme_mgr.is_dark_mode()
        is_auto = self.theme_mgr.is_system_theme()

        act_auto = menu.addAction(get_themed_icon("monitor", role="btn_text", theme=theme, size=16), "Follow Windows Theme (Auto)")
        act_auto.setCheckable(True)
        act_auto.setChecked(is_auto)

        menu.addSeparator()

        act_dark = menu.addAction(get_themed_icon("moon", role="btn_text", theme=theme, size=16), "Dark Theme (Antigravity 2.0)")
        act_dark.setCheckable(True)
        act_dark.setChecked(not is_auto and is_dark)

        act_light = menu.addAction(get_themed_icon("sun", role="btn_text", theme=theme, size=16), "Light Theme")
        act_light.setCheckable(True)
        act_light.setChecked(not is_auto and theme == "light")

        act_sepia = menu.addAction("Sepia Theme")
        act_sepia.setCheckable(True)
        act_sepia.setChecked(not is_auto and theme == "sepia")

        action = menu.exec(self.theme_btn.mapToGlobal(pos))
        if action == act_auto:
            self.theme_mgr.set_theme("system")
        elif action == act_dark:
            self.theme_mgr.set_theme("dark")
        elif action == act_light:
            self.theme_mgr.set_theme("light")
        elif action == act_sepia:
            self.theme_mgr.set_theme("sepia")

        app = QApplication.instance()
        if app:
            app.setStyleSheet(self.theme_mgr.get_app_stylesheet())
        self._update_header_icons()

    def _open_help_dialog(self):
        """Displays the Help, Shortcuts, and About Dialog."""
        dialog = HelpAboutDialog(self)
        dialog.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F1 or (event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_H):
            self._open_help_dialog()
            return
        super().keyPressEvent(event)

    def _toggle_theme(self):
        self.theme_mgr.toggle_theme()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(self.theme_mgr.get_app_stylesheet())

    def _on_theme_changed(self, new_theme: str):
        self._update_header_icons()
        if hasattr(self, 'highlighter'):
            self.highlighter.set_theme(new_theme)
        if hasattr(self, 'format_toolbar'):
            self.format_toolbar.update_icons_for_theme(new_theme)
        if self.preview.isVisible():
            self._render_markdown()

    def _on_media_dropped(self, media_type: str, file_path: str):
        """Handles drag-and-dropped media files by copying to attachments and inserting markdown tag."""
        try:
            copied = copy_to_attachments(file_path)
        except ValueError as e:
            QMessageBox.warning(self, "Security Alert", str(e))
            return

        url = QUrl.fromLocalFile(str(copied)).toString()
        cursor = self.editor.textCursor()
        if media_type == "image":
            cursor.insertText(f"\n![{copied.stem}]({url})\n")
        elif media_type == "audio":
            cursor.insertText(f"\n🎵 [Play Voice Note: {copied.name}]({url})\n")
        elif media_type == "video":
            cursor.insertText(f"\n🎥 [Watch Video: {copied.name}]({url})\n")
        self.editor.setFocus()

    def _auto_save(self):
        if not self.current_note_id:
            return
        title = self.title_input.text().strip() or "Untitled Note"
        content = self.editor.toPlainText()
        database.update_note(self.current_note_id, title=title, content=content, color_hex=self.current_color_hex, project_id=self.current_project_id)

    def _on_back_clicked(self):
        self._stop_and_hide_audio_player()
        self._auto_save()
        self.back_requested.emit()

    def _open_color_picker(self):
        flyout = ColorPickerFlyout(self)
        flyout.color_selected.connect(self._on_color_selected)
        # Position below the badge button
        pos = self.color_badge.mapToGlobal(self.color_badge.rect().bottomLeft())
        flyout.move(pos.x() - 100, pos.y() + 6)
        flyout.show()

    def _open_tags_flyout(self):
        if not self.current_note_id:
            return
        flyout = TagSelectorFlyout(self.current_note_id, self)
        pos = self.tags_btn.mapToGlobal(self.tags_btn.rect().bottomLeft())
        flyout.move(pos.x() - 100, pos.y() + 6)
        flyout.exec()
        self._refresh_tags_bar()

    def _refresh_tags_bar(self):
        """Renders interactive tag chips with (×) quick remove and [+ Add Tag] button."""
        if not hasattr(self, 'tags_bar_layout') or self.tags_bar_layout is None:
            return
        while self.tags_bar_layout.count():
            item = self.tags_bar_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.current_note_id:
            return

        tags = database.get_note_tags(self.current_note_id)

        theme = self.theme_mgr.current_theme
        is_dark = self.theme_mgr.is_dark_mode()
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])
        chip_bg = pal.get("btn_hover", "#333537" if is_dark else "#E2E8F0")
        chip_fg = pal.get("text_primary", "#E3E3E3" if is_dark else "#1E293B")
        border = pal.get("border", "#444746" if is_dark else "#CBD5E1")

        for tag in tags:
            chip = QFrame(self.tags_bar_widget)
            chip.setStyleSheet(f"""
                QFrame {{
                    background-color: {chip_bg};
                    border: 1px solid {border};
                    border-radius: 11px;
                }}
            """)
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(7, 2, 6, 2)
            c_lay.setSpacing(5)

            lbl = QLabel(f"#{tag}", chip)
            lbl.setStyleSheet(f"color: {chip_fg}; font-size: 11px; font-weight: 600; border: none; background: transparent;")
            c_lay.addWidget(lbl)

            btn_del = QPushButton("×", chip)
            btn_del.setFixedSize(14, 14)
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn_del.setToolTip(f"Remove #{tag}")
            btn_del.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: #94A3B8;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 0;
                    margin: 0;
                }
                QPushButton:hover {
                    color: #EF4444;
                }
            """)
            btn_del.clicked.connect(lambda _, t=tag: self._remove_tag_from_current_note(t))
            c_lay.addWidget(btn_del)

            self.tags_bar_layout.addWidget(chip)

        # "+ Add Tag" button
        add_tag_btn = QPushButton(f"+ {tr('add_tag')}", self.tags_bar_widget)
        add_tag_btn.setObjectName("AddTagBtn")
        add_tag_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_tag_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px dashed {border};
                border-radius: 11px;
                padding: 2px 9px;
                font-size: 11px;
                font-weight: 600;
                color: {pal.get('accent', '#2563EB')};
            }}
            QPushButton:hover {{
                background-color: {chip_bg};
            }}
        """)
        add_tag_btn.clicked.connect(self._open_tags_flyout)
        self.tags_bar_layout.addWidget(add_tag_btn)

        self.tags_bar_layout.addStretch()

    def _remove_tag_from_current_note(self, tag_to_remove: str):
        if not self.current_note_id:
            return
        current_tags = database.get_note_tags(self.current_note_id)
        new_tags = [t for t in current_tags if t != tag_to_remove]
        database.set_note_tags(self.current_note_id, new_tags)
        self._refresh_tags_bar()

    def _apply_language_change(self):
        """Updates all button tooltips and text in the editor when the language switches."""
        if hasattr(self, 'back_btn'):
            self.back_btn.setToolTip(f"{tr('back_to_board')} (Esc)")
        if hasattr(self, 'title_input'):
            self.title_input.setPlaceholderText(tr("editor_title_placeholder"))
        if hasattr(self, 'btn_edit'):
            self.btn_edit.setText(tr("mode_edit"))
        if hasattr(self, 'btn_split'):
            self.btn_split.setText(tr("mode_split"))
        if hasattr(self, 'btn_preview'):
            self.btn_preview.setText(tr("mode_preview"))
        if hasattr(self, 'dup_btn'):
            self.dup_btn.setToolTip(tr("duplicate_note"))
        if hasattr(self, 'share_btn'):
            self.share_btn.setToolTip(tr("share_export"))
        if hasattr(self, 'help_btn'):
            self.help_btn.setToolTip(tr("help_tooltip"))
        if hasattr(self, 'tags_btn'):
            self.tags_btn.setToolTip(tr("tooltip_tags"))
        if hasattr(self, 'color_badge'):
            self.color_badge.setToolTip(tr("tooltip_palette"))
        if hasattr(self, 'format_toolbar') and hasattr(self.format_toolbar, 'retranslate_ui'):
            self.format_toolbar.retranslate_ui()
        if hasattr(self, 'highlighter'):
            engine = get_proofing_engine()
            lang = getattr(self.i18n, 'current_language', 'en')
            engine.set_language(lang)
            self.highlighter.rehighlight()
        self._refresh_tags_bar()

    def _on_color_selected(self, hex_val: str):
        self.current_color_hex = hex_val
        self._update_color_badge()
        self._auto_save()

    def _update_color_badge(self):
        border = "#333333" if not is_dark_color(self.current_color_hex) else "#FFFFFF"
        self.color_badge.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color_hex};
                border: 2px solid {border};
                border-radius: 14px;
            }}
            QPushButton:hover {{
                transform: scale(1.1);
            }}
        """)

    def _duplicate_current_note(self):
        if not self.current_note_id:
            return
        self._auto_save()
        new_id = database.duplicate_note(self.current_note_id)
        if new_id:
            QMessageBox.information(self, "Duplicated", "Note duplicated successfully!")
            self.back_requested.emit()

    def _share_current_note(self):
        self._auto_save()
        title = self.title_input.text().strip() or "Untitled Note"
        content = self.editor.toPlainText()
        dialog = ShareNoteDialog(title, content, self)
        dialog.exec()

    def _on_add_picture(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert Picture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;All Files (*.*)"
        )
        if file_path:
            try:
                copied = copy_to_attachments(file_path)
            except ValueError as e:
                QMessageBox.warning(self, "Security Alert", str(e))
                return
            url = QUrl.fromLocalFile(str(copied)).toString()
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n![{copied.stem}]({url})\n")
            self.editor.setFocus()

    def _on_add_audio(self):
        dialog = VoiceRecorderDialog(self)
        if dialog.exec():
            if dialog.result_audio_path:
                path = Path(dialog.result_audio_path)
                url = QUrl.fromLocalFile(str(path)).toString()
                cursor = self.editor.textCursor()
                cursor.insertText(f"\n🎵 [Play Voice Note: {path.name}]({url})\n")
                self.editor.setFocus()

    def _on_add_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Attach Video",
            "",
            "Video Files (*.mp4 *.webm *.mkv *.mov *.avi);;All Files (*.*)"
        )
        if file_path:
            try:
                copied = copy_to_attachments(file_path)
            except ValueError as e:
                QMessageBox.warning(self, "Security Alert", str(e))
                return
            url = QUrl.fromLocalFile(str(copied)).toString()
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n🎥 [Watch Video: {copied.name}]({url})\n")
            self.editor.setFocus()

    def _on_record_screen(self):
        """Launches the Desktop Screen Recorder and embeds the recorded video upon completion."""
        top_window = self.window()

        dialog = ScreenRecorderDialog(self)
        res = dialog.exec()

        if top_window and top_window.isMinimized():
            top_window.showNormal()
            top_window.activateWindow()

        if res == QDialog.DialogCode.Accepted and dialog.result_video_path:
            path = Path(dialog.result_video_path)
            url = QUrl.fromLocalFile(str(path)).toString()
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n🎥 [Watch Screen Recording: {path.name}]({url})\n")
            self.editor.setFocus()
            self._auto_save()
            self.set_view_mode("split")

            duration = getattr(dialog, "result_duration", 0)
            complete_dialog = RecordingCompleteDialog(dialog.result_video_path, duration=duration, parent=self)
            complete_dialog.exec()

    def _on_screen_capture(self):
        """Captures a screenshot or interactive region snip and embeds it into the note."""
        top_window = self.window()
        was_visible = top_window.isVisible() if top_window else False

        # Briefly hide window so user can capture clean desktop or background windows
        if top_window and was_visible:
            top_window.hide()
            QApplication.processEvents()
            time.sleep(0.18)

        screen = QGuiApplication.primaryScreen()
        if not screen:
            if top_window and was_visible:
                top_window.show()
            return

        screenshot = screen.grabWindow(0)
        overlay = SnippingOverlay(screenshot)
        res = overlay.exec()

        if top_window and was_visible:
            if top_window.isMinimized():
                top_window.showNormal()
            else:
                top_window.show()
            top_window.activateWindow()

        if res == QDialog.DialogCode.Accepted and overlay.result_pixmap and not overlay.result_pixmap.isNull():
            attachments_dir = get_attachments_dir()
            attachments_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = uuid.uuid4().hex[:8]
            file_name = f"capture_{timestamp}_{unique_id}.png"
            file_path = attachments_dir / file_name

            overlay.result_pixmap.save(str(file_path), "PNG")

            url = QUrl.fromLocalFile(str(file_path)).toString()
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n![Screen Capture: {file_name}]({url})\n")
            self.editor.setFocus()
            self._auto_save()
            self.set_view_mode("split")

    def _on_attach_audio_file(self):
        """Attaches an existing audio file from local disk."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("attach_audio") if callable(tr) else "Attach Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac *.wma);;All Files (*.*)"
        )
        if file_path:
            try:
                copied = copy_to_attachments(file_path)
            except ValueError as e:
                QMessageBox.warning(self, "Security Alert", str(e))
                return
            url = QUrl.fromLocalFile(str(copied)).toString()
            cursor = self.editor.textCursor()
            cursor.insertText(f"\n🎵 [Play Voice Note: {copied.name}]({url})\n")
            self.editor.setFocus()
            self._auto_save()

    def _open_attachments_folder(self):
        """Opens the local attachments directory in the system file manager."""
        attachments_dir = get_attachments_dir()
        attachments_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", os.path.normpath(str(attachments_dir))])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(attachments_dir)))

    def _on_anchor_clicked(self, url: QUrl):
        """Open audio/video media files or links with security validation and in-app playback."""
        url_str = url.toString()
        if url_str.startswith("#"):
            self.preview.scrollToAnchor(url_str.lstrip("#"))
            return

        is_safe, reason = is_safe_url(url_str, allowed_attachments_dir=get_attachments_dir())
        if not is_safe:
            QMessageBox.warning(
                self, 
                "Security Alert", 
                f"Opening this link was blocked for your protection:\n\n{url_str}\n\nReason: {reason}"
            )
            return

        # Check local files for existence, zero-byte status, and in-app playback
        if url.isLocalFile():
            local_path = Path(url.toLocalFile())
            if not local_path.exists():
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"The attached file could not be found:\n\n{local_path.name}\n\nIt may have been moved or deleted."
                )
                return

            if local_path.stat().st_size <= 350 and local_path.suffix.lower() in ('.wav', '.m4a', '.mp3'):
                QMessageBox.warning(
                    self,
                    "Empty Recording",
                    f"This audio recording is empty (0 bytes of sound captured).\n\n"
                    f"File: {local_path.name}\n\n"
                    "The microphone did not send any audio data when this note was recorded."
                )
                return

            # Audio attachments play directly inside the app!
            if local_path.suffix.lower() in ('.wav', '.m4a', '.mp3', '.ogg', '.flac', '.aac'):
                self._play_audio_in_app(url, local_path.name)
                return

        # For videos, external web links, or other documents, open with system default handler
        QDesktopServices.openUrl(url)

    def _play_audio_in_app(self, url: QUrl, name: str):
        """Starts in-app audio playback and reveals the player control bar."""
        self._current_audio_url = url
        clean_name = name.replace("voice_note_", "Voice Note ")
        self.audio_title_label.setText(f"🎵 {clean_name}")
        self.audio_player_frame.setVisible(True)
        self.media_player.setSource(url)
        self.media_player.play()

    def _toggle_audio_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _on_seek_audio(self, pos_ms: int):
        self.media_player.setPosition(pos_ms)

    def _on_player_position_changed(self, pos_ms: int):
        if not self.audio_slider.isSliderDown():
            self.audio_slider.setValue(pos_ms)
        self._update_time_label(pos_ms, self.media_player.duration())

    def _on_player_duration_changed(self, dur_ms: int):
        self.audio_slider.setRange(0, dur_ms)
        self._update_time_label(self.media_player.position(), dur_ms)

    def _on_player_state_changed(self, state):
        theme = self.theme_mgr.current_theme
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setIcon(get_themed_icon("pause", role="btn_text", theme=theme, size=16))
        else:
            self.play_pause_btn.setIcon(get_themed_icon("play", role="btn_text", theme=theme, size=16))

    def _update_time_label(self, current_ms: int, total_ms: int):
        cur_sec = current_ms // 1000
        tot_sec = max(0, total_ms // 1000)
        self.audio_time_label.setText(f"{cur_sec // 60:02d}:{cur_sec % 60:02d} / {tot_sec // 60:02d}:{tot_sec % 60:02d}")

    def _open_audio_externally(self):
        if self._current_audio_url:
            QDesktopServices.openUrl(self._current_audio_url)

    def _stop_and_hide_audio_player(self):
        self.media_player.stop()
        self.audio_player_frame.setVisible(False)

    def keyPressEvent(self, event):
        # Keyboard formatting shortcuts
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_B:
                self.format_toolbar.apply_bold()
                return
            elif event.key() == Qt.Key.Key_I:
                self.format_toolbar.apply_italic()
                return
            elif event.key() == Qt.Key.Key_U:
                self.format_toolbar.apply_underline()
                return

        # Escape key returns to notes board
        if event.key() == Qt.Key.Key_Escape:
            self._on_back_clicked()
        else:
            super().keyPressEvent(event)


