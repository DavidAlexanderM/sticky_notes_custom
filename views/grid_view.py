"""
grid_view.py - Main Sticky Notes Grid / Board View.
Features responsive multi-column note layout, color filter chips, live search,
Shift/Ctrl multi-selection, keyboard navigation, and Help & About center.
"""

from pathlib import Path
from typing import Optional, List, Set
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QGridLayout, 
    QFrame, QMessageBox, QFileDialog, QApplication, QMenu, QComboBox
)
from PySide6.QtGui import QCursor, QKeyEvent, QIcon, QPixmap, QPainter, QColor, QBrush, QPen
import markdown2

try:
    from ..components.note_card import NoteCard
    from ..components.stack_card import StackCard
    from ..components.help_dialog import HelpAboutDialog
    from ..components.share_dialog import ShareNoteDialog
    from ..components.project_dialog import NewProjectDialog, ManageProjectsDialog
    from ..styles import NOTE_COLORS, MARKDOWN_PREVIEW_CSS, THEME_PALETTES
    from ..theme_manager import get_theme_manager
    from ..icons import get_themed_icon, render_note_stack_icon
    from .. import database
except ImportError:
    from components.note_card import NoteCard
    from components.stack_card import StackCard
    from components.help_dialog import HelpAboutDialog
    from components.share_dialog import ShareNoteDialog
    from components.project_dialog import NewProjectDialog, ManageProjectsDialog
    from styles import NOTE_COLORS, MARKDOWN_PREVIEW_CSS, THEME_PALETTES
    from theme_manager import get_theme_manager
    from icons import get_themed_icon, render_note_stack_icon
    import database


def create_color_swatch_icon(color_hex: str, size: int = 14) -> QIcon:
    """Renders a crisp circular color swatch icon for filter pills."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(color_hex)))
    painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pix)


class ColorDotPillButton(QPushButton):
    """
    High-DPI resolution-independent circular color swatch filter button.
    Renders vector circles via QPainter with subpixel antialiasing to guarantee
    razor-sharp edges without the pixelation of CSS border-radius.
    """
    def __init__(self, color_hex: str, color_name: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.color_name = color_name
        self.is_active = False
        self.setObjectName("ColorDotPill")
        self.setFixedSize(24, 24)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"{color_name} notes")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_active(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        is_hovered = self.underMouse()

        theme_mgr = get_theme_manager()
        is_dark = theme_mgr.is_dark_mode()
        pal = THEME_PALETTES.get(theme_mgr.current_theme, THEME_PALETTES["light"])
        accent = QColor(pal.get("accent", "#2563EB"))

        if self.is_active:
            # Outer high-contrast accent ring + inner color fill
            outer_pen = QPen(accent, 2.0)
            painter.setPen(outer_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), 10.0, 10.0)

            # Inner color circle
            painter.setPen(QPen(QColor(0, 0, 0, 35 if not is_dark else 70), 0.8))
            painter.setBrush(QBrush(QColor(self.color_hex)))
            painter.drawEllipse(QPointF(cx, cy), 7.2, 7.2)

        elif is_hovered:
            # Hovered: Crisp accent border with full color fill
            hover_pen = QPen(accent, 2.0)
            painter.setPen(hover_pen)
            painter.setBrush(QBrush(QColor(self.color_hex)))
            painter.drawEllipse(QPointF(cx, cy), 9.2, 9.2)

        else:
            # Inactive: Crisp subtle perimeter border with full color fill
            subtle_border = QColor(255, 255, 255, 75) if is_dark else QColor(0, 0, 0, 50)
            painter.setPen(QPen(subtle_border, 1.2))
            painter.setBrush(QBrush(QColor(self.color_hex)))
            painter.drawEllipse(QPointF(cx, cy), 9.0, 9.0)

        painter.end()



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
        self.active_project_id = database.get_active_project_id()
        self.all_notes: List[dict] = []
        self.note_cards: List[NoteCard] = []
        self.stack_cards: List[StackCard] = []
        self.selected_note_ids: Set[str] = set()
        self.current_color_filter: Optional[str] = None
        self.anchor_card_index: int = -1
        self.focused_card_index: int = -1

        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(28, 20, 28, 16)
        self.main_layout.setSpacing(14)

        # Header Bar
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(10)

        # Header Sticky Note App Icon
        self.sticky_icon_label = QLabel(self)
        self.sticky_icon_label.setObjectName("HeaderStickyIcon")
        self.sticky_icon_label.setFixedSize(30, 30)
        self.sticky_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sticky_icon_label.setToolTip("Sticky Notes")
        ico_file = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        if ico_file.exists():
            self.sticky_icon_label.setPixmap(QIcon(str(ico_file)).pixmap(26, 26))
        else:
            self.sticky_icon_label.setPixmap(render_note_stack_icon("#F9AB00", size=26).pixmap(26, 26))
        self.header_layout.addWidget(self.sticky_icon_label)

        self.title_label = QLabel("", self)
        self.title_label.setObjectName("AppHeaderTitle")
        self.title_label.setVisible(False)
        self.header_layout.addWidget(self.title_label)

        # Back to Board Button (visible when inside a stack)
        self.back_to_board_btn = QPushButton("← Back to Board", self)
        self.back_to_board_btn.setObjectName("BackToBoardBtn")
        self.back_to_board_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.back_to_board_btn.setToolTip("Return to main board showing all stacks and free notes")
        self.back_to_board_btn.clicked.connect(lambda: self._switch_active_project("default"))
        self.back_to_board_btn.setVisible(False)
        self.header_layout.addWidget(self.back_to_board_btn)

        # Project Stack Switcher Button
        self.project_btn = QPushButton(self)
        self.project_btn.setObjectName("ProjectSwitcherBtn")
        self.project_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.project_btn.clicked.connect(self._show_project_menu)
        self.header_layout.addWidget(self.project_btn)

        self.header_layout.addStretch()

        # Help & Keyboard Shortcuts Button (❓)
        self.help_btn = QPushButton(self)
        self.help_btn.setObjectName("EditorHeaderBtn")
        self.help_btn.setFixedSize(36, 36)
        self.help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.help_btn.setToolTip("Help & Keyboard Shortcuts (F1)")
        self.help_btn.clicked.connect(self._open_help_dialog)
        self.header_layout.addWidget(self.help_btn)

        # Theme Switcher Button (Icon-Only, System/Dark/Light)
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("ThemeToggleBtn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_btn.customContextMenuRequested.connect(self._show_theme_context_menu)
        self.header_layout.addWidget(self.theme_btn)

        # "+ New Note" Button
        self.new_note_btn = QPushButton(" New Note", self)
        self.new_note_btn.setObjectName("NewNoteButton")
        self.new_note_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.new_note_btn.clicked.connect(self._create_new_note)
        self.header_layout.addWidget(self.new_note_btn)

        self.main_layout.addLayout(self.header_layout)

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

        # Color Filter Chips & Sort Selector Bar
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)
        chips_layout.setContentsMargins(0, 0, 0, 0)

        self.pill_buttons = {}
        all_pill = QPushButton("All", self)
        all_pill.setObjectName("FilterPill")
        all_pill.setProperty("active", True)
        all_pill.setToolTip("Show notes of all colors")
        all_pill.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        all_pill.clicked.connect(lambda: self._set_color_filter(None))
        chips_layout.addWidget(all_pill)
        self.pill_buttons[None] = all_pill

        for c in NOTE_COLORS:
            hex_val = c["hex"]
            pill = ColorDotPillButton(hex_val, c["name"], self)
            pill.clicked.connect(lambda _, h=hex_val: self._set_color_filter(h))
            chips_layout.addWidget(pill)
            self.pill_buttons[hex_val] = pill

        self._update_pill_styles()

        chips_layout.addStretch()

        # Sort Dropdown
        sort_lbl = QLabel("Sort:", self)
        sort_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        chips_layout.addWidget(sort_lbl)

        self.sort_combo = QComboBox(self)
        self.sort_combo.setObjectName("SortComboBox")
        self.sort_combo.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.sort_combo.addItem("📅 Created (Newest)", "created_desc")
        self.sort_combo.addItem("📅 Created (Oldest)", "created_asc")
        self.sort_combo.addItem("⏱️ Recently Edited", "updated_desc")
        self.sort_combo.addItem("⏱️ Oldest Edited", "updated_asc")
        self.sort_combo.addItem("🔤 Title (A-Z)", "title_asc")

        # Set initial sort selection based on persisted preference
        saved_sort = database.get_sort_preference()
        for idx in range(self.sort_combo.count()):
            if self.sort_combo.itemData(idx) == saved_sort:
                self.sort_combo.setCurrentIndex(idx)
                break

        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        chips_layout.addWidget(self.sort_combo)

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

        self.move_selected_btn = QPushButton(" Move to Stack", self.action_bar)
        self.move_selected_btn.setObjectName("SelectModeButton")
        self.move_selected_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.move_selected_btn.clicked.connect(self._show_batch_move_menu)
        action_layout.addWidget(self.move_selected_btn)

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

    def show_update_available_banner(self, release_info: dict):
        """Displays a non-intrusive update pill button in the top header."""
        self._latest_release_info = release_info
        ver = release_info.get("version", "")
        self.help_btn.setToolTip(f"Help & About (F1) • Update v{ver} Available!")

        if not hasattr(self, 'update_alert_btn') or self.update_alert_btn is None:
            self.update_alert_btn = QPushButton(f"✨ v{ver} Available", self)
            self.update_alert_btn.setObjectName("NewNoteButton")
            self.update_alert_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.update_alert_btn.setToolTip(f"A new version of Sticky Notes (v{ver}) is available. Click to view & install.")
            self.update_alert_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8AB4F8;
                    color: #041E49;
                    font-size: 11px;
                    font-weight: 700;
                    border-radius: 6px;
                    padding: 5px 10px;
                }
                QPushButton:hover { background-color: #A8C7FA; }
            """)
            self.update_alert_btn.clicked.connect(self._open_update_from_banner)
            idx = self.header_layout.indexOf(self.help_btn)
            self.header_layout.insertWidget(max(0, idx), self.update_alert_btn)

    def _open_update_from_banner(self):
        try:
            from components.update_dialog import UpdateDialog
        except ImportError:
            from ..components.update_dialog import UpdateDialog
        dialog = UpdateDialog(self, auto_check=False)
        if hasattr(self, '_latest_release_info') and self._latest_release_info:
            dialog._show_update_available(self._latest_release_info)
        else:
            dialog._start_check()
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
        if hasattr(self, 'move_selected_btn'):
            self.move_selected_btn.setIcon(get_themed_icon("folder", role="btn_text", theme=theme, size=15))

        self._update_project_button_label()

    def _update_project_button_label(self):
        """Updates the Project Switcher button label, back button, and header title based on active stack."""
        theme = self.theme_mgr.current_theme
        projects = database.get_all_projects()
        all_count = sum(p.get("note_count", 0) for p in projects)
        
        is_in_stack = self.active_project_id not in ("all", "default")
        self.back_to_board_btn.setVisible(is_in_stack)

        if self.active_project_id == "all":
            self.title_label.setText("")
            self.title_label.setVisible(False)
            self.project_btn.setText(f" All Notes ({all_count}) ▾")
            self.project_btn.setIcon(get_themed_icon("layers", role="btn_text", theme=theme, size=16))
            self.project_btn.setToolTip("Active Collection: All Notes\nClick to switch project stack")
            return

        active_proj = next((p for p in projects if p["id"] == self.active_project_id), None)
        if not active_proj:
            # Project was deleted or invalid; fallback to default
            self.active_project_id = "default"
            database.set_active_project_id("default")
            active_proj = next((p for p in projects if p["id"] == "default"), None)
            self.back_to_board_btn.setVisible(False)

        if self.active_project_id == "default":
            self.title_label.setText("")
            self.title_label.setVisible(False)
            count = active_proj.get("note_count", 0) if active_proj else 0
            self.project_btn.setText(f" Free Notes ({count}) ▾")
            p_color = active_proj.get("color", "#F9AB00") if active_proj else "#F9AB00"
            self.project_btn.setIcon(render_note_stack_icon(p_color, size=18))
            self.project_btn.setToolTip("Active Collection: Free Notes\nClick to switch project stack")
        else:
            name = active_proj["name"] if active_proj else "Stack"
            count = active_proj.get("note_count", 0) if active_proj else 0
            p_color = active_proj.get("color", "#F9AB00") if active_proj else "#F9AB00"
            self.title_label.setText(f"📚 {name}")
            self.title_label.setVisible(True)
            self.project_btn.setText(f" {name} ({count}) ▾")
            self.project_btn.setIcon(render_note_stack_icon(p_color, size=18))
            self.project_btn.setToolTip(f"Active Stack: {name}\nClick to switch project stack")

    def _show_project_menu(self):
        """Displays dropdown menu listing all project stacks with note counts and management options."""
        menu = QMenu(self)
        theme = self.theme_mgr.current_theme
        is_dark = self.theme_mgr.is_dark_mode()
        try:
            from ..styles import THEME_PALETTES
        except ImportError:
            from styles import THEME_PALETTES
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

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

        projects = database.get_all_projects()
        all_count = sum(p.get("note_count", 0) for p in projects)

        # "All Notes" option
        act_all = menu.addAction(get_themed_icon("layers", role="btn_text", theme=theme, size=16), f"All Notes ({all_count})")
        act_all.setCheckable(True)
        act_all.setChecked(self.active_project_id == "all")

        menu.addSeparator()

        # Project items
        project_actions = {}
        for p in projects:
            p_id = p["id"]
            p_name = p["name"]
            p_count = p.get("note_count", 0)
            p_color = p.get("color", "#F9AB00")
            act = menu.addAction(render_note_stack_icon(p_color, size=16), f"{p_name} ({p_count})")
            act.setCheckable(True)
            act.setChecked(self.active_project_id == p_id)
            project_actions[act] = p_id

        menu.addSeparator()

        # New Project Stack
        act_new = menu.addAction(get_themed_icon("plus", role="btn_text", theme=theme, size=15), "New Project Stack...")
        # Manage Project Stacks
        act_manage = menu.addAction("⚙️ Manage Stacks...")

        pos = self.project_btn.mapToGlobal(self.project_btn.rect().bottomLeft())
        action = menu.exec(pos)

        if action == act_all:
            self._switch_active_project("all")
        elif action in project_actions:
            self._switch_active_project(project_actions[action])
        elif action == act_new:
            self._open_new_project_dialog()
        elif action == act_manage:
            self._open_manage_projects_dialog()

    def _switch_active_project(self, project_id: str):
        self.active_project_id = project_id
        database.set_active_project_id(project_id)
        self._update_project_button_label()
        self.load_notes()

    def _open_new_project_dialog(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() and dlg.created_project_id:
            self._switch_active_project(dlg.created_project_id)

    def _open_manage_projects_dialog(self):
        dlg = ManageProjectsDialog(self)
        dlg.projects_changed.connect(self._on_projects_changed)
        dlg.exec()
        self._on_projects_changed()

    def _on_projects_changed(self):
        projects = database.get_all_projects()
        p_ids = {p["id"] for p in projects}
        if self.active_project_id != "all" and self.active_project_id not in p_ids:
            self.active_project_id = "default"
            database.set_active_project_id("default")
        self._update_project_button_label()
        self.load_notes()

    def _show_batch_move_menu(self):
        if not self.selected_note_ids:
            return
        menu = QMenu(self)
        theme = self.theme_mgr.current_theme
        projects = database.get_all_projects()
        project_actions = {}
        for p in projects:
            p_id = p["id"]
            p_name = p["name"]
            p_color = p.get("color", "#F9AB00")
            act = menu.addAction(render_note_stack_icon(p_color, size=16), f"Move to {p_name}")
            project_actions[act] = p_id

        pos = self.move_selected_btn.mapToGlobal(self.move_selected_btn.rect().topLeft())
        action = menu.exec(pos)
        if action in project_actions:
            target_pid = project_actions[action]
            database.move_notes_to_project(list(self.selected_note_ids), target_pid)
            self.selected_note_ids.clear()
            self.load_notes()

    def _on_card_move_to_project(self, note_id: str, project_id: str):
        database.move_notes_to_project([note_id], project_id)
        self.load_notes()

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
        self._update_pill_styles()
        for card in self.note_cards:
            card._apply_style()
        for sc in self.stack_cards:
            sc._apply_style()

    def _update_pill_styles(self):
        """Updates circular color swatches and active ring based on current theme."""
        theme = self.theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])
        accent = pal.get("accent", "#2563EB")
        is_dark = self.theme_mgr.is_dark_mode()
        default_border = "rgba(255, 255, 255, 0.30)" if is_dark else "rgba(0, 0, 0, 0.18)"

        for hex_val, btn in self.pill_buttons.items():
            if hex_val is None:
                is_active = (self.current_color_filter is None)
                btn.setProperty("active", is_active)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            else:
                is_active = (self.current_color_filter == hex_val)
                if hasattr(btn, 'set_active'):
                    btn.set_active(is_active)
                else:
                    btn.setProperty("active", is_active)
                    btn.update()

    def _set_color_filter(self, hex_val):
        self.current_color_filter = hex_val
        self._update_pill_styles()
        self._filter_and_render_notes()

    def _on_sort_changed(self, index: int):
        """Triggered when the user changes the sort dropdown."""
        sort_mode = self.sort_combo.itemData(index)
        if sort_mode:
            database.set_sort_preference(sort_mode)
            self.load_notes()

    def _clear_filters(self):
        """Clears search input and resets active color filter."""
        self.search_input.clear()
        self._set_color_filter(None)

    def _on_search_changed(self, text: str):
        self._filter_and_render_notes()

    def load_notes(self):
        """Reloads notes from database and refreshes view."""
        if self.active_project_id in ("all", "default"):
            self.all_notes = database.get_all_notes("all")
        else:
            self.all_notes = database.get_all_notes(self.active_project_id)
        self._update_project_button_label()
        self._filter_and_render_notes()

    def _filter_and_render_notes(self):
        """Filters notes and stacks based on search query and color, then renders grid."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.note_cards.clear()
        self.stack_cards.clear()
        self.selected_note_ids.clear()
        self.anchor_card_index = -1
        self.focused_card_index = -1
        self._update_selection_ui()

        search_query = self.search_input.text().strip().lower()

        filtered_projects = []
        if self.active_project_id in ("all", "default"):
            projects = database.get_all_projects()
            custom_projects = [p for p in projects if p["id"] != "default"]
            for p in custom_projects:
                if self.current_color_filter:
                    p_colors = database.get_project_note_colors(p["id"])
                    if p.get("color") != self.current_color_filter and self.current_color_filter not in p_colors:
                        continue
                if search_query:
                    p_name_match = search_query in p["name"].lower()
                    preview_notes = database.get_project_notes_preview(p["id"], limit=10)
                    note_match = any(search_query in (n.get("title") or "").lower() for n in preview_notes)
                    if not (p_name_match or note_match):
                        continue
                filtered_projects.append(p)

        filtered_notes = []
        notes_source = self.all_notes
        if self.active_project_id in ("all", "default"):
            notes_source = [n for n in self.all_notes if n.get("project_id", "default") == "default"]

        for note in notes_source:
            if self.current_color_filter and note.get("color_hex") != self.current_color_filter:
                continue
            if search_query:
                title_match = search_query in note.get("title", "").lower()
                content_match = search_query in note.get("content", "").lower()
                if not (title_match or content_match):
                    continue
            filtered_notes.append(note)

        # Empty state handling
        if not filtered_projects and not filtered_notes:
            empty_frame = QFrame(self.grid_content)
            empty_frame.setObjectName("EmptyStateCard")
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.setSpacing(10)

            if search_query or self.current_color_filter:
                icon_lbl = QLabel("🔍", empty_frame)
                icon_lbl.setStyleSheet("font-size: 32px;")
                title_lbl = QLabel("No notes or stacks matched your search.", empty_frame)
                title_lbl.setObjectName("EmptyStateTitle")
                btn_clear = QPushButton("Clear Filter", empty_frame)
                btn_clear.setObjectName("SelectModeButton")
                btn_clear.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn_clear.clicked.connect(self._clear_filters)
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(btn_clear, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                if self.active_project_id not in ("all", "default"):
                    icon_lbl = QLabel("📚", empty_frame)
                    icon_lbl.setStyleSheet("font-size: 36px;")
                    title_lbl = QLabel("This stack is currently empty.", empty_frame)
                    title_lbl.setObjectName("EmptyStateTitle")
                    sub_lbl = QLabel("Click '+ New Note' or drag notes into this stack from the main board!", empty_frame)
                    sub_lbl.setObjectName("EmptyStateSubtitle")
                else:
                    icon_lbl = QLabel("📝", empty_frame)
                    icon_lbl.setStyleSheet("font-size: 36px;")
                    title_lbl = QLabel("No notes yet.", empty_frame)
                    title_lbl.setObjectName("EmptyStateTitle")
                    sub_lbl = QLabel("Click '+ New Note' to create a note, or drag notes over each other to form a stack!", empty_frame)
                    sub_lbl.setObjectName("EmptyStateSubtitle")
                empty_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                empty_layout.addWidget(sub_lbl, 0, Qt.AlignmentFlag.AlignCenter)

            self.grid_layout.addWidget(empty_frame, 0, 0, 1, 3)
            return

        cols = max(1, self.width() // 250) if self.width() > 0 else 3
        current_idx = 0

        # Render Stacks (when at root board)
        for project in filtered_projects:
            row = current_idx // cols
            col = current_idx % cols
            sc = StackCard(project, self.grid_content)
            sc.open_stack_requested.connect(self._switch_active_project)
            sc.note_dropped_into_stack.connect(self._on_note_dropped_into_stack)
            sc.dissolve_requested.connect(self._on_stack_dissolved)
            sc.delete_requested.connect(self._on_stack_deleted)
            sc.color_changed.connect(lambda pid, c: self.load_notes())
            sc.renamed.connect(lambda pid, n: self._update_project_button_label())
            self.grid_layout.addWidget(sc, row, col)
            self.stack_cards.append(sc)
            current_idx += 1

        # Render Notes
        for note in filtered_notes:
            row = current_idx // cols
            col = current_idx % cols
            
            card = NoteCard(note, self.grid_content)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.clicked.connect(self._on_card_clicked)
            card.color_changed.connect(self._on_card_color_changed)
            card.duplicate_requested.connect(self._on_card_duplicate_requested)
            card.share_requested.connect(self._on_card_share_requested)
            card.delete_requested.connect(self._on_card_delete_requested)
            card.selection_toggled.connect(self._on_card_selection_toggled)
            card.move_to_project_requested.connect(self._on_card_move_to_project)
            card.create_stack_requested.connect(self._on_create_stack_from_notes)
            
            self.grid_layout.addWidget(card, row, col)
            self.note_cards.append(card)
            current_idx += 1

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
        pid = self.active_project_id if self.active_project_id not in ("all", "default") else "default"
        note_id = database.create_note(title="Untitled Note", content="", color_hex=initial_color, project_id=pid)
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

    def _on_create_stack_from_notes(self, source_note_id: str, target_note_id: str):
        """Merges two notes into a new project stack when dragged onto each other."""
        stack_name = database.get_next_stack_name()
        target_note = database.get_note(target_note_id)
        color = target_note.get("color_hex", "#FFF9C4") if target_note else "#FFF9C4"
        new_pid = database.create_project(name=stack_name, color_hex=color)
        database.move_notes_to_project([source_note_id, target_note_id], new_pid)
        self.load_notes()

    def _on_note_dropped_into_stack(self, note_id: str, project_id: str):
        """Called when a note is dropped onto an existing stack card."""
        database.move_notes_to_project([note_id], project_id)
        self.load_notes()

    def _on_stack_dissolved(self, project_id: str):
        """Called when a stack card is dissolved via its menu."""
        self.load_notes()

    def _on_stack_deleted(self, project_id: str):
        """Called when a stack is deleted."""
        self.load_notes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'all_notes') and self.all_notes:
            self._filter_and_render_notes()
