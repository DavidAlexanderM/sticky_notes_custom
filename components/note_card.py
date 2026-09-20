from datetime import datetime
import re
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMenu, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QEnterEvent

try:
    from .color_picker_flyout import ColorPickerFlyout
    from ..styles import is_dark_color
    from ..icons import get_icon
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from styles import is_dark_color
    from icons import get_icon


class NoteCard(QFrame):
    """
    Modern Sticky Note card widget with hover elevation, 1-click Quick Action menu (⋯),
    markdown preview excerpt, and dynamic theme contrast.
    """
    double_clicked = Signal(str)          # Emits note_id
    color_changed = Signal(str, str)      # Emits (note_id, new_color_hex)
    delete_requested = Signal(str)       # Emits note_id
    duplicate_requested = Signal(str)    # Emits note_id
    share_requested = Signal(str)        # Emits note_id
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

        # Soft shadow for card elevation
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(12)
        self.shadow.setColor(QColor(0, 0, 0, 32))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(6)

        # Top row (Title + Menu button / Selection checkbox)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        # Note Title
        self.title_label = QLabel(self.note.get("title") or "Untitled", self)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(44)
        top_row.addWidget(self.title_label, 1)

        # Quick Action Button (⋯)
        self.menu_btn = QPushButton(self)
        self.menu_btn.setObjectName("CardMenuBtn")
        self.menu_btn.setFixedSize(26, 24)
        self.menu_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.menu_btn.setToolTip("Note Options")
        self.menu_btn.clicked.connect(self._on_menu_btn_clicked)
        top_row.addWidget(self.menu_btn)

        # Checkbox indicator for multi-selection mode
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

        # Media Badges row (Photos, Audio, Video indicators)
        badges = self._get_media_badges(self.note.get("content", ""))
        self.badge_label = QLabel(badges, self)
        self.badge_label.setObjectName("CardBadges")
        self.badge_label.setVisible(bool(badges))
        layout.addWidget(self.badge_label)

        # Bottom row (timestamp + palette hint)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        date_str = self._format_date(self.note.get("updated_at", ""))
        self.date_label = QLabel(date_str, self)
        self.date_label.setObjectName("CardDate")
        bottom_row.addWidget(self.date_label)

        bottom_row.addStretch()
        
        self.palette_icon_btn = QPushButton(self)
        self.palette_icon_btn.setObjectName("CardPaletteBtn")
        self.palette_icon_btn.setFixedSize(22, 20)
        self.palette_icon_btn.setToolTip("Change Note Color")
        self.palette_icon_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.palette_icon_btn.clicked.connect(lambda: self._show_color_flyout(self.mapToGlobal(QPoint(20, 160))))
        bottom_row.addWidget(self.palette_icon_btn)

        layout.addLayout(bottom_row)

        self._apply_style()

    def enterEvent(self, event: QEnterEvent):
        """Elevate shadow smoothly on hover."""
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 6)
        self.shadow.setColor(QColor(0, 0, 0, 48))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Restore default elevation."""
        self.shadow.setBlurRadius(12)
        self.shadow.setOffset(0, 3)
        self.shadow.setColor(QColor(0, 0, 0, 32))
        super().leaveEvent(event)

    def set_selection_mode(self, enabled: bool):
        self.selection_mode = enabled
        self.check_indicator.setVisible(enabled)
        self.menu_btn.setVisible(not enabled)
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
        dark_card = is_dark_color(self.color_hex)
        if dark_card:
            text_color = "#FFFFFF"
            subtext_color = "#F1F5F9"
            date_color = "#CBD5E1"
            badge_bg = "rgba(255, 255, 255, 0.18)"
            border_color = "rgba(255, 255, 255, 0.25)"
            menu_hover = "rgba(255, 255, 255, 0.20)"
        else:
            text_color = "#0F172A"
            subtext_color = "#1E293B"
            date_color = "#475569"
            badge_bg = "rgba(0, 0, 0, 0.08)"
            border_color = "rgba(0, 0, 0, 0.14)"
            menu_hover = "rgba(0, 0, 0, 0.08)"
        
        if self.is_selected:
            border_style = "2.5px solid #2563EB"
        else:
            border_style = f"1.5px solid {border_color}"

        self.menu_btn.setIcon(get_icon("more_horizontal", color=text_color, size=16))
        self.palette_icon_btn.setIcon(get_icon("palette", color=date_color, size=14))

        self.setStyleSheet(f"""
            QFrame#NoteCardFrame {{
                background-color: {self.color_hex};
                border: {border_style};
                border-radius: 12px;
            }}
            QFrame#NoteCardFrame:hover {{
                border: 2px solid #2563EB;
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
            QLabel#CardBadges {{
                font-size: 11px;
                font-weight: 600;
                color: {text_color};
                background-color: {badge_bg};
                border-radius: 6px;
                padding: 3px 8px;
            }}
            QLabel#CardDate {{
                color: {date_color};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }}
            QPushButton#CardMenuBtn, QPushButton#CardPaletteBtn {{
                background-color: transparent;
                border: none;
                border-radius: 5px;
                padding: 2px;
            }}
            QPushButton#CardMenuBtn:hover, QPushButton#CardPaletteBtn:hover {{
                background-color: {menu_hover};
            }}
        """)

    def _get_media_badges(self, content: str) -> str:
        """Returns visual indicators for attached media types."""
        if not content:
            return ""
        badges = []
        if "![" in content or any(ext in content.lower() for ext in (".png)", ".jpg)", ".jpeg)", ".gif)", ".webp)")):
            badges.append("Photo")
        if "Voice Note" in content or any(ext in content.lower() for ext in (".m4a)", ".mp3)", ".wav)")):
            badges.append("Audio")
        if "Watch Video" in content or any(ext in content.lower() for ext in (".mp4)", ".webm)", ".mkv)")):
            badges.append("Video")
        return "  •  ".join(badges)

    def _clean_excerpt(self, markdown_text: str) -> str:
        """Strip markdown syntax to create a clean, elegant note excerpt."""
        if not markdown_text:
            return "Empty note"

        # Remove image and media links (already displayed in media badges row)
        text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
        text = re.sub(r'[🎵🎥]\s*\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

        # Strip code block fences
        text = re.sub(r'```[\s\S]*?```', '', text)

        # Clean task checklist checkboxes into readable bullets
        text = re.sub(r'^\s*[-*+]\s*\[[ xX]\]\s*', '• ', text, flags=re.MULTILINE)

        # Normalize bullet markers
        text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)

        # Remove headers and inline formatting characters
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'[*_`~<>]', '', text)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "Empty note"

        clean = "  ".join(lines)
        return clean[:95] + ("..." if len(clean) > 95 else "")

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

    def _on_menu_btn_clicked(self):
        """Opens quick action context menu right beneath the ⋯ button."""
        pos = self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height()))
        self._show_card_menu(pos)

    def _show_card_menu(self, global_pos: QPoint):
        """Displays modern Quick Action Menu with vector icons."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px 6px 10px;
                font-size: 13px;
                border-radius: 4px;
                color: #0F172A;
            }
            QMenu::item:selected {
                background-color: #F1F5F9;
                color: #2563EB;
            }
        """)

        act_edit = menu.addAction(get_icon("edit", color="#0F172A", size=16), "Open Note")
        act_dup = menu.addAction(get_icon("copy", color="#0F172A", size=16), "Duplicate")
        act_color = menu.addAction(get_icon("palette", color="#0F172A", size=16), "Change Color")
        act_share = menu.addAction(get_icon("share", color="#0F172A", size=16), "Share / Export")
        menu.addSeparator()
        act_delete = menu.addAction(get_icon("trash", color="#DC2626", size=16), "Delete Note")

        action = menu.exec(global_pos)
        if action == act_edit:
            self.double_clicked.emit(self.note_id)
        elif action == act_dup:
            self.duplicate_requested.emit(self.note_id)
        elif action == act_color:
            self._show_color_flyout(global_pos)
        elif action == act_share:
            self.share_requested.emit(self.note_id)
        elif action == act_delete:
            self.delete_requested.emit(self.note_id)

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
