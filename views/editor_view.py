import markdown2
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QTextBrowser, QPushButton,
    QFrame, QSplitter, QMessageBox, QFileDialog, QMenu, QApplication
)
from PySide6.QtGui import QCursor
try:
    from ..components.color_picker_flyout import ColorPickerFlyout
    from ..styles import MARKDOWN_PREVIEW_CSS, is_dark_color
    from .. import database
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from styles import MARKDOWN_PREVIEW_CSS, is_dark_color
    import database

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
        self.back_btn = QPushButton("←", self)
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
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 0, 0, 0)
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
        self.dup_btn = QPushButton("📋", self)
        self.dup_btn.setToolTip("Duplicate Note")
        self.dup_btn.setFixedSize(32, 30)
        self.dup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dup_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.05); }
        """)
        self.dup_btn.clicked.connect(self._duplicate_current_note)
        header_layout.addWidget(self.dup_btn)

        self.share_btn = QPushButton("↗", self)
        self.share_btn.setToolTip("Share / Export Note")
        self.share_btn.setFixedSize(32, 30)
        self.share_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.share_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.05); }
        """)
        self.share_btn.clicked.connect(self._share_current_note)
        header_layout.addWidget(self.share_btn)

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

        # Raw Markdown Text Editor
        self.editor = QTextEdit(self.splitter)
        self.editor.setObjectName("MarkdownEditor")
        self.editor.setPlaceholderText("Write your note here in Markdown...\n\n# Heading\n- Bullet item\n**Bold text**\n`code`")
        self.editor.textChanged.connect(self._on_content_changed)

        # Rendered Markdown Browser
        self.preview = QTextBrowser(self.splitter)
        self.preview.setObjectName("MarkdownPreview")
        self.preview.setOpenExternalLinks(True)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)

        main_layout.addWidget(self.splitter, 1)

        # Default Mode is Split View
        self.set_view_mode("split")

    def load_note(self, note_id: str):
        """Loads a note by ID into the editor."""
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
        # Convert markdown to html using markdown2 with code, tables, and fenced-code-blocks
        html_body = markdown2.markdown(
            raw_text, 
            extras=["fenced-code-blocks", "tables", "task_list", "strike"]
        )
        full_html = f"<html><head>{MARKDOWN_PREVIEW_CSS}</head><body>{html_body}</body></html>"
        self.preview.setHtml(full_html)

    def _auto_save(self):
        if not self.current_note_id:
            return
        title = self.title_input.text().strip() or "Untitled Note"
        content = self.editor.toPlainText()
        database.update_note(self.current_note_id, title=title, content=content, color_hex=self.current_color_hex)

    def _on_back_clicked(self):
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
                full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{MARKDOWN_PREVIEW_CSS}</head><body><h1>{title}</h1>{html_body}</body></html>"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

    def keyPressEvent(self, event):
        # Allow pressing Escape to quickly return to notes
        if event.key() == Qt.Key.Key_Escape:
            self._on_back_clicked()
        else:
            super().keyPressEvent(event)

