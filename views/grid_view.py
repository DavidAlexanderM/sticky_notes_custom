from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QGridLayout, QFrame,
    QMessageBox, QFileDialog, QMenu, QApplication
)
from PySide6.QtGui import QCursor, QAction
import markdown2

try:
    from ..components.note_card import NoteCard
    from ..styles import MARKDOWN_PREVIEW_CSS, NOTE_COLORS
    from ..theme_manager import get_theme_manager
    from .. import database
except ImportError:
    from components.note_card import NoteCard
    from styles import MARKDOWN_PREVIEW_CSS, NOTE_COLORS
    from theme_manager import get_theme_manager
    import database


class StickyNotesGridView(QWidget):
    """
    Main board displaying notes with real-time search filtering,
    color category chips, theme switching, and multi-selection management.
    """
    open_note_requested = Signal(str)  # Emits note_id to switch to editor

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GridViewContainer")
        self.note_cards = []
        self.all_notes = []
        self.is_selection_mode = False
        self.selected_note_ids = set()
        self.current_color_filter = None  # None means 'All'
        self.theme_mgr = get_theme_manager()

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 20, 28, 16)
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

        # Theme Switcher Button (☀️ / 🌙)
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("ThemeToggleBtn")
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.setToolTip("Toggle Light / Dark Theme")
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_btn_label()
        header_layout.addWidget(self.theme_btn)

        # "Select" Mode Toggle Button
        self.select_mode_btn = QPushButton("Select", self)
        self.select_mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(120, 120, 120, 0.25);
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.10);
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

        # Search Bar & Color Filter Bar
        search_filter_layout = QVBoxLayout()
        search_filter_layout.setSpacing(8)

        # Real-time search input
        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("SearchInput")
        self.search_input.setPlaceholderText("🔍 Search notes by title, tag, or content...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_filter_layout.addWidget(self.search_input)

        # Color Filter Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        chips_layout.setContentsMargins(0, 0, 0, 0)

        self.pill_buttons = {}
        all_pill = QPushButton("All Notes", self)
        all_pill.setObjectName("FilterPill")
        all_pill.setProperty("active", True)
        all_pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        all_pill.clicked.connect(lambda: self._set_color_filter(None))
        chips_layout.addWidget(all_pill)
        self.pill_buttons[None] = all_pill

        for c in NOTE_COLORS[:6]:  # Top 6 popular colors
            hex_val = c["hex"]
            pill = QPushButton(f"● {c['name'].split()[0]}", self)
            pill.setObjectName("FilterPill")
            pill.setProperty("active", False)
            pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pill.clicked.connect(lambda _, h=hex_val: self._set_color_filter(h))
            chips_layout.addWidget(pill)
            self.pill_buttons[hex_val] = pill

        chips_layout.addStretch()
        search_filter_layout.addLayout(chips_layout)

        self.main_layout.addLayout(search_filter_layout)

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
                background-color: rgba(120, 120, 120, 0.15);
                border: 1px solid rgba(120, 120, 120, 0.25);
                border-radius: 10px;
                padding: 8px 16px;
            }
        """)
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(8, 4, 8, 4)
        action_layout.setSpacing(12)

        self.selection_count_label = QLabel("0 notes selected", self.action_bar)
        self.selection_count_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        action_layout.addWidget(self.selection_count_label)

        action_layout.addStretch()

        self.select_all_btn = QPushButton("Select All", self.action_bar)
        self.select_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_all_btn.setStyleSheet("border: 1px solid rgba(120, 120, 120, 0.3); border-radius: 6px; padding: 5px 12px; font-size: 12px;")
        self.select_all_btn.clicked.connect(self._select_all_notes)
        action_layout.addWidget(self.select_all_btn)

        self.delete_selected_btn = QPushButton("🗑 Delete Selected", self.action_bar)
        self.delete_selected_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.delete_selected_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.delete_selected_btn.clicked.connect(self._delete_selected_notes)
        action_layout.addWidget(self.delete_selected_btn)

        self.main_layout.addWidget(self.action_bar)

        # Listen to theme change signals
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)

    def _update_theme_btn_label(self):
        """Updates the theme toggle button icon and text."""
        if self.theme_mgr.is_dark_mode():
            self.theme_btn.setText("☀️ Light")
        else:
            self.theme_btn.setText("🌙 Dark")

    def _toggle_theme(self):
        new_theme = self.theme_mgr.toggle_theme()
        # Apply globally to application
        app = QApplication.instance()
        if app:
            app.setStyleSheet(self.theme_mgr.get_app_stylesheet())
        self._update_theme_btn_label()

    def _on_theme_changed(self, new_theme: str):
        self._update_theme_btn_label()
        for card in self.note_cards:
            card._apply_style()

    def _set_color_filter(self, hex_val):
        self.current_color_filter = hex_val
        for key, btn in self.pill_buttons.items():
            btn.setProperty("active", key == hex_val)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._filter_and_render_notes()

    def _on_search_changed(self, text: str):
        self._filter_and_render_notes()

    def load_notes(self):
        """Reloads notes from database and refreshes view."""
        self.all_notes = database.get_all_notes()
        self._filter_and_render_notes()

    def _filter_and_render_notes(self):
        """Filters notes based on search query and color chip, then renders grid."""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.note_cards.clear()
        self.selected_note_ids.clear()
        self._update_selection_ui()

        search_query = self.search_input.text().strip().lower()

        filtered = []
        for note in self.all_notes:
            # Color filter
            if self.current_color_filter and note.get("color_hex") != self.current_color_filter:
                continue
            # Text search filter
            if search_query:
                title_match = search_query in note.get("title", "").lower()
                content_match = search_query in note.get("content", "").lower()
                if not (title_match or content_match):
                    continue
            filtered.append(note)

        # Empty state handling
        if not filtered:
            empty_frame = QFrame(self.grid_content)
            empty_frame.setObjectName("EmptyStateCard")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(10)

            if search_query or self.current_color_filter:
                icon_lbl = QLabel("🔍", empty_frame)
                icon_lbl.setStyleSheet("font-size: 32px;")
                title_lbl = QLabel("No notes matched your search.", empty_frame)
                title_lbl.setStyleSheet("font-size: 15px; font-weight: 600;")
                btn_clear = QPushButton("Clear Filter", empty_frame)
                btn_clear.setStyleSheet("padding: 6px 14px; border-radius: 6px;")
                btn_clear.clicked.connect(self._clear_filters)
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(btn_clear, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                icon_lbl = QLabel("📝", empty_frame)
                icon_lbl.setStyleSheet("font-size: 36px;")
                title_lbl = QLabel("No notes yet.", empty_frame)
                title_lbl.setStyleSheet("font-size: 16px; font-weight: 600;")
                sub_lbl = QLabel("Click '+ New Note' to create your first sticky note!", empty_frame)
                sub_lbl.setStyleSheet("font-size: 13px; opacity: 0.7;")
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(sub_lbl, 0, Qt.AlignmentFlag.AlignCenter)

            self.grid_layout.addWidget(empty_frame, 0, 0, 1, 3)
            return

        # Render responsive grid
        cols = max(1, self.width() // 250) if self.width() > 0 else 3

        for index, note in enumerate(filtered):
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

    def _clear_filters(self):
        self.search_input.clear()
        self._set_color_filter(None)

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

    def _delete_selected_notes(self):
        count = len(self.selected_note_ids)
        if count == 0:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete {count} selected note(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            database.delete_multiple_notes(list(self.selected_note_ids))
            self._toggle_selection_mode()
            self.load_notes()

    def _update_selection_ui(self):
        count = len(self.selected_note_ids)
        self.selection_count_label.setText(f"{count} note{'s' if count != 1 else ''} selected")
        self.delete_selected_btn.setEnabled(count > 0)

    def _create_new_note(self):
        """Creates an untitled note and immediately switches to edit mode."""
        initial_color = self.current_color_filter or "#FFF9C4"
        note_id = database.create_note(title="Untitled Note", content="", color_hex=initial_color)
        self.open_note_requested.emit(note_id)

    def _on_card_double_clicked(self, note_id: str):
        self.open_note_requested.emit(note_id)

    def _on_card_color_changed(self, note_id: str, new_color_hex: str):
        database.update_note(note_id, color_hex=new_color_hex)
        for n in self.all_notes:
            if n["id"] == note_id:
                n["color_hex"] = new_color_hex
                break

    def _on_card_duplicate_requested(self, note_id: str):
        new_id = database.duplicate_note(note_id)
        if new_id:
            self.load_notes()

    def _on_card_share_requested(self, note_id: str):
        note = database.get_note(note_id)
        if not note:
            return
        
        title = note.get("title") or "Untitled Note"
        content = note.get("content") or ""

        menu = QMenu(self)
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
                full_html = f"<html><head>{MARKDOWN_PREVIEW_CSS}</head><body>{html_body}</body></html>"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_html)

    def _on_card_delete_requested(self, note_id: str):
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to permanently delete this note?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            database.delete_note(note_id)
            self.load_notes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-layout grid columns if width changed significantly
        if hasattr(self, 'all_notes') and self.all_notes:
            self._filter_and_render_notes()
