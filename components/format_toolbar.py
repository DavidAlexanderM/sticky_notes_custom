from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, 
    QTextEdit, QMenu
)
from PySide6.QtGui import QCursor, QTextCursor

try:
    from ..icons import get_themed_icon
    from ..i18n import tr
    from ..proofing_engine import get_proofing_engine
except ImportError:
    from icons import get_themed_icon
    from i18n import tr
    from proofing_engine import get_proofing_engine


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
    screen_capture_requested = Signal()
    attach_audio_requested = Signal()

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

        # 1-Touch Direct Action: Audio Recording
        self.btn_audio = FormatButton(text=f" {tr('btn_audio')}", icon_name="mic", tooltip=tr("tooltip_record_audio"), parent=self)
        self.btn_audio.clicked.connect(self.add_audio_requested.emit)
        layout.addWidget(self.btn_audio)

        # 1-Touch Direct Action: Screen Capture
        self.btn_capture = FormatButton(text=f" {tr('btn_screen_capture')}", icon_name="camera", tooltip=tr("tooltip_screen_capture"), parent=self)
        self.btn_capture.clicked.connect(self.screen_capture_requested.emit)
        layout.addWidget(self.btn_capture)

        # 1-Touch Direct Action: Video Recording
        self.btn_video = FormatButton(text=f" {tr('btn_video')}", icon_name="video", tooltip=tr("tooltip_record_video"), parent=self)
        self.btn_video.clicked.connect(self.record_screen_requested.emit)
        layout.addWidget(self.btn_video)

        # Unified File Attachments Menu (Clip)
        self.btn_attach = FormatButton(text=f" {tr('btn_attach')} ▾", icon_name="clip", tooltip=tr("tooltip_attach_media"), parent=self)
        self.btn_attach.clicked.connect(self._show_attach_menu)
        layout.addWidget(self.btn_attach)
        self.btn_picture = self.btn_attach

        layout.addStretch()

        # Spell Check Toggle Button
        self.proofing_engine = get_proofing_engine()
        self.btn_spell = FormatButton(
            text=" ABC✓" if self.proofing_engine.is_enabled else " ABC",
            tooltip=tr("tooltip_spellcheck"),
            parent=self
        )
        self.btn_spell.setCheckable(True)
        self.btn_spell.setChecked(self.proofing_engine.is_enabled)
        self.btn_spell.toggled.connect(self._on_spell_toggled)
        layout.addWidget(self.btn_spell)

    def _on_spell_toggled(self, checked: bool):
        self.proofing_engine.set_enabled(checked)
        self.btn_spell.setText(" ABC✓" if checked else " ABC")

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
        self.btn_audio.setText(f" {tr('btn_audio')}")
        self.btn_audio.setToolTip(tr("tooltip_record_audio"))
        self.btn_capture.setText(f" {tr('btn_screen_capture')}")
        self.btn_capture.setToolTip(tr("tooltip_screen_capture"))
        self.btn_video.setText(f" {tr('btn_video')}")
        self.btn_video.setToolTip(tr("tooltip_record_video"))
        self.btn_attach.setText(f" {tr('btn_attach')} ▾")
        self.btn_attach.setToolTip(tr("tooltip_attach_media"))
        if hasattr(self, 'btn_spell'):
            self.btn_spell.setToolTip(tr("tooltip_spellcheck"))
            self.btn_spell.setText(" ABC✓" if self.proofing_engine.is_enabled else " ABC")

    def _show_attach_menu(self):
        menu = QMenu(self)
        picture_action = menu.addAction(f"🖼️ {tr('attach_picture')}")
        picture_action.triggered.connect(self.add_picture_requested.emit)

        audio_action = menu.addAction(f"🎵 {tr('attach_audio')}")
        audio_action.triggered.connect(self.attach_audio_requested.emit)

        video_action = menu.addAction(f"🎥 {tr('attach_video')}")
        video_action.triggered.connect(self.add_video_requested.emit)

        menu.addSeparator()
        folder_action = menu.addAction(f"📂 {tr('open_attachments')}")
        folder_action.triggered.connect(self.open_attachments_requested.emit)

        menu.exec(self.btn_attach.mapToGlobal(self.btn_attach.rect().bottomLeft()))

    def _show_video_menu(self):
        self._show_attach_menu()

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
