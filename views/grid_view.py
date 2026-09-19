from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QFrame,
    QMessageBox, QFileDialog, QMenu, QApplication
)
from PySide6.QtGui import QCursor, QAction
import markdown2
try:
    from ..components.note_card import NoteCard
    from ..styles import MARKDOWN_PREVIEW_CSS
    from .. import database
except ImportError:
    from components.note_card import NoteCard
    from styles import MARKDOWN_PREVIEW_CSS
    import database

class StickyNotesGridView(QWidget):
    """
    Main board displaying recent sticky notes in a minimal responsive grid.
    """
    open_note_requested = Signal(str)  # Emits note_id to switch to editor

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GridViewContainer")
        self.note_cards = []
        self.is_selection_mode = False
        self.selected_note_ids = set()

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 24, 28, 16)
        self.main_layout.setSpacing(14)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        self.title_label = QLabel("My Notes", self)
        self.title_label.setObjectName("AppHeaderTitle")
        title_col.addWidget(self.title_label)

        self.subtitle_label = QLabel("Double-click to edit • Right-click for options", self)
        self.subtitle_label.setObjectName("AppHeaderSubtitle")
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # "Select" Mode Toggle Button
        self.select_mode_btn = QPushButton("Select", self)
        self.select_mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 13px;
                font-weight: 600;
                color: #334155;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
        """)
        self.select_mode_btn.clicked.connect(self._toggle_selection_mode)
        header_layout.addWidget(self.select_mode_btn)

        # "+ New Note" Button
        self.new_note_btn = QPushButton("+ New Note", self)
        self.new_note_btn.setObjectName("NewNoteButton")
        self.new_note_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_note_btn.clicked.connect(self._create_new_note)
        header_layout.addWidget(self.new_note_btn)

        self.main_layout.addLayout(header_layout)

        # Scroll Area for Notes Grid
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_content = QWidget()
        self.grid_layout = QGridLayout(self.grid_content)
        self.grid_layout.setContentsMargins(4, 8, 4, 16)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.grid_content)
        self.main_layout.addWidget(self.scroll_area, 1)

        # Bottom Selection Action Bar (hidden by default)
        self.action_bar = QFrame(self)
        self.action_bar.setObjectName("SelectionActionBar")
        self.action_bar.setVisible(False)
        self.action_bar.setStyleSheet("""
            QFrame#SelectionActionBar {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 10px;
                padding: 8px 16px;
            }
        """)
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(8, 4, 8, 4)
        action_layout.setSpacing(12)

        self.selection_count_label = QLabel("0 notes selected", self.action_bar)
        self.selection_count_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
        action_layout.addWidget(self.selection_count_label)

        action_layout.addStretch()

        self.select_all_btn = QPushButton("Select All", self.action_bar)
        self.select_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_all_btn.setStyleSheet("border: none; color: #0067C0; font-weight: 600; padding: 6px 10px;")
        self.select_all_btn.clicked.connect(self._select_all_notes)
        action_layout.addWidget(self.select_all_btn)

        self.delete_selected_btn = QPushButton("Delete Selected", self.action_bar)
        self.delete_selected_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #B91C1C; }
            QPushButton:disabled { background-color: #F87171; }
        """)
        self.delete_selected_btn.clicked.connect(self._delete_selected_notes)
        action_layout.addWidget(self.delete_selected_btn)

        self.cancel_selection_btn = QPushButton("Cancel", self.action_bar)
        self.cancel_selection_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_selection_btn.setStyleSheet("border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 6px; padding: 6px 12px; font-weight: 600;")
        self.cancel_selection_btn.clicked.connect(self._toggle_selection_mode)
        action_layout.addWidget(self.cancel_selection_btn)

        self.main_layout.addWidget(self.action_bar)

    def load_notes(self):
        """Reloads all notes from the database and populates the grid."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.note_cards.clear()
        self.selected_note_ids.clear()
        self._update_selection_ui()

        notes = database.get_all_notes()
        
        if not notes:
            empty_label = QLabel("No notes yet. Click '+ New Note' to create your first sticky note!", self)
            empty_label.setStyleSheet("color: #6B7280; font-size: 14px; margin-top: 40px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        cols = max(1, self.width() // 250) if self.width() > 0 else 3

        for index, note in enumerate(notes):
            row = index // cols
            col = index % cols
            
            card = NoteCard(note, self.grid_content)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.color_changed.connect(self._on_card_color_changed)
            card.duplicate_requested.connect(self._on_card_duplicate_requested)
            card.share_requested.connect(self._on_card_share_requested)
            card.delete_requested.connect(self._on_card_delete_requested)
            card.selection_toggled.connect(self._on_card_selection_toggled)
            
            if self.is_selection_mode:
                card.set_selection_mode(True)
            
            self.grid_layout.addWidget(card, row, col)
            self.note_cards.append(card)

    def _toggle_selection_mode(self):
        self.is_selection_mode = not self.is_selection_mode
        self.action_bar.setVisible(self.is_selection_mode)
        self.select_mode_btn.setText("Done" if self.is_selection_mode else "Select")
        self.selected_note_ids.clear()
        
        for card in self.note_cards:
            card.set_selection_mode(self.is_selection_mode)
            
        self._update_selection_ui()

    def _on_card_selection_toggled(self, note_id: str, is_selected: bool):
        if is_selected:
            self.selected_note_ids.add(note_id)
        else:
            self.selected_note_ids.discard(note_id)
        self._update_selection_ui()

    def _select_all_notes(self):
        all_selected = len(self.selected_note_ids) == len(self.note_cards)
        new_state = not all_selected
        self.selected_note_ids.clear()
        
        for card in self.note_cards:
            card.set_selected(new_state)
            if new_state:
                self.selected_note_ids.add(card.note_id)
                
        self.select_all_btn.setText("Deselect All" if new_state else "Select All")
        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self.selected_note_ids)
        self.selection_count_label.setText(f"{count} note{'s' if count != 1 else ''} selected")
        self.delete_selected_btn.setEnabled(count > 0)
        self.delete_selected_btn.setText(f"Delete Selected ({count})" if count > 0 else "Delete Selected")

    def _delete_selected_notes(self):
        count = len(self.selected_note_ids)
        if count == 0:
            return
            
        confirm = QMessageBox.question(
            self,
            "Delete Notes",
            f"Are you sure you want to delete {count} selected note{'s' if count != 1 else ''}?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            database.delete_multiple_notes(list(self.selected_note_ids))
            self._toggle_selection_mode()
            self.load_notes()

    def _create_new_note(self):
        new_id = database.create_note(title="Untitled Note", content="", color_hex="#FFF9C4")
        self.open_note_requested.emit(new_id)

    def _on_card_double_clicked(self, note_id: str):
        if not self.is_selection_mode:
            self.open_note_requested.emit(note_id)

    def _on_card_color_changed(self, note_id: str, new_color_hex: str):
        database.update_note(note_id, color_hex=new_color_hex)

    def _on_card_duplicate_requested(self, note_id: str):
        database.duplicate_note(note_id)
        self.load_notes()

    def _on_card_share_requested(self, note_id: str):
        note = database.get_note(note_id)
        if not note:
            return
            
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
            clipboard_text = f"# {note['title']}\n\n{note['content']}"
            QApplication.clipboard().setText(clipboard_text)
            QMessageBox.information(self, "Copied", "Note copied to clipboard!")
        elif action == act_export_md:
            safe_title = "".join(c for c in note['title'] if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as Markdown", f"{safe_title}.md", "Markdown Files (*.md)")
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"# {note['title']}\n\n{note['content']}")
        elif action == act_export_html:
            safe_title = "".join(c for c in note['title'] if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as HTML", f"{safe_title}.html", "HTML Files (*.html)")
            if file_path:
                html_body = markdown2.markdown(note['content'], extras=["fenced-code-blocks", "tables", "task_list", "strike"])
                full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{note['title']}</title>{MARKDOWN_PREVIEW_CSS}</head><body><h1>{note['title']}</h1>{html_body}</body></html>"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

    def _on_card_delete_requested(self, note_id: str):
        database.delete_note(note_id)
        self.load_notes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.note_cards:
            cols = max(1, self.width() // 250)
            for index, card in enumerate(self.note_cards):
                self.grid_layout.removeWidget(card)
                row = index // cols
                col = index % cols
                self.grid_layout.addWidget(card, row, col)

