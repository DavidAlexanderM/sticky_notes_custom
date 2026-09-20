from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, 
    QTextEdit
)
from PySide6.QtGui import QCursor, QTextCursor

class FormatButton(QPushButton):
    """Compact toolbar button styled in Fluent minimal aesthetic."""
    def __init__(self, text: str, tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("FormatButton")
        if tooltip:
            self.setToolTip(tooltip)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(28)

class FormatToolbar(QFrame):
    """
    Rich text formatting and media attachment toolbar.
    """
    add_picture_requested = Signal()
    add_audio_requested = Signal()
    add_video_requested = Signal()

    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setObjectName("FormatToolbarFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(4)

        # Bold (B)
        self.btn_bold = FormatButton("B", "Bold (Ctrl+B)", self)
        self.btn_bold.setStyleSheet(self.btn_bold.styleSheet() + "font-weight: 800; font-family: 'Times New Roman', serif; font-size: 14px;")
        self.btn_bold.clicked.connect(self.apply_bold)
        layout.addWidget(self.btn_bold)

        # Italics (I)
        self.btn_italic = FormatButton("I", "Italics (Ctrl+I)", self)
        self.btn_italic.clicked.connect(self.apply_italic)
        layout.addWidget(self.btn_italic)

        # Underline (U)
        self.btn_underline = FormatButton("U", "Underline (Ctrl+U)", self)
        self.btn_underline.clicked.connect(self.apply_underline)
        layout.addWidget(self.btn_underline)

        # Strikethrough (S)
        self.btn_strike = FormatButton("S", "Strikethrough", self)
        self.btn_strike.clicked.connect(self.apply_strikethrough)
        layout.addWidget(self.btn_strike)

        layout.addWidget(self._create_separator())

        # Heading (H)
        self.btn_heading = FormatButton("H", "Heading (##)", self)
        self.btn_heading.clicked.connect(self.apply_heading)
        layout.addWidget(self.btn_heading)

        # Bullet List (•)
        self.btn_bullet = FormatButton("• List", "Bullet List (- )", self)
        self.btn_bullet.clicked.connect(self.apply_bullet_list)
        layout.addWidget(self.btn_bullet)

        # Task Checklist (☑)
        self.btn_check = FormatButton("☑ Task", "Task Checklist (- [ ])", self)
        self.btn_check.clicked.connect(self.apply_task_list)
        layout.addWidget(self.btn_check)

        # Code (<>)
        self.btn_code = FormatButton("< >", "Code Block", self)
        self.btn_code.clicked.connect(self.apply_code)
        layout.addWidget(self.btn_code)

        layout.addWidget(self._create_separator())

        # Media: Picture
        self.btn_picture = FormatButton("🖼 Picture", "Insert Picture / Photo", self)
        self.btn_picture.clicked.connect(self.add_picture_requested.emit)
        layout.addWidget(self.btn_picture)

        # Media: Audio / Voice
        self.btn_audio = FormatButton("🎙 Audio", "Record Voice Note or Attach Audio", self)
        self.btn_audio.clicked.connect(self.add_audio_requested.emit)
        layout.addWidget(self.btn_audio)

        # Media: Video
        self.btn_video = FormatButton("🎥 Video", "Attach Video File", self)
        self.btn_video.clicked.connect(self.add_video_requested.emit)
        layout.addWidget(self.btn_video)

        layout.addStretch()

    def _create_separator(self) -> QFrame:
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(0, 0, 0, 0.12); margin: 3px 2px;")
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
