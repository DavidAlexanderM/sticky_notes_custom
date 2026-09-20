"""
project_dialog.py - Project Stack Creation and Management Dialogs.
Allows users to create, color-code, rename, and manage projects/stacks.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QListWidget, 
    QListWidgetItem, QMessageBox, QWidget
)
from PySide6.QtGui import QCursor

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
    from ..icons import get_themed_icon
    from .. import database
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES
    from icons import get_themed_icon
    import database


PROJECT_COLORS = [
    "#8AB4F8",  # Electric Blue (Antigravity)
    "#81C995",  # Emerald Green
    "#FDD663",  # Amber Gold
    "#FF8BCB",  # Vibrant Rose
    "#C58AF9",  # Purple
    "#78D9EC",  # Cyan
    "#FCAD70",  # Coral Orange
]


class NewProjectDialog(QDialog):
    """Modal dialog for creating a new project / collection stack."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project Stack")
        self.setFixedSize(380, 240)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])

        self.selected_color = PROJECT_COLORS[0]
        self.created_project_id: Optional[str] = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("New Project Stack", self)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        layout.addWidget(title_lbl)

        # Project Name Input
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Project name (e.g. Doctora, Research, Work)...")
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
        """)
        layout.addWidget(self.name_input)

        # Color Selector Chips
        color_lbl = QLabel("Stack Accent Color:", self)
        color_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.pal['text_secondary']};")
        layout.addWidget(color_lbl)

        color_row = QHBoxLayout()
        color_row.setSpacing(8)
        self.color_buttons = []
        for color in PROJECT_COLORS:
            btn = QPushButton(self)
            btn.setFixedSize(26, 26)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            border = "3px solid white" if color == self.selected_color else "1px solid rgba(0,0,0,0.2)"
            btn.setStyleSheet(f"background-color: {color}; border-radius: 13px; border: {border};")
            btn.clicked.connect(lambda checked=False, c=color: self._select_color(c))
            color_row.addWidget(btn)
            self.color_buttons.append((btn, color))
        color_row.addStretch()
        layout.addLayout(color_row)

        layout.addStretch()

        # Action Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.setObjectName("SelectModeButton")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        create_btn = QPushButton("Create Stack", self)
        create_btn.setObjectName("NewNoteButton")
        create_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        create_btn.setFixedHeight(32)
        create_btn.clicked.connect(self._create_project)
        btn_row.addWidget(create_btn)

        layout.addLayout(btn_row)

    def _select_color(self, color: str):
        self.selected_color = color
        for btn, c in self.color_buttons:
            border = "3px solid white" if c == self.selected_color else "1px solid rgba(0,0,0,0.2)"
            btn.setStyleSheet(f"background-color: {c}; border-radius: 13px; border: {border};")

    def _create_project(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a project name.")
            return
        self.created_project_id = database.create_project(name, color_hex=self.selected_color)
        self.accept()


class ManageProjectsDialog(QDialog):
    """Modal dialog for viewing, renaming, and deleting project stacks."""
    projects_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Project Stacks")
        self.resize(480, 400)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Project Stacks", self)
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("➕ New Project", self)
        add_btn.setObjectName("NewNoteButton")
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.clicked.connect(self._add_new_project)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Project list
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {self.pal['bg_surface']};
                border: 1px solid {self.pal['border']};
                border-radius: 8px;
                padding: 6px;
                color: {self.pal['text_primary']};
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {self.pal['accent']};
                color: {self.pal['accent_text']};
            }}
        """)
        layout.addWidget(self.list_widget, 1)

        # Action row
        action_row = QHBoxLayout()
        
        self.rename_btn = QPushButton("✏️ Rename", self)
        self.rename_btn.setObjectName("SelectModeButton")
        self.rename_btn.clicked.connect(self._rename_selected)
        action_row.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("🗑️ Delete Stack", self)
        self.delete_btn.setObjectName("SelectModeButton")
        self.delete_btn.setStyleSheet("color: #E57373;")
        self.delete_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self.delete_btn)

        action_row.addStretch()

        close_btn = QPushButton("Done", self)
        close_btn.setObjectName("SelectModeButton")
        close_btn.setFixedSize(80, 32)
        close_btn.clicked.connect(self.accept)
        action_row.addWidget(close_btn)

        layout.addLayout(action_row)

    def _refresh_list(self):
        self.list_widget.clear()
        projects = database.get_all_projects()
        for p in projects:
            is_def = p["id"] == "default"
            count = p.get("note_count", 0)
            tag = " (Default)" if is_def else ""
            item_text = f"📁  {p['name']}{tag}  —  {count} note{'s' if count != 1 else ''}"
            item = QListWidgetItem(item_text, self.list_widget)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.list_widget.addItem(item)

    def _add_new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_list()
            self.projects_changed.emit()

    def _rename_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        p = item.data(Qt.ItemDataRole.UserRole)
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Project", "New project stack name:", text=p["name"])
        if ok and new_name.strip():
            database.update_project(p["id"], name=new_name.strip())
            self._refresh_list()
            self.projects_changed.emit()

    def _delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        p = item.data(Qt.ItemDataRole.UserRole)
        if p["id"] == "default":
            QMessageBox.information(self, "Notice", "The default project stack cannot be deleted.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Project Stack",
            f"Are you sure you want to delete '{p['name']}'?\n\nIts notes will not be deleted; they will be safely reassigned to 'General Notes'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.delete_project(p["id"], reassign_to_id="default")
            self._refresh_list()
            self.projects_changed.emit()
