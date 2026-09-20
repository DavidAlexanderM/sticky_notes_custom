"""
Styles and color definitions for Fluent / WinUI 3 minimal theme.
"""

NOTE_COLORS = [
    {"name": "Butter Yellow", "hex": "#FFF9C4", "dark": False, "border": "#F0E68C"},
    {"name": "Mint Green",   "hex": "#C8E6C9", "dark": False, "border": "#A5D6A7"},
    {"name": "Soft Coral",   "hex": "#FFCDD2", "dark": False, "border": "#EF9A9A"},
    {"name": "Lavender",     "hex": "#E1BEE7", "dark": False, "border": "#CE93D8"},
    {"name": "Sky Blue",     "hex": "#BBDEFB", "dark": False, "border": "#90CAF9"},
    {"name": "Warm Peach",   "hex": "#FFE0B2", "dark": False, "border": "#FFCC80"},
    {"name": "Soft Pink",    "hex": "#F8BBD0", "dark": False, "border": "#F48FB1"},
    {"name": "Slate Dark",   "hex": "#27272A", "dark": True,  "border": "#3F3F46"},
]

def is_dark_color(hex_code: str) -> bool:
    """Determine if a hex color is dark to pick white or black text."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) != 6:
        return False
    r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    # Standard relative luminance formula
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5

APP_STYLESHEET = """
QMainWindow {
    background-color: #F3F3F3;
}

QWidget#CentralWidget {
    background-color: #F3F3F3;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 4px 0 4px 0;
}

QScrollBar::handle:vertical {
    background: rgba(0, 0, 0, 0.2);
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(0, 0, 0, 0.4);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Header & Navigation */
QLabel#AppHeaderTitle {
    font-size: 24px;
    font-weight: 700;
    color: #1A1A1A;
    margin: 0;
    padding: 0;
}

QLabel#AppHeaderSubtitle {
    font-size: 13px;
    color: #6E6E6E;
}

QPushButton#NewNoteButton {
    background-color: #0067C0;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 16px;
}

QPushButton#NewNoteButton:hover {
    background-color: #005FB8;
}

QPushButton#NewNoteButton:pressed {
    background-color: #0054A6;
}

/* Back Button */
QPushButton#BackButton {
    background-color: transparent;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 16px;
    font-weight: bold;
    color: #1F1F1F;
}

QPushButton#BackButton:hover {
    background-color: rgba(0, 0, 0, 0.05);
    border-color: rgba(0, 0, 0, 0.15);
}

QPushButton#BackButton:pressed {
    background-color: rgba(0, 0, 0, 0.1);
}

/* Editor Inputs */
QLineEdit#NoteTitleInput {
    font-size: 22px;
    font-weight: 700;
    color: #1F1F1F;
    border: 1px solid transparent;
    background-color: transparent;
    border-radius: 6px;
    padding: 6px 8px;
}

QLineEdit#NoteTitleInput:focus {
    border: 1px solid #0067C0;
    background-color: #FFFFFF;
}

QTextEdit#MarkdownEditor {
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    background-color: #FFFFFF;
    color: #1E1E1E;
    font-family: "Cascadia Code", "Consolas", "Segoe UI", monospace;
    font-size: 14px;
    line-height: 1.5;
    padding: 12px;
}

QTextBrowser#MarkdownPreview {
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    background-color: #FFFFFF;
    color: #1E1E1E;
    font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 14px;
    padding: 14px 18px;
}

/* Segmented Toggle Buttons */
QPushButton#ModeTabButton {
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 600;
    color: #5C5C5C;
}

QPushButton#ModeTabButton:hover {
    color: #1F1F1F;
}

QPushButton#ModeTabButton[active="true"] {
    color: #0067C0;
    border-bottom: 2px solid #0067C0;
}
"""

MARKDOWN_PREVIEW_CSS = """
<style>
body {
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-size: 14px;
    color: #24292f;
    line-height: 1.6;
}
h1, h2, h3, h4 {
    color: #1a1f2c;
    margin-top: 14px;
    margin-bottom: 8px;
    font-weight: 600;
}
h1 { font-size: 1.6em; border-bottom: 1px solid #e1e4e8; padding-bottom: 4px; }
h2 { font-size: 1.3em; border-bottom: 1px solid #eaecef; padding-bottom: 3px; }
h3 { font-size: 1.1em; }
code {
    background-color: rgba(175, 184, 193, 0.2);
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 2px 5px;
    font-size: 85%;
}
pre {
    background-color: #f6f8fa;
    border-radius: 6px;
    padding: 10px;
    overflow: auto;
    border: 1px solid #e1e4e8;
}
pre code {
    background-color: transparent;
    padding: 0;
}
blockquote {
    border-left: 3px solid #0067C0;
    color: #57606a;
    padding-left: 10px;
    margin-left: 0;
}
ul, ol {
    padding-left: 20px;
}
li {
    margin-bottom: 4px;
}
u {
    text-decoration: underline;
}
del, s, strike {
    text-decoration: line-through;
    color: #8c959f;
}
img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 10px 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    display: block;
}
a {
    color: #0969da;
    text-decoration: none;
    font-weight: 500;
}
a:hover {
    text-decoration: underline;
}
</style>
"""
