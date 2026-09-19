from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtGui import QCursor
try:
    from ..components.note_card import NoteCard
    from .. import database
except ImportError:
    from components.note_card import NoteCard
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

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 20)
        main_layout.setSpacing(18)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        self.title_label = QLabel("My Notes", self)
        self.title_label.setObjectName("AppHeaderTitle")
        title_col.addWidget(self.title_label)

        self.subtitle_label = QLabel("Double-click to edit • Right-click for colors", self)
        self.subtitle_label.setObjectName("AppHeaderSubtitle")
        title_col.addWidget(self.subtitle_label)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # "+ New Note" Button
        self.new_note_btn = QPushButton("+ New Note", self)
        self.new_note_btn.setObjectName("NewNoteButton")
        self.new_note_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_note_btn.clicked.connect(self._create_new_note)
        header_layout.addWidget(self.new_note_btn)

        main_layout.addLayout(header_layout)

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
        main_layout.addWidget(self.scroll_area)

    def load_notes(self):
        """Reloads all notes from the database and populates the grid."""
        # Clear existing cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.note_cards.clear()

        notes = database.get_all_notes()
        
        if not notes:
            empty_label = QLabel("No notes yet. Click '+ New Note' to create your first sticky note!", self)
            empty_label.setStyleSheet("color: #6B7280; font-size: 14px; margin-top: 40px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        # Calculate columns based on width (approx 3 cards per row for 800px width)
        cols = max(1, self.width() // 250) if self.width() > 0 else 3

        for index, note in enumerate(notes):
            row = index // cols
            col = index % cols
            
            card = NoteCard(note, self.grid_content)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.color_changed.connect(self._on_card_color_changed)
            card.delete_requested.connect(self._on_card_delete_requested)
            
            self.grid_layout.addWidget(card, row, col)
            self.note_cards.append(card)

    def _create_new_note(self):
        """Creates a blank note and immediately opens the editor."""
        new_id = database.create_note(title="Untitled Note", content="", color_hex="#FFF9C4")
        self.open_note_requested.emit(new_id)

    def _on_card_double_clicked(self, note_id: str):
        self.open_note_requested.emit(note_id)

    def _on_card_color_changed(self, note_id: str, new_color_hex: str):
        database.update_note(note_id, color_hex=new_color_hex)

    def _on_card_delete_requested(self, note_id: str):
        database.delete_note(note_id)
        self.load_notes()

    def resizeEvent(self, event):
        """Re-layout cards when window is resized."""
        super().resizeEvent(event)
        # Only rearrange if count > 0 and width has meaningful change
        if self.note_cards:
            cols = max(1, self.width() // 250)
            for index, card in enumerate(self.note_cards):
                self.grid_layout.removeWidget(card)
                row = index // cols
                col = index % cols
                self.grid_layout.addWidget(card, row, col)
