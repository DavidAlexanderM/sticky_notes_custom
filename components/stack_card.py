"""
stack_card.py - Physical 3D Note Stack Widget for Sticky Notes.
Renders a physical pile of sticky notes with slightly shifted, rotated multicolor paper layers,
interactive drop target for dragging notes into stacks, and inline F2/double-click renaming.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal, QPoint, QRectF
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMenu, QLineEdit, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QTransform, 
    QCursor, QMouseEvent, QKeyEvent, QPaintEvent
)

try:
    from .color_picker_flyout import ColorPickerFlyout
    from ..styles import is_dark_color, THEME_PALETTES
    from ..icons import get_icon, get_themed_icon
    from ..theme_manager import get_theme_manager
    from ..i18n import tr
    from .. import database
except ImportError:
    from components.color_picker_flyout import ColorPickerFlyout
    from styles import is_dark_color, THEME_PALETTES
    from icons import get_icon, get_themed_icon
    from theme_manager import get_theme_manager
    from i18n import tr
    import database


class StackCard(QFrame):
    """
    Card representing a physical stack/collection of sticky notes.
    Features 3D tilted multicolor paper sheets, inline F2/double-click renaming,
    and drag & drop acceptance.
    """
    open_stack_requested = Signal(str)           # Emits project_id
    note_dropped_into_stack = Signal(str, str)   # Emits (note_id, project_id)
    dissolve_requested = Signal(str)             # Emits project_id
    delete_requested = Signal(str)               # Emits project_id
    color_changed = Signal(str, str)             # Emits (project_id, new_color_hex)
    renamed = Signal(str, str)                   # Emits (project_id, new_name)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        self.project_id = project["id"]
        self.color_hex = project.get("color_hex") or project.get("color") or "#FFF9C4"
        self.note_count = project.get("note_count", 0)
        self.is_drop_target = False
        self.is_focused = False

        self.setFixedSize(220, 200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAcceptDrops(True)
        self.setObjectName("StackCardFrame")

        # Fetch layer colors and notes preview
        self.layer_colors = self._get_layer_colors()
        self.notes_preview = database.get_project_notes_preview(self.project_id, limit=3)

        # Soft shadow for card elevation
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(14)
        self.shadow.setColor(QColor(0, 0, 0, 36))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

        # Content Layout over the top sheet
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(6)

        # Top row: Stack Badge & Options Button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        count_suffix = tr("one_note_count") if self.note_count == 1 else tr("notes_count", count=self.note_count)
        count_text = f"📚 {count_suffix}"
        self.badge_lbl = QLabel(count_text, self)
        self.badge_lbl.setObjectName("StackBadge")
        top_row.addWidget(self.badge_lbl, 1)

        self.menu_btn = QPushButton(self)
        self.menu_btn.setObjectName("CardMenuBtn")
        self.menu_btn.setFixedSize(26, 24)
        self.menu_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.menu_btn.setToolTip(tr("stack_options"))
        self.menu_btn.clicked.connect(self._on_menu_clicked)
        top_row.addWidget(self.menu_btn)

        self.main_layout.addLayout(top_row)

        # Stack Name Row (Display Label & Inline QLineEdit)
        self.name_label = QLabel(self.project.get("name", "Stack"), self)
        self.name_label.setObjectName("StackTitle")
        self.name_label.setWordWrap(True)
        self.name_label.setToolTip(tr("rename_stack_hint"))
        self.main_layout.addWidget(self.name_label)

        # Inline editor (hidden until F2 / double-click)
        self.name_edit = QLineEdit(self)
        self.name_edit.setObjectName("StackTitleEdit")
        self.name_edit.setVisible(False)
        self.name_edit.returnPressed.connect(self._commit_rename)
        self.main_layout.addWidget(self.name_edit)

        # Preview of notes inside stack
        self.preview_layout = QVBoxLayout()
        self.preview_layout.setSpacing(3)
        self.preview_layout.setContentsMargins(0, 4, 0, 0)
        self._populate_preview()
        self.main_layout.addLayout(self.preview_layout)

        self.main_layout.addStretch()

        # Bottom subtle hint
        self.hint_label = QLabel(tr("double_click_open_stack"), self)
        self.hint_label.setObjectName("StackHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(self.hint_label)

        self._apply_style()

    def _get_layer_colors(self) -> List[str]:
        """Retrieves colors of notes in stack, or generates complementary fallback colors."""
        note_colors = database.get_project_note_colors(self.project_id, limit=3)
        fallbacks = ["#FFF9C4", "#E8F5E9", "#E1F5FE", "#FCE4EC", "#FFE0B2"]
        
        # Ensure we have at least 3 colors for the 3 visual layers
        colors = []
        if self.color_hex:
            colors.append(self.color_hex)
        for c in note_colors:
            if c not in colors:
                colors.append(c)
        for fb in fallbacks:
            if fb not in colors:
                colors.append(fb)
            if len(colors) >= 3:
                break
        return colors[:3]

    def _populate_preview(self):
        """Displays small bullet items showing titles of notes in this stack."""
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.notes_preview:
            empty_lbl = QLabel("(Empty stack • Drag notes here)", self)
            empty_lbl.setObjectName("StackPreviewEmpty")
            self.preview_layout.addWidget(empty_lbl)
            return

        for n in self.notes_preview:
            title = n.get("title") or "Untitled note"
            if len(title) > 22:
                title = title[:20] + "…"
            bullet = QLabel(f"• {title}", self)
            bullet.setObjectName("StackPreviewItem")
            self.preview_layout.addWidget(bullet)

    def _apply_style(self):
        dark_card = is_dark_color(self.color_hex)
        if dark_card:
            text_color = "#FFFFFF"
            subtext_color = "#E2E8F0"
            hint_color = "#CBD5E1"
            badge_bg = "rgba(255, 255, 255, 0.22)"
            menu_hover = "rgba(255, 255, 255, 0.20)"
            input_bg = "rgba(0, 0, 0, 0.40)"
        else:
            text_color = "#0F172A"
            subtext_color = "#1E293B"
            hint_color = "#64748B"
            badge_bg = "rgba(0, 0, 0, 0.09)"
            menu_hover = "rgba(0, 0, 0, 0.08)"
            input_bg = "rgba(255, 255, 255, 0.70)"

        self.menu_btn.setIcon(get_icon("more_horizontal", color=text_color, size=16))

        self.setStyleSheet(f"""
            QLabel#StackBadge {{
                font-size: 11px;
                font-weight: 700;
                color: {text_color};
                background-color: {badge_bg};
                border-radius: 6px;
                padding: 3px 7px;
            }}
            QLabel#StackTitle {{
                font-size: 16px;
                font-weight: 800;
                color: {text_color};
                background: transparent;
            }}
            QLineEdit#StackTitleEdit {{
                font-size: 15px;
                font-weight: 700;
                color: {text_color};
                background-color: {input_bg};
                border: 1.5px solid #2563EB;
                border-radius: 6px;
                padding: 2px 6px;
            }}
            QLabel#StackPreviewItem {{
                font-size: 12px;
                color: {subtext_color};
                background: transparent;
            }}
            QLabel#StackPreviewEmpty {{
                font-size: 11px;
                font-style: italic;
                color: {hint_color};
                background: transparent;
            }}
            QLabel#StackHint {{
                font-size: 10px;
                font-weight: 600;
                color: {hint_color};
                background: transparent;
            }}
            QPushButton#CardMenuBtn {{
                background-color: transparent;
                border: none;
                border-radius: 5px;
                padding: 2px;
            }}
            QPushButton#CardMenuBtn:hover {{
                background-color: {menu_hover};
            }}
        """)

    def paintEvent(self, event: QPaintEvent):
        """Paints 3 slightly shifted, rotated paper sheets representing a physical note stack."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        # Layer 3: Bottom sheet (tilted -3.5 deg, shifted left/down)
        c3 = QColor(self.layer_colors[2] if len(self.layer_colors) > 2 else "#E1F5FE")
        painter.save()
        painter.translate(cx - 3.0, cy + 4.0)
        painter.rotate(-3.8)
        painter.translate(-cx, -cy)
        # Drop shadow for layer 3
        painter.setBrush(QBrush(QColor(0, 0, 0, 18)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(10, 10, w - 20, h - 20), 10, 10)
        # Paper 3
        painter.setBrush(QBrush(c3))
        painter.setPen(QPen(QColor(0, 0, 0, 45), 1))
        painter.drawRoundedRect(QRectF(8, 8, w - 18, h - 18), 10, 10)
        painter.restore()

        # Layer 2: Middle sheet (tilted +3.2 deg, shifted right/down)
        c2 = QColor(self.layer_colors[1] if len(self.layer_colors) > 1 else "#E8F5E9")
        painter.save()
        painter.translate(cx + 4.0, cy + 2.0)
        painter.rotate(3.2)
        painter.translate(-cx, -cy)
        # Drop shadow for layer 2
        painter.setBrush(QBrush(QColor(0, 0, 0, 20)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(10, 10, w - 20, h - 20), 10, 10)
        # Paper 2
        painter.setBrush(QBrush(c2))
        painter.setPen(QPen(QColor(0, 0, 0, 45), 1))
        painter.drawRoundedRect(QRectF(8, 8, w - 18, h - 18), 10, 10)
        painter.restore()

        # Layer 1: Top sheet (facing straight with soft shadow)
        c1 = QColor(self.color_hex)
        painter.save()
        # Drop shadow for top paper
        painter.setBrush(QBrush(QColor(0, 0, 0, 24)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(9, 9, w - 16, h - 16), 11, 11)

        # Top paper body
        painter.setBrush(QBrush(c1))
        if self.is_drop_target:
            # Active drop glow border
            painter.setPen(QPen(QColor("#2563EB"), 3))
        elif self.hasFocus():
            painter.setPen(QPen(QColor("#2563EB"), 2, Qt.PenStyle.DashLine))
        else:
            border_alpha = 40 if is_dark_color(self.color_hex) else 30
            painter.setPen(QPen(QColor(0, 0, 0, border_alpha), 1.5))
        painter.drawRoundedRect(QRectF(7, 7, w - 14, h - 14), 11, 11)
        painter.restore()

        super().paintEvent(event)

    def start_rename(self):
        """Initiates inline rename mode."""
        self.name_label.setVisible(False)
        self.name_edit.setText(self.project.get("name", "Stack"))
        self.name_edit.setVisible(True)
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _commit_rename(self):
        """Saves inline edited name to database."""
        new_name = self.name_edit.text().strip()
        if new_name and new_name != self.project.get("name"):
            database.update_project(self.project_id, name=new_name)
            self.project["name"] = new_name
            self.name_label.setText(new_name)
            self.renamed.emit(self.project_id, new_name)
        self.name_edit.setVisible(False)
        self.name_label.setVisible(True)

    def keyPressEvent(self, event: QKeyEvent):
        if self.name_edit.isVisible():
            if event.key() == Qt.Key.Key_Escape:
                self.name_edit.setVisible(False)
                self.name_label.setVisible(True)
                return
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_F2:
            self.start_rename()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.open_stack_requested.emit(self.project_id)
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # If double clicked directly on title label, start rename
            if self.name_label.geometry().contains(event.position().toPoint()):
                self.start_rename()
            else:
                self.open_stack_requested.emit(self.project_id)
            return
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-stickynote-id"):
            event.acceptProposedAction()
            self.is_drop_target = True
            self.update()

    def dragLeaveEvent(self, event):
        self.is_drop_target = False
        self.update()

    def dropEvent(self, event):
        self.is_drop_target = False
        self.update()
        if event.mimeData().hasFormat("application/x-stickynote-id"):
            raw = event.mimeData().data("application/x-stickynote-id")
            note_id = bytes(raw).decode("utf-8")
            database.move_notes_to_project([note_id], self.project_id)
            event.acceptProposedAction()
            self.note_dropped_into_stack.emit(note_id, self.project_id)

    def _on_menu_clicked(self):
        pos = self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height()))
        self._show_menu(pos)

    def _show_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        theme_mgr = get_theme_manager()
        theme = theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])
        is_dark = theme_mgr.is_dark_mode()

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
            QMenu::separator {{
                height: 1px;
                background-color: {pal.get('border_subtle', '#2D2E30' if is_dark else '#E2E8F0')};
                margin: 4px 6px;
            }}
        """)

        act_open = menu.addAction(get_themed_icon("layers", role="btn_text", theme=theme, size=15), tr("open_stack"))
        act_rename = menu.addAction(get_themed_icon("edit", role="btn_text", theme=theme, size=15), tr("rename_stack"))
        act_color = menu.addAction(get_icon("palette", color=pal.get("btn_text", "#000"), size=15), tr("change_stack_color"))
        menu.addSeparator()
        act_dissolve = menu.addAction(tr("unstack_all_notes"))
        act_delete = menu.addAction(get_icon("trash", color="#EF4444", size=15), tr("delete_stack_and_notes"))

        action = menu.exec(global_pos)
        if action == act_open:
            self.open_stack_requested.emit(self.project_id)
        elif action == act_rename:
            self.start_rename()
        elif action == act_color:
            self._show_color_flyout(global_pos)
        elif action == act_dissolve:
            database.dissolve_project_stack(self.project_id)
            self.dissolve_requested.emit(self.project_id)
        elif action == act_delete:
            database.delete_project(self.project_id, reassign_to_id="default")
            self.delete_requested.emit(self.project_id)

    def _show_color_flyout(self, global_pos: QPoint):
        flyout = ColorPickerFlyout(self)
        flyout.color_selected.connect(self._on_color_chosen)
        flyout.show_at(global_pos)

    def _on_color_chosen(self, hex_val: str):
        self.color_hex = hex_val
        database.update_project(self.project_id, color_hex=hex_val)
        self.layer_colors = self._get_layer_colors()
        self._apply_style()
        self.update()
        self.color_changed.emit(self.project_id, hex_val)
