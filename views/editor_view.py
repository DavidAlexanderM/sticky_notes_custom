import re
from pathlib import Path
import markdown2
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QTextBrowser, QPushButton,
    QFrame, QSplitter, QMessageBox, QFileDialog, QMenu, QApplication, QSlider
)
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
try:
    from ..components.color_picker_flyout import ColorPickerFlyout
    from ..components.format_toolbar import FormatToolbar
    from ..components.voice_recorder_dialog import VoiceRecorderDialog
    from ..components.help_dialog import HelpAboutDialog
    from ..media_manager import copy_to_attachments, get_attachments_dir
    from ..styles import MARKDOWN_PREVIEW_CSS, is_dark_color, get_markdown_preview_css
    from ..security import is_safe_url, sanitize_markdown_html
    from ..theme_manager import get_theme_manager
    from ..icons import get_themed_icon
    from ..markdown_highlighter import MarkdownHighlighter
    from .. import database
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from components.format_toolbar import FormatToolbar
    from components.voice_recorder_dialog import VoiceRecorderDialog
    from components.help_dialog import HelpAboutDialog
    from media_manager import copy_to_attachments, get_attachments_dir
    from styles import MARKDOWN_PREVIEW_CSS, is_dark_color, get_markdown_preview_css
    from security import is_safe_url, sanitize_markdown_html
    from theme_manager import get_theme_manager
    from icons import get_themed_icon
    from markdown_highlighter import MarkdownHighlighter
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

        # Color Indicator & Selector Button
        self.color_badge = QPushButton(self)
        self.color_badge.setFixedSize(28, 28)
        self.color_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.color_badge.setToolTip("Change Note Color")
        self.color_badge.clicked.connect(self._open_color_picker)
        header_layout.addWidget(self.color_badge)

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
        header_layout.addWidget(self.theme_btn)

        main_layout.addLayout(header_layout)

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
        self._update_color_badge()

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
        if hasattr(self, 'share_btn'):
            self.share_btn.setIcon(get_themed_icon("share", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'help_btn'):
            self.help_btn.setIcon(get_themed_icon("help_circle", role="btn_text", theme=theme, size=18))
        if hasattr(self, 'theme_btn'):
            is_dark = self.theme_mgr.is_dark_mode()
            self.theme_btn.setText("")
            self.theme_btn.setIcon(get_themed_icon("sun" if is_dark else "moon", role="btn_text", theme=theme, size=18))
            self.theme_btn.setToolTip(f"Theme: {'Dark' if is_dark else 'Light'} (Click to switch)")

        # Audio player buttons
        if hasattr(self, 'play_pause_btn'):
            is_playing = hasattr(self, 'media_player') and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            self.play_pause_btn.setIcon(get_themed_icon("pause" if is_playing else "play", role="btn_text", theme=theme, size=16))
        if hasattr(self, 'external_play_btn'):
            self.external_play_btn.setIcon(get_themed_icon("external_link", role="btn_text", theme=theme, size=16))
        if hasattr(self, 'close_player_btn'):
            self.close_player_btn.setIcon(get_themed_icon("close", role="btn_text", theme=theme, size=16))

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
        database.update_note(self.current_note_id, title=title, content=content, color_hex=self.current_color_hex)

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

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 16px;
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #0067C0;
            }
        """)

        act_copy = menu.addAction("📋 Copy Markdown to Clipboard")
        act_export_md = menu.addAction("📄 Export as .md file")
        act_export_html = menu.addAction("🌐 Export as .html file")

        action = menu.exec(QCursor.pos())
        if action == act_copy:
            clipboard_text = f"# {title}\n\n{content}"
            QApplication.clipboard().setText(clipboard_text)
            QMessageBox.information(self, "Copied", "Note copied to clipboard!")
        elif action == act_export_md:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as Markdown", f"{safe_title}.md", "Markdown Files (*.md)")
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n{content}")
        elif action == act_export_html:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as HTML", f"{safe_title}.html", "HTML Files (*.html)")
            if file_path:
                html_body = markdown2.markdown(content, extras=["fenced-code-blocks", "tables", "task_list", "strike"])
                safe_html_body = sanitize_markdown_html(html_body)
                full_html = f"<html><head>{MARKDOWN_PREVIEW_CSS}</head><body>{safe_html_body}</body></html>"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

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


