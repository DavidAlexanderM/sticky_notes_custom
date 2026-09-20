"""
tag_selector_flyout.py - Lightweight Tag Selection Flyout / Modal for Sticky Notes.
Enables 1-click assigning and unassigning of tags to a note, with Custom Tags
listed first, Predetermined System Tags listed second, and inline tag creation.
"""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QScrollArea, QFrame,
    QCheckBox, QLineEdit, QMessageBox
)
from PySide6.QtGui import QCursor, QPainter, QColor, QBrush, QPen

try:
    from .. import database
    from ..i18n import tr, get_translation_manager
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
except ImportError:
    import database
    from i18n import tr, get_translation_manager
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES


class TagColorDot(QWidget):
    """Miniature anti-aliased vector color dot for tag items."""
    def __init__(self, color_hex: str, size: int = 12, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = (min(self.width(), self.height()) / 2.0) - 1.0
        painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
        painter.setBrush(QBrush(QColor(self.color_hex)))
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.end()


class TagSelectorFlyout(QDialog):
    """
    Tag assignment flyout listing custom tags first, then predetermined tags,
    with instant toggle checkboxes and inline custom tag creation.
    """
    tags_changed = Signal(str, list)  # (note_id, updated_tags_list)

    def __init__(self, note_id: str, parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.current_tags = set(database.get_note_tags(note_id))
        self.theme_mgr = get_theme_manager()
        self.i18n = get_translation_manager()

        self.setWindowTitle(tr("select_tags"))
        self.setFixedSize(280, 380)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

        self._build_ui()

    def _get_palette(self) -> dict:
        is_dark = self.theme_mgr.is_dark_mode()
        fallback_pal = THEME_PALETTES["dark" if is_dark else "light"]
        theme = self.theme_mgr.current_theme
        return THEME_PALETTES.get(theme, fallback_pal) or fallback_pal

    def _build_ui(self):
        pal = self._get_palette()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {pal.get('bg_surface', '#FFFFFF')};
                border: 1.5px solid {pal.get('border', '#E2E8F0')};
                border-radius: 10px;
            }}
            QLabel {{
                color: {pal.get('text_primary', '#0F172A')};
            }}
            QCheckBox {{
                color: {pal.get('text_primary', '#0F172A')};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid {pal['border']};
                background: {pal['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {pal['accent']};
                border-color: {pal['accent']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        header_lbl = QLabel(f"🏷️ <b>{tr('select_tags')}</b>", self)
        header_lbl.setStyleSheet("font-size: 14px;")
        header_row.addWidget(header_lbl)
        header_row.addStretch()

        close_btn = QPushButton("✕", self)
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {pal['text_secondary']};
                font-size: 13px;
                font-weight: bold;
                border-radius: 11px;
            }}
            QPushButton:hover {{
                background-color: {pal['btn_hover']};
                color: {pal['text_primary']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # Scrollable Tags Area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(2, 4, 2, 4)
        self.content_layout.setSpacing(6)

        self._populate_tags()

        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)

        # Bottom row: Quick Add Custom Tag Input
        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self.new_tag_input = QLineEdit(self)
        self.new_tag_input.setPlaceholderText(tr("add_custom_tag"))
        self.new_tag_input.setStyleSheet(f"""
            QLineEdit {{
                background: {pal['input_bg']};
                color: {pal['text_primary']};
                border: 1px solid {pal['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }}
        """)
        self.new_tag_input.returnPressed.connect(self._add_custom_tag)
        add_row.addWidget(self.new_tag_input, 1)

        add_btn = QPushButton("+", self)
        add_btn.setFixedSize(26, 26)
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {pal['accent']};
                color: {pal['accent_text']};
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        add_btn.clicked.connect(self._add_custom_tag)
        add_row.addWidget(add_btn)

        layout.addLayout(add_row)

    def _populate_tags(self):
        # Clear existing items
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        pal = self._get_palette()

        # 1. Custom Tags Section (FIRST in order, as requested)
        custom_tags = database.get_custom_tags()
        if custom_tags:
            cust_header = QLabel(f"<b>{tr('custom_tags_section')}</b>", self.scroll_content)
            cust_header.setStyleSheet(f"font-size: 11px; color: {pal['text_muted']}; text-transform: uppercase;")
            self.content_layout.addWidget(cust_header)

            for tag in custom_tags:
                self._add_tag_checkbox_row(tag["name"], tag.get("color_hex", "#8AB4F8"))

            sep = QFrame(self.scroll_content)
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"background-color: {pal['border']}; max-height: 1px; margin: 4px 0;")
            self.content_layout.addWidget(sep)

        # 2. Predetermined Tags Section (SECOND)
        pred_header = QLabel(f"<b>{tr('predetermined_tags_section')}</b>", self.scroll_content)
        pred_header.setStyleSheet(f"font-size: 11px; color: {pal['text_muted']}; text-transform: uppercase;")
        self.content_layout.addWidget(pred_header)

        for pt in database.PREDETERMINED_TAGS:
            name = tr(pt["key"])
            self._add_tag_checkbox_row(name, pt["color_hex"])

        self.content_layout.addStretch()

    def _add_tag_checkbox_row(self, tag_name: str, color_hex: str):
        row_widget = QWidget(self.scroll_content)
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(8)

        dot = TagColorDot(color_hex, size=11, parent=row_widget)
        row.addWidget(dot)

        cb = QCheckBox(tag_name, row_widget)
        cb.setChecked(tag_name in self.current_tags)
        cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cb.toggled.connect(lambda checked, t=tag_name: self._on_tag_toggled(t, checked))
        row.addWidget(cb, 1)

        self.content_layout.addWidget(row_widget)

    def _on_tag_toggled(self, tag_name: str, checked: bool):
        if checked:
            self.current_tags.add(tag_name)
        else:
            self.current_tags.discard(tag_name)
        
        tags_list = list(self.current_tags)
        database.set_note_tags(self.note_id, tags_list)
        self.tags_changed.emit(self.note_id, tags_list)

    def _add_custom_tag(self):
        text = self.new_tag_input.text().strip()
        if not text:
            return
        
        # Color cycle for custom tags
        custom_colors = ["#F43F5E", "#EC4899", "#8B5CF6", "#6366F1", "#0EA5E9", "#10B981", "#F59E0B"]
        existing_count = len(database.get_custom_tags())
        chosen_color = custom_colors[existing_count % len(custom_colors)]

        created = database.create_custom_tag(text, chosen_color)
        if created:
            self.current_tags.add(text)
            tags_list = list(self.current_tags)
            database.set_note_tags(self.note_id, tags_list)
            self.tags_changed.emit(self.note_id, tags_list)
            self.new_tag_input.clear()
            self._populate_tags()
        else:
            self.new_tag_input.clear()
