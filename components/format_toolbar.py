from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, 
    QTextEdit, QMenu
)
from PySide6.QtGui import QCursor, QTextCursor

try:
    from ..icons import get_themed_icon
    from ..i18n import tr
except ImportError:
    from icons import get_themed_icon
    from i18n import tr


class FormatButton(QPushButton):
    """Compact toolbar button styled in Fluent minimal aesthetic with crisp vector icons."""
    def __init__(self, text: str = "", icon_name: str = None, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("FormatButton")
        self.icon_name = icon_name
        if tooltip:
            self.setToolTip(tooltip)
        if icon_name:
            self.setIcon(get_themed_icon(icon_name, role="btn_text", size=16))
            self.setIconSize(QSize(16, 16))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(28)

    def update_icon_theme(self, theme: str):
        if self.icon_name:
            self.setIcon(get_themed_icon(self.icon_name, role="btn_text", theme=theme, size=16))


class FormatToolbar(QFrame):
    """
    Rich text formatting and media attachment toolbar with vector SVG iconography.
    """
    add_picture_requested = Signal()
    add_audio_requested = Signal()
    add_video_requested = Signal()
    record_screen_requested = Signal()
    open_attachments_requested = Signal()

    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setObjectName("FormatToolbarFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        # Bold
        self.btn_bold = FormatButton(icon_name="bold", tooltip=f"{tr('tooltip_bold')}", parent=self)
        self.btn_bold.clicked.connect(self.apply_bold)
        layout.addWidget(self.btn_bold)

        # Italics
        self.btn_italic = FormatButton(icon_name="italic", tooltip=f"{tr('tooltip_italic')}", parent=self)
        self.btn_italic.clicked.connect(self.apply_italic)
        layout.addWidget(self.btn_italic)

        # Underline
        self.btn_underline = FormatButton(icon_name="underline", tooltip=f"{tr('tooltip_underline')}", parent=self)
        self.btn_underline.clicked.connect(self.apply_underline)
        layout.addWidget(self.btn_underline)

        # Strikethrough
        self.btn_strike = FormatButton(icon_name="strikethrough", tooltip=tr("tooltip_strike"), parent=self)
        self.btn_strike.clicked.connect(self.apply_strikethrough)
        layout.addWidget(self.btn_strike)

        layout.addWidget(self._create_separator())

        # Heading
        self.btn_heading = FormatButton(icon_name="heading", tooltip=f"{tr('tooltip_heading')}", parent=self)
        self.btn_heading.clicked.connect(self.apply_heading)
        layout.addWidget(self.btn_heading)

        # Bullet List
        self.btn_bullet = FormatButton(text=f" {tr('tooltip_list')}", icon_name="list", tooltip=f"{tr('tooltip_bullet_list')} (- )", parent=self)
        self.btn_bullet.clicked.connect(self.apply_bullet_list)
        layout.addWidget(self.btn_bullet)

        # Task Checklist
        self.btn_check = FormatButton(text=f" {tr('tooltip_task')}", icon_name="check_square", tooltip=f"{tr('tooltip_checklist')} (- [ ])", parent=self)
        self.btn_check.clicked.connect(self.apply_task_list)
        layout.addWidget(self.btn_check)

        # Code Block
        self.btn_code = FormatButton(icon_name="code", tooltip=f"{tr('tooltip_code')} (```)", parent=self)
        self.btn_code.clicked.connect(self.apply_code)
        layout.addWidget(self.btn_code)

        layout.addWidget(self._create_separator())

        # Media: Picture
        self.btn_picture = FormatButton(text=f" {tr('tooltip_photo')}", icon_name="image", tooltip=tr("tooltip_image"), parent=self)
        self.btn_picture.clicked.connect(self.add_picture_requested.emit)
        layout.addWidget(self.btn_picture)

        # Media: Audio / Voice
        self.btn_audio = FormatButton(text=f" {tr('tooltip_audio')}", icon_name="mic", tooltip=tr("tooltip_voice"), parent=self)
        self.btn_audio.clicked.connect(self.add_audio_requested.emit)
        layout.addWidget(self.btn_audio)

        # Media: Video
        self.btn_video = FormatButton(text=f" {tr('tooltip_video')}", icon_name="video", tooltip=tr("tooltip_video"), parent=self)
        self.btn_video.clicked.connect(self._show_video_menu)
        layout.addWidget(self.btn_video)

        layout.addStretch()

    def retranslate_ui(self):
        """Refreshes all button text and tooltips on language change."""
        self.btn_bold.setToolTip(f"{tr('tooltip_bold')}")
        self.btn_italic.setToolTip(f"{tr('tooltip_italic')}")
        self.btn_underline.setToolTip(f"{tr('tooltip_underline')}")
        self.btn_strike.setToolTip(tr("tooltip_strike"))
        self.btn_heading.setToolTip(f"{tr('tooltip_heading')}")
        self.btn_bullet.setText(f" {tr('tooltip_list')}")
        self.btn_bullet.setToolTip(f"{tr('tooltip_bullet_list')} (- )")
        self.btn_check.setText(f" {tr('tooltip_task')}")
        self.btn_check.setToolTip(f"{tr('tooltip_checklist')} (- [ ])")
        self.btn_code.setToolTip(f"{tr('tooltip_code')} (```)")
        self.btn_picture.setText(f" {tr('tooltip_photo')}")
        self.btn_picture.setToolTip(tr("tooltip_image"))
        self.btn_audio.setText(f" {tr('tooltip_audio')}")
        self.btn_audio.setToolTip(tr("tooltip_voice"))
        self.btn_video.setText(f" {tr('tooltip_video')}")
        self.btn_video.setToolTip(tr("tooltip_video"))

    def _show_video_menu(self):
        menu = QMenu(self)
        record_action = menu.addAction(f"🔴 {tr('record_screen')}")
        record_action.triggered.connect(self.record_screen_requested.emit)

        choose_action = menu.addAction(f"📁 {tr('choose_video')}")
        choose_action.triggered.connect(self.add_video_requested.emit)

        menu.addSeparator()
        folder_action = menu.addAction(f"📂 {tr('open_attachments')}")
        folder_action.triggered.connect(self.open_attachments_requested.emit)

        menu.exec(self.btn_video.mapToGlobal(self.btn_video.rect().bottomLeft()))

    def update_icons_for_theme(self, theme: str):
        """Updates all button vector icons when theme changes."""
        for btn in self.findChildren(FormatButton):
            btn.update_icon_theme(theme)

    def _create_separator(self) -> QFrame:
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(128, 128, 128, 0.25); margin: 3px 2px;")
        return sep

    # Formatting Actions
    def wrap_selection(self, prefix: str, suffix: str):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(f"{prefix}{selected_text}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def apply_bold(self):
        self.wrap_selection("**", "**")

    def apply_italic(self):
        self.wrap_selection("*", "*")

    def apply_underline(self):
        self.wrap_selection("<u>", "</u>")

    def apply_strikethrough(self):
        self.wrap_selection("~~", "~~")

    def apply_code(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and "\n" in cursor.selectedText():
            self.wrap_selection("```\n", "\n```")
        else:
            self.wrap_selection("`", "`")

    def apply_heading(self):
        self._prefix_current_line("## ")

    def apply_bullet_list(self):
        self._prefix_current_line("- ")

    def apply_task_list(self):
        self._prefix_current_line("- [ ] ")

    def _prefix_current_line(self, prefix: str):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(prefix)
        self.editor.setFocus()
