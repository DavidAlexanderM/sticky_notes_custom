"""
tag_side_panel.py - Collapsible Tag Side Panel for Sticky Notes Board.
Displays custom tags first at the top, predetermined system tags below,
note count badges, 1-click filtering, and tag management.
"""

from typing import Optional, Dict
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QInputDialog,
    QMessageBox, QMenu
)
from PySide6.QtGui import QCursor, QPainter, QColor, QBrush, QPen

try:
    from .. import database
    from ..i18n import tr, get_translation_manager
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
    from ..icons import get_themed_icon
except ImportError:
    import database
    from i18n import tr, get_translation_manager
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES
    from icons import get_themed_icon


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


class TagSidePanelItem(QPushButton):
    """Interactive button representing a single tag in the sidebar with badge count."""
    def __init__(self, tag_key: str, display_name: str, color_hex: Optional[str] = None, count: int = 0, is_custom: bool = False, parent=None):
        super().__init__(parent)
        self.tag_key = tag_key
        self.display_name = display_name
        self.color_hex = color_hex
        self.count = count
        self.is_custom = is_custom
        self.is_active = False

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(32)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        if self.color_hex:
            self.dot = TagColorDot(self.color_hex, size=11, parent=self)
            layout.addWidget(self.dot)
        else:
            icon_lbl = QLabel("🏷️", self)
            icon_lbl.setStyleSheet("font-size: 11px;")
            layout.addWidget(icon_lbl)

        self.name_lbl = QLabel(self.display_name, self)
        layout.addWidget(self.name_lbl, 1)

        self.count_lbl = QLabel(str(self.count), self)
        layout.addWidget(self.count_lbl)

    def set_active(self, active: bool, theme_pal: dict):
        self.is_active = active
        accent = theme_pal.get("accent", "#2563EB")
        accent_text = theme_pal.get("accent_text", "#FFFFFF")
        text_pri = theme_pal.get("text_primary", "#0F172A")
        text_sec = theme_pal.get("text_secondary", "#475569")
        hover_bg = theme_pal.get("btn_hover", "#F1F5F9")

        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                }}
            """)
            self.name_lbl.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {accent_text}; background: transparent;")
            self.count_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {accent_text}; background: transparent;")
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                }}
            """)
            self.name_lbl.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {text_pri}; background: transparent;")
            self.count_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {text_sec}; background: transparent;")


class TagSidePanel(QWidget):
    """
    Collapsible side panel organizing tags with Custom Tags ordered first at top,
    system predetermined tags below, note counts, and reactive filtering.
    """
    tag_selected = Signal(str)  # Emits selected tag name, or "" for all, or "__untagged__"
    tags_modified = Signal()    # Emitted when custom tags are created, renamed, or deleted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TagSidePanel")
        self.theme_mgr = get_theme_manager()
        self.i18n = get_translation_manager()
        self.active_tag: Optional[str] = None  # None = All Notes
        self.is_collapsed = False
        self.panel_width = 190

        self.setFixedWidth(self.panel_width)
        self._build_ui()

        # Listen for theme and language changes
        self.theme_mgr.theme_changed.connect(self._on_theme_changed)
        self.i18n.language_changed.connect(self._on_language_changed)

    def _on_theme_changed(self, _=None):
        try:
            self._refresh_styles()
        except RuntimeError:
            pass

    def _on_language_changed(self, _=None):
        try:
            self.refresh_tags()
        except RuntimeError:
            pass

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 12, 8, 12)
        self.main_layout.setSpacing(6)

        # Panel Header
        header_row = QHBoxLayout()
        header_row.setContentsMargins(6, 0, 6, 4)
        
        self.title_lbl = QLabel(f"<b>{tr('tags_header')}</b>", self)
        self.title_lbl.setStyleSheet("font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;")
        header_row.addWidget(self.title_lbl)
        header_row.addStretch()

        self.add_btn = QPushButton("+", self)
        self.add_btn.setFixedSize(22, 22)
        self.add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_btn.setToolTip(tr("add_custom_tag"))
        self.add_btn.clicked.connect(self._prompt_create_custom_tag)
        header_row.addWidget(self.add_btn)

        self.main_layout.addLayout(header_row)

        # Scroll Area for Tag Items
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.items_layout = QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(3)

        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll, 1)

        self.tag_buttons: Dict[str, TagSidePanelItem] = {}
        self.refresh_tags()
        self._refresh_styles()

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(0)
            self.setVisible(False)
        else:
            self.setVisible(True)
            self.setFixedWidth(self.panel_width)

    def _get_palette(self) -> dict:
        is_dark = self.theme_mgr.is_dark_mode()
        fallback_pal = THEME_PALETTES["dark" if is_dark else "light"]
        theme = self.theme_mgr.current_theme
        return THEME_PALETTES.get(theme, fallback_pal) or fallback_pal

    def refresh_tags(self):
        """Rebuilds the list of tags: Custom Tags FIRST, then Predetermined Tags."""
        # Clear existing items
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.tag_buttons.clear()

        pal = self._get_palette()
        tag_counts = database.get_all_tag_counts()
        all_notes = database.get_all_notes(project_id="all")
        total_notes_count = len(all_notes)
        untagged_count = sum(1 for n in all_notes if not database.get_note_tags(n["id"]))

        # 1. Top Global Filters: All Notes & Untagged
        all_item = TagSidePanelItem(
            tag_key="", display_name=tr("all_tags_filter"),
            color_hex=None, count=total_notes_count, is_custom=False, parent=self.scroll_content
        )
        all_item.clicked.connect(lambda: self._select_tag(None))
        self.items_layout.addWidget(all_item)
        self.tag_buttons["__all__"] = all_item

        untagged_item = TagSidePanelItem(
            tag_key="__untagged__", display_name=tr("untagged_filter"),
            color_hex="#94A3B8", count=untagged_count, is_custom=False, parent=self.scroll_content
        )
        untagged_item.clicked.connect(lambda: self._select_tag("__untagged__"))
        self.items_layout.addWidget(untagged_item)
        self.tag_buttons["__untagged__"] = untagged_item

        sep1 = QFrame(self.scroll_content)
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"background-color: {pal.get('border_subtle', '#334155')}; max-height: 1px; margin: 4px 0;")
        self.items_layout.addWidget(sep1)

        # 2. Custom Tags Section (FIRST IN SELECTION ORDER)
        custom_hdr = QLabel(f"<b>{tr('custom_tags_section')}</b>", self.scroll_content)
        custom_hdr.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {pal.get('text_muted', '#8E918F')}; text-transform: uppercase; padding: 4px 8px; background: transparent;")
        self.items_layout.addWidget(custom_hdr)

        custom_tags = database.get_custom_tags()
        for ct in custom_tags:
            tag_name = ct["name"]
            cnt = tag_counts.get(tag_name, 0)
            item = TagSidePanelItem(
                tag_key=tag_name, display_name=tag_name,
                color_hex=ct["color_hex"], count=cnt, is_custom=True, parent=self.scroll_content
            )
            item.clicked.connect(lambda _, t=tag_name: self._select_tag(t))
            item.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            item.customContextMenuRequested.connect(lambda pos, t=tag_name: self._show_tag_context_menu(pos, t))
            self.items_layout.addWidget(item)
            self.tag_buttons[tag_name] = item

        sep2 = QFrame(self.scroll_content)
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background-color: {pal.get('border_subtle', '#334155')}; max-height: 1px; margin: 4px 0;")
        self.items_layout.addWidget(sep2)

        # 3. Predetermined System Tags Section (SECOND)
        pred_hdr = QLabel(f"<b>{tr('predetermined_tags_section')}</b>", self.scroll_content)
        pred_hdr.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {pal.get('text_muted', '#8E918F')}; text-transform: uppercase; padding: 4px 8px; background: transparent;")
        self.items_layout.addWidget(pred_hdr)

        for pt in database.PREDETERMINED_TAGS:
            name = tr(pt["key"])
            canonical = pt["default_name"]
            cnt = tag_counts.get(name, 0)
            if name != canonical:
                cnt += tag_counts.get(canonical, 0)
            item = TagSidePanelItem(
                tag_key=canonical, display_name=name,
                color_hex=pt["color_hex"], count=cnt, is_custom=False, parent=self.scroll_content
            )
            item.clicked.connect(lambda _, t=canonical: self._select_tag(t))
            self.items_layout.addWidget(item)
            self.tag_buttons[canonical] = item

        self.items_layout.addStretch()
        self._refresh_selection_visuals()

    def _select_tag(self, tag_key: Optional[str]):
        self.active_tag = tag_key
        self._refresh_selection_visuals()
        self.tag_selected.emit(tag_key or "")

    def _refresh_selection_visuals(self):
        pal = self._get_palette()

        for key, btn in self.tag_buttons.items():
            if self.active_tag is None:
                is_act = (key == "__all__")
            elif self.active_tag == "__untagged__":
                is_act = (key == "__untagged__")
            else:
                is_act = (btn.tag_key == self.active_tag or key == self.active_tag)
            btn.set_active(is_act, pal)

    def _refresh_styles(self):
        pal = self._get_palette()

        self.setStyleSheet(f"""
            QWidget#TagSidePanel {{
                background-color: {pal.get('bg_surface', '#FFFFFF')};
                border-right: 1px solid {pal.get('border', '#E2E8F0')};
            }}
            QLabel {{
                color: {pal.get('text_primary', '#0F172A')};
            }}
            QPushButton {{
                color: {pal.get('text_primary', '#0F172A')};
            }}
        """)
        self.title_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: 700; color: {pal.get('text_secondary', '#C4C7C5')}; text-transform: uppercase; letter-spacing: 0.8px; background: transparent;")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {pal['accent']};
                color: {pal['accent_text']};
                border: none;
                border-radius: 11px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        self._refresh_selection_visuals()

    def _prompt_create_custom_tag(self):
        tag_name, ok = QInputDialog.getText(
            self, tr("create_tag_title"), tr("create_tag_prompt")
        )
        if ok and tag_name.strip():
            clean = tag_name.strip()
            custom_colors = ["#F43F5E", "#EC4899", "#8B5CF6", "#6366F1", "#0EA5E9", "#10B981", "#F59E0B"]
            existing = len(database.get_custom_tags())
            chosen_color = custom_colors[existing % len(custom_colors)]

            created = database.create_custom_tag(clean, chosen_color)
            if created:
                self.refresh_tags()
                self.tags_modified.emit()
                self._select_tag(clean)
            else:
                QMessageBox.warning(self, tr("create_tag_title"), tr("tag_already_exists"))

    def _show_tag_context_menu(self, pos, tag_name: str):
        menu = QMenu(self)
        pal = self._get_palette()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {pal.get('menu_bg', '#FFFFFF')};
                border: 1px solid {pal.get('border', '#E2E8F0')};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                color: {pal.get('text_primary', '#0F172A')};
                font-size: 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {pal.get('btn_hover', '#F1F5F9')};
                color: {pal.get('accent', '#2563EB')};
            }}
        """)

        act_rename = menu.addAction(tr("rename"))
        act_delete = menu.addAction(tr("delete"))

        btn = self.tag_buttons.get(tag_name)
        global_pos = btn.mapToGlobal(pos) if btn else self.mapToGlobal(pos)
        action = menu.exec(global_pos)

        if action == act_rename:
            new_name, ok = QInputDialog.getText(self, tr("rename"), tr("create_tag_prompt"), text=tag_name)
            if ok and new_name.strip() and new_name.strip() != tag_name:
                if database.rename_custom_tag(tag_name, new_name.strip()):
                    self.refresh_tags()
                    self.tags_modified.emit()
                    if self.active_tag == tag_name:
                        self._select_tag(new_name.strip())
        elif action == act_delete:
            confirm = QMessageBox.question(
                self, tr("delete_tag"),
                tr("confirm_delete_tag", name=tag_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                database.delete_custom_tag(tag_name)
                self.refresh_tags()
                self.tags_modified.emit()
                if self.active_tag == tag_name:
                    self._select_tag(None)
