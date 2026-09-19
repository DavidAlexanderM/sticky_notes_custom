from datetime import datetime
import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QCursor, QMouseEvent
try:
    from .color_picker_flyout import ColorPickerFlyout
    from ..styles import is_dark_color
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from styles import is_dark_color

class NoteCard(QFrame):
    """
    A sticky note card widget displaying title, markdown excerpt, and timestamp.
    """
    double_clicked = Signal(str)       # Emits note_id
    color_changed = Signal(str, str)   # Emits (note_id, new_color_hex)
    delete_requested = Signal(str)    # Emits note_id
    duplicate_requested = Signal(str) # Emits note_id
    share_requested = Signal(str)     # Emits note_id
    selection_toggled = Signal(str, bool) # Emits (note_id, is_selected)

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note = note
        self.note_id = note["id"]
        self.color_hex = note.get("color_hex", "#FFF9C4")
        self.selection_mode = False
        self.is_selected = False
        
        self.setFixedSize(220, 200)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("NoteCardFrame")

        # Soft shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(12)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Top row (Title + Checkbox for multi-select)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        # Note Title
        self.title_label = QLabel(self.note.get("title") or "Untitled", self)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(44)
        top_row.addWidget(self.title_label, 1)

        # Checkbox indicator for selection mode
        self.check_indicator = QLabel("⚪", self)
        self.check_indicator.setObjectName("CheckIndicator")
        self.check_indicator.setVisible(False)
        self.check_indicator.setFixedSize(20, 20)
        self.check_indicator.setStyleSheet("font-size: 13px; background: transparent;")
        top_row.addWidget(self.check_indicator)

        layout.addLayout(top_row)

        # Note Preview / Excerpt
        self.snippet_label = QLabel(self._clean_excerpt(self.note.get("content", "")), self)
        self.snippet_label.setObjectName("CardSnippet")
        self.snippet_label.setWordWrap(True)
        self.snippet_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.snippet_label, 1)

        # Bottom row (timestamp + right click hint)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        date_str = self._format_date(self.note.get("updated_at", ""))
        self.date_label = QLabel(date_str, self)
        self.date_label.setObjectName("CardDate")
        bottom_row.addWidget(self.date_label)

        bottom_row.addStretch()
        
        hint_label = QLabel("🎨", self)
        hint_label.setToolTip("Right-click for colors")
        hint_label.setStyleSheet("opacity: 0.6; font-size: 11px;")
        bottom_row.addWidget(hint_label)

        layout.addLayout(bottom_row)

        self._apply_style()

    def set_selection_mode(self, enabled: bool):
        self.selection_mode = enabled
        self.check_indicator.setVisible(enabled)
        if not enabled:
            self.is_selected = False
            self.check_indicator.setText("⚪")
        self._apply_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.check_indicator.setText("🔵" if selected else "⚪")
        self._apply_style()

    def toggle_selection(self):
        self.set_selected(not self.is_selected)
        self.selection_toggled.emit(self.note_id, self.is_selected)

    def update_color(self, new_hex: str):
        self.color_hex = new_hex
        self._apply_style()

    def _apply_style(self):
        dark_mode = is_dark_color(self.color_hex)
        text_color = "#FFFFFF" if dark_mode else "#1F2937"
        subtext_color = "#D1D5DB" if dark_mode else "#4B5563"
        muted_color = "#9CA3AF" if dark_mode else "#6B7280"
        
        if self.is_selected:
            border_style = "2.5px solid #0067C0"
        else:
            border_color = "rgba(255, 255, 255, 0.15)" if dark_mode else "rgba(0, 0, 0, 0.08)"
            border_style = f"1px solid {border_color}"

        self.setStyleSheet(f"""
            QFrame#NoteCardFrame {{
                background-color: {self.color_hex};
                border: {border_style};
                border-radius: 12px;
            }}
            QFrame#NoteCardFrame:hover {{
                border: 2px solid #0067C0;
            }}
            QLabel#CardTitle {{
                color: {text_color};
                font-weight: 700;
                font-size: 14px;
                background: transparent;
            }}
            QLabel#CardSnippet {{
                color: {subtext_color};
                font-size: 12px;
                line-height: 1.4;
                background: transparent;
            }}
            QLabel#CardDate {{
                color: {muted_color};
                font-size: 10px;
                font-weight: 500;
                background: transparent;
            }}
        """)

    def _clean_excerpt(self, markdown_text: str) -> str:
        """Strip markdown syntax to create a clean excerpt."""
        if not markdown_text:
            return "Empty note"
        # Remove headers, bullets, code fences
        text = re.sub(r'#+\s*', '', markdown_text)
        text = re.sub(r'[*_`~]', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean = " ".join(lines)
        return clean[:90] + ("..." if len(clean) > 90 else "")

    def _format_date(self, iso_date: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%b %d, %I:%M %p")
        except Exception:
            return "Recently"

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.selection_mode:
            self.toggle_selection()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.note_id)

    def mousePressEvent(self, event: QMouseEvent):
        if self.selection_mode and event.button() == Qt.MouseButton.LeftButton:
            self.toggle_selection()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._show_color_flyout(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def _show_color_flyout(self, global_pos):
        flyout = ColorPickerFlyout(self)
        flyout.color_selected.connect(self._on_flyout_color_selected)
        flyout.duplicate_requested.connect(lambda: self.duplicate_requested.emit(self.note_id))
        flyout.share_requested.connect(lambda: self.share_requested.emit(self.note_id))
        flyout.delete_requested.connect(lambda: self.delete_requested.emit(self.note_id))
        flyout.move(global_pos.x() - 20, global_pos.y() - 20)
        flyout.show()

    def _on_flyout_color_selected(self, hex_val: str):
        self.update_color(hex_val)
        self.color_changed.emit(self.note_id, hex_val)

