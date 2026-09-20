"""
grid_view.py - Main Sticky Notes Grid / Board View.
Features responsive multi-column note layout, color filter chips, live search,
Shift/Ctrl multi-selection, keyboard navigation, and Help & About center.
"""

from typing import Optional, List, Set
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QGridLayout, 
    QFrame, QMessageBox, QFileDialog, QApplication, QMenu
)
from PySide6.QtGui import QCursor, QKeyEvent
import markdown2

try:
    from ..components.note_card import NoteCard
    from ..components.help_dialog import HelpAboutDialog
    from ..components.share_dialog import ShareNoteDialog
    from ..styles import NOTE_COLORS, MARKDOWN_PREVIEW_CSS
    from ..theme_manager import get_theme_manager
    from ..icons import get_themed_icon
    from .. import database
except ImportError:
    from components.note_card import NoteCard
    from components.help_dialog import HelpAboutDialog
    from components.share_dialog import ShareNoteDialog
    from styles import NOTE_COLORS, MARKDOWN_PREVIEW_CSS
    from theme_manager import get_theme_manager
    from icons import get_themed_icon
    import database


class StickyNotesGridView(QWidget):
    """
    Main board displaying sticky notes in a responsive, filterable grid
    with Shift/Ctrl multi-selection and complete keyboard navigation.
    """
    open_note_requested = Signal(str)  # Emits note_id when user opens a note

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GridViewContainer")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.theme_mgr = get_theme_manager()
        self.all_notes: List[dict] = []
        self.note_cards: List[NoteCard] = []
        self.selected_note_ids: Set[str] = set()
        self.current_color_filter: Optional[str] = None
        self.anchor_card_index: int = -1
        self.focused_card_index: int = -1

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 20, 28, 16)
        self.main_layout.setSpacing(14)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.title_label = QLabel("My Notes", self)
        self.title_label.setObjectName("AppHeaderTitle")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Help & Keyboard Shortcuts Button (❓)
        self.help_btn = QPushButton(self)
        self.help_btn.setObjectName("EditorHeaderBtn")
        self.help_btn.setFixedSize(36, 36)
        self.help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.help_btn.setToolTip("Help & Keyboard Shortcuts (F1)")
        self.help_btn.clicked.connect(self._open_help_dialog)
        header_layout.addWidget(self.help_btn)

        # Theme Switcher Button (Icon-Only, System/Dark/Light)
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("ThemeToggleBtn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_btn.customContextMenuRequested.connect(self._show_theme_context_menu)
        header_layout.addWidget(self.theme_btn)

        # "+ New Note" Button
        self.new_note_btn = QPushButton(" New Note", self)
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
        self.search_input.setPlaceholderText("Search notes by title, tag, or content... (Ctrl+F)")
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

        # Bottom Selection Action Bar (Appears automatically when notes are selected)
        self.action_bar = QFrame(self)
        self.action_bar.setObjectName("SelectionActionBar")
        self.action_bar.setVisible(False)
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(14, 8, 14, 8)
        action_layout.setSpacing(12)

        self.selection_count_label = QLabel("0 notes selected", self.action_bar)
        self.selection_count_label.setObjectName("SelectionCountLabel")
        action_layout.addWidget(self.selection_count_label)

        action_layout.addStretch()

        self.select_all_btn = QPushButton(" Select All", self.action_bar)
        self.select_all_btn.setObjectName("SelectAllButton")
        self.select_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_all_btn.clicked.connect(self._select_all_notes)
        action_layout.addWidget(self.select_all_btn)

        self.delete_selected_btn = QPushButton(" Delete Selected", self.action_bar)
        self.delete_selected_btn.setObjectName("DeleteSelectedButton")
        self.delete_selected_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.delete_selected_btn.clicked.connect(self._delete_selected_notes)
        action_layout.addWidget(self.delete_selected_btn)

        self.clear_selection_btn = QPushButton(" Clear", self.action_bar)
        self.clear_selection_btn.setObjectName("SelectModeButton")
        self.clear_selection_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_selection_btn.clicked.connect(self._clear_selection)
        action_layout.addWidget(self.clear_selection_btn)

        self.main_layout.addWidget(self.action_bar)

        self._update_theme_btn_label()
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)

    def _open_help_dialog(self):
        """Displays the Help, Shortcuts, and About Dialog."""
        dialog = HelpAboutDialog(self)
        dialog.exec()

    def _update_theme_btn_label(self):
        """Updates icons across the header and action buttons based on current theme (Icon-only theme switcher)."""
        theme = self.theme_mgr.current_theme
        is_dark = self.theme_mgr.is_dark_mode()
        is_auto = self.theme_mgr.is_system_theme()
        
        # Icon-only theme button with clear state feedback
        mode_desc = f"Auto (Following Windows: {'Dark' if is_dark else 'Light'})" if is_auto else f"{'Dark' if is_dark else 'Light'} (Manual)"
        self.theme_btn.setText("")
        self.theme_btn.setIcon(get_themed_icon("sun" if is_dark else "moon", role="btn_text", theme=theme, size=18))
        self.theme_btn.setToolTip(f"Theme: {mode_desc}\nLeft-click: Cycle theme\nRight-click: Choose theme mode")

        # Help button
        self.help_btn.setIcon(get_themed_icon("help_circle", role="btn_text", theme=theme, size=18))

        # Action buttons
        self.new_note_btn.setIcon(get_themed_icon("plus", role="white", theme=theme, size=16))
        self.select_all_btn.setIcon(get_themed_icon("check", role="btn_text", theme=theme, size=15))
        self.delete_selected_btn.setIcon(get_themed_icon("trash", role="white", theme=theme, size=15))
        self.clear_selection_btn.setIcon(get_themed_icon("close", role="btn_text", theme=theme, size=14))

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
        self._update_theme_btn_label()

    def _toggle_theme(self):
        self.theme_mgr.toggle_theme()
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
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.note_cards.clear()
        self.selected_note_ids.clear()
        self.anchor_card_index = -1
        self.focused_card_index = -1
        self._update_selection_ui()

        search_query = self.search_input.text().strip().lower()

        filtered = []
        for note in self.all_notes:
            if self.current_color_filter and note.get("color_hex") != self.current_color_filter:
                continue
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
                title_lbl.setObjectName("EmptyStateTitle")
                btn_clear = QPushButton("Clear Filter", empty_frame)
                btn_clear.setObjectName("SelectModeButton")
                btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_clear.clicked.connect(self._clear_filters)
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(btn_clear, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                icon_lbl = QLabel("📝", empty_frame)
                icon_lbl.setStyleSheet("font-size: 36px;")
                title_lbl = QLabel("No notes yet.", empty_frame)
                title_lbl.setObjectName("EmptyStateTitle")
                sub_lbl = QLabel("Click '+ New Note' to create your first sticky note!", empty_frame)
                sub_lbl.setObjectName("EmptyStateSubtitle")
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(sub_lbl, 0, Qt.AlignmentFlag.AlignCenter)

            self.grid_layout.addWidget(empty_frame, 0, 0, 1, 3)
            return

        cols = max(1, self.width() // 250) if self.width() > 0 else 3

        for index, note in enumerate(filtered):
            row = index // cols
            col = index % cols
            
            card = NoteCard(note, self.grid_content)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.clicked.connect(self._on_card_clicked)
            card.color_changed.connect(self._on_card_color_changed)
            card.duplicate_requested.connect(self._on_card_duplicate_requested)
            card.share_requested.connect(self._on_card_share_requested)
            card.delete_requested.connect(self._on_card_delete_requested)
            card.selection_toggled.connect(self._on_card_selection_toggled)
            
            self.grid_layout.addWidget(card, row, col)
            self.note_cards.append(card)

    def _clear_filters(self):
        self.search_input.clear()
        self._set_color_filter(None)

    def _on_card_clicked(self, note_id: str, shift_held: bool, ctrl_held: bool):
        """
        Standard desktop multi-selection logic:
        - Shift+Click: Extend continuous range selection from anchor to target.
        - Ctrl+Click: Toggle selection of target item in a multi-item group.
        - Normal Click: Focus note, or single select if previously multiple were selected.
        """
        target_idx = -1
        for idx, c in enumerate(self.note_cards):
            if c.note_id == note_id:
                target_idx = idx
                break

        if target_idx == -1:
            return

        if shift_held and self.anchor_card_index != -1:
            start = min(self.anchor_card_index, target_idx)
            end = max(self.anchor_card_index, target_idx)
            if not ctrl_held:
                self.selected_note_ids.clear()
            for i in range(start, end + 1):
                self.selected_note_ids.add(self.note_cards[i].note_id)
            self.focused_card_index = target_idx
        elif ctrl_held:
            if note_id in self.selected_note_ids:
                self.selected_note_ids.remove(note_id)
            else:
                self.selected_note_ids.add(note_id)
            self.anchor_card_index = target_idx
            self.focused_card_index = target_idx
        else:
            # Simple click: if multiple were selected, clear selection and select/focus this card
            self.selected_note_ids.clear()
            self.anchor_card_index = target_idx
            self.focused_card_index = target_idx

        self._update_selection_ui()

    def _on_card_selection_toggled(self, note_id: str, is_selected: bool):
        if is_selected:
            self.selected_note_ids.add(note_id)
        else:
            self.selected_note_ids.discard(note_id)
        self._update_selection_ui()

    def _clear_selection(self):
        """Clears all selected notes."""
        self.selected_note_ids.clear()
        self._update_selection_ui()

    def _select_all_notes(self):
        all_selected = len(self.selected_note_ids) == len(self.note_cards) and len(self.note_cards) > 0
        if all_selected:
            self.selected_note_ids.clear()
        else:
            self.selected_note_ids = {card.note_id for card in self.note_cards}
            
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
            self.selected_note_ids.clear()
            self.load_notes()

    def _update_selection_ui(self):
        """Refreshes card visual selection and focuses, and manages action bar visibility."""
        count = len(self.selected_note_ids)
        self.action_bar.setVisible(count > 0)
        self.selection_count_label.setText(f"{count} note{'s' if count != 1 else ''} selected")
        self.delete_selected_btn.setEnabled(count > 0)
        
        all_selected = count == len(self.note_cards) and count > 0
        self.select_all_btn.setText(" Deselect All" if all_selected else " Select All")

        for idx, card in enumerate(self.note_cards):
            card.set_selected(card.note_id in self.selected_note_ids)
            card.set_focused(idx == self.focused_card_index)

    def keyPressEvent(self, event: QKeyEvent):
        """Comprehensive keyboard navigation across the sticky notes grid."""
        key = event.key()
        modifiers = event.modifiers()
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        ctrl_held = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        # F1 or Ctrl+H: Open Help Dialog
        if key == Qt.Key.Key_F1 or (ctrl_held and key == Qt.Key.Key_H):
            self._open_help_dialog()
            return

        # Ctrl+N: Create new note
        if ctrl_held and key == Qt.Key.Key_N:
            self._create_new_note()
            return

        # Ctrl+F: Focus search input
        if ctrl_held and key == Qt.Key.Key_F:
            self.search_input.setFocus()
            self.search_input.selectAll()
            return

        # Ctrl+A: Select all notes
        if ctrl_held and key == Qt.Key.Key_A:
            self._select_all_notes()
            return

        # Escape: Clear selection or clear search
        if key == Qt.Key.Key_Escape:
            if self.selected_note_ids:
                self._clear_selection()
            elif self.search_input.text():
                self.search_input.clear()
            return

        # Delete / Backspace: Delete selected or focused note
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_note_ids:
                self._delete_selected_notes()
            elif 0 <= self.focused_card_index < len(self.note_cards):
                self._on_card_delete_requested(self.note_cards[self.focused_card_index].note_id)
            return

        # Enter / Return: Open focused or selected note
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if 0 <= self.focused_card_index < len(self.note_cards):
                self.open_note_requested.emit(self.note_cards[self.focused_card_index].note_id)
                return
            elif len(self.selected_note_ids) == 1:
                note_id = next(iter(self.selected_note_ids))
                self.open_note_requested.emit(note_id)
                return

        # Arrow key navigation
        cols = max(1, self.width() // 250) if self.width() > 0 else 3
        num_cards = len(self.note_cards)
        if num_cards == 0:
            super().keyPressEvent(event)
            return

        new_idx = self.focused_card_index
        if key == Qt.Key.Key_Right:
            new_idx = 0 if new_idx < 0 else min(num_cards - 1, new_idx + 1)
        elif key == Qt.Key.Key_Left:
            new_idx = 0 if new_idx < 0 else max(0, new_idx - 1)
        elif key == Qt.Key.Key_Down:
            new_idx = 0 if new_idx < 0 else min(num_cards - 1, new_idx + cols)
        elif key == Qt.Key.Key_Up:
            new_idx = 0 if new_idx < 0 else max(0, new_idx - cols)
        else:
            super().keyPressEvent(event)
            return

        if new_idx != self.focused_card_index:
            if shift_held:
                if self.anchor_card_index < 0:
                    self.anchor_card_index = self.focused_card_index if self.focused_card_index >= 0 else 0
                self.selected_note_ids.clear()
                start = min(self.anchor_card_index, new_idx)
                end = max(self.anchor_card_index, new_idx)
                for i in range(start, end + 1):
                    self.selected_note_ids.add(self.note_cards[i].note_id)
            else:
                self.anchor_card_index = new_idx

            self.focused_card_index = new_idx
            self._update_selection_ui()

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
        dialog = ShareNoteDialog(title, content, self)
        dialog.exec()

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
        if hasattr(self, 'all_notes') and self.all_notes:
            self._filter_and_render_notes()
