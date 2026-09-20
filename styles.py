"""
styles.py - High-contrast design system, tokenized palettes, and QSS stylesheets for Sticky Notes.
Engineered for maximum legibility, WCAG AAA contrast, and modern WinUI 3 / Fluent styling.
"""

from typing import Dict, Any

NOTE_COLORS = [
    {"name": "Butter Yellow", "hex": "#FFF9C4", "dark": False, "border": "#E6D775", "dark_hex": "#3A351E"},
    {"name": "Mint Green",   "hex": "#C8E6C9", "dark": False, "border": "#81C784", "dark_hex": "#1E3825"},
    {"name": "Soft Coral",   "hex": "#FFCDD2", "dark": False, "border": "#E57373", "dark_hex": "#3E2224"},
    {"name": "Lavender",     "hex": "#E1BEE7", "dark": False, "border": "#BA68C8", "dark_hex": "#34203A"},
    {"name": "Sky Blue",     "hex": "#BBDEFB", "dark": False, "border": "#64B5F6", "dark_hex": "#1B2C3F"},
    {"name": "Warm Peach",   "hex": "#FFE0B2", "dark": False, "border": "#FFB74D", "dark_hex": "#3D2B1A"},
    {"name": "Soft Pink",    "hex": "#F8BBD0", "dark": False, "border": "#F06292", "dark_hex": "#3C1D2A"},
    {"name": "Slate Dark",   "hex": "#1E1F20", "dark": True,  "border": "#444746", "dark_hex": "#1E1F20"},
]

THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg_main": "#F8FAFC",              # Clean light slate canvas
        "bg_surface": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "text_primary": "#0F172A",         # Deep slate-900 - maximum contrast
        "text_secondary": "#334155",       # Slate-700 - sharp, never washed-out
        "text_muted": "#475569",           # Slate-600
        "border": "#CBD5E1",               # Slate-300 - crisp, defined edges
        "border_subtle": "#E2E8F0",
        "accent": "#2563EB",               # Vibrant blue
        "accent_hover": "#1D4ED8",
        "accent_pressed": "#1E40AF",
        "accent_text": "#FFFFFF",
        "btn_bg": "#FFFFFF",
        "btn_hover": "#F1F5F9",
        "btn_text": "#0F172A",             # High contrast button label
        "input_bg": "#FFFFFF",
        "input_border": "#94A3B8",
        "pill_bg": "#F1F5F9",
        "pill_text": "#1E293B",            # Crisp readable filter chips
        "scrollbar_handle": "#94A3B8",
        "scrollbar_hover": "#64748B",
        "action_bar_bg": "#FFFFFF",
        "action_bar_border": "#CBD5E1",
        "menu_bg": "#FFFFFF",
    },
    "dark": {
        "bg_main": "#131314",              # Neutral carbon obsidian canvas
        "bg_surface": "#1E1F20",           # Clean neutral elevated surface
        "bg_card": "#1E1F20",
        "text_primary": "#E3E3E3",         # Bright neutral white text
        "text_secondary": "#C4C7C5",       # Soft legible gray
        "text_muted": "#8E918F",           # Muted gray
        "border": "#444746",               # Neutral outline border
        "border_subtle": "#2D2E30",
        "accent": "#8AB4F8",               # Google Gemini electric light blue
        "accent_hover": "#A8C7FA",
        "accent_pressed": "#669DF6",
        "accent_text": "#041E49",          # Deep contrast text on accent fill
        "btn_bg": "#28292A",
        "btn_hover": "#333537",
        "btn_text": "#E3E3E3",             # Pure bright white button label
        "input_bg": "#1E1F20",
        "input_border": "#444746",
        "pill_bg": "#28292A",
        "pill_text": "#E3E3E3",
        "scrollbar_handle": "#444746",
        "scrollbar_hover": "#5E5E5E",
        "action_bar_bg": "#1E1F20",
        "action_bar_border": "#444746",
        "menu_bg": "#1E1F20",
    },
    "sepia": {
        "bg_main": "#F7F2E7",              # Warm parchment canvas
        "bg_surface": "#FFFDF9",
        "bg_card": "#FFFDF9",
        "text_primary": "#2D2319",         # Deep espresso text
        "text_secondary": "#574737",
        "text_muted": "#6E5D4D",
        "border": "#D5C7B3",
        "border_subtle": "#E7DDCF",
        "accent": "#8C5A2B",
        "accent_hover": "#73471E",
        "accent_pressed": "#5A3414",
        "accent_text": "#FFFFFF",
        "btn_bg": "#FFFDF9",
        "btn_hover": "#F0E7D8",
        "btn_text": "#2D2319",
        "input_bg": "#FFFDF9",
        "input_border": "#C4B49F",
        "pill_bg": "#F0E7D8",
        "pill_text": "#2D2319",
        "scrollbar_handle": "#B8A790",
        "scrollbar_hover": "#8C7A65",
        "action_bar_bg": "#FFFDF9",
        "action_bar_border": "#D5C7B3",
        "menu_bg": "#FFFDF9",
    }
}


def is_dark_color(hex_code: str) -> bool:
    """Determine if a hex color is dark to pick white or black text."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) != 6:
        return False
    try:
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5
    except ValueError:
        return False


def generate_app_stylesheet(theme: str = "light") -> str:
    """Generates complete QSS stylesheet dynamically from tokenized theme palette."""
    pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

    return f"""
QMainWindow {{
    background-color: {pal["bg_main"]};
}}

QWidget#CentralWidget {{
    background-color: {pal["bg_main"]};
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
}}

QWidget#GridViewContainer, QWidget#EditorViewContainer {{
    background-color: {pal["bg_main"]};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* Crisp Modern Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
    margin: 4px 0 4px 0;
}}

QScrollBar::handle:vertical {{
    background: {pal["scrollbar_handle"]};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {pal["scrollbar_hover"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Typography */
QLabel#AppHeaderTitle {{
    font-size: 26px;
    font-weight: 700;
    color: {pal["text_primary"]};
    margin: 0;
    padding: 0;
}}

QLabel#AppHeaderSubtitle {{
    font-size: 13px;
    font-weight: 500;
    color: {pal["text_secondary"]};
}}

/* Primary Action Button (+ New Note) */
QPushButton#NewNoteButton {{
    background-color: {pal["accent"]};
    color: {pal["accent_text"]};
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 18px;
}}

QPushButton#NewNoteButton:hover {{
    background-color: {pal["accent_hover"]};
}}

QPushButton#NewNoteButton:pressed {{
    background-color: {pal["accent_pressed"]};
}}

/* Standard High-Contrast Buttons */
QPushButton#ThemeToggleBtn, QPushButton#SelectModeButton {{
    background-color: {pal["btn_bg"]};
    color: {pal["btn_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#ThemeToggleBtn:hover, QPushButton#SelectModeButton:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

QPushButton#EditorHeaderBtn {{
    background-color: {pal["btn_bg"]};
    color: {pal["btn_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 2px;
    font-size: 15px;
    font-weight: 600;
}}

QPushButton#EditorHeaderBtn:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

/* In-App Audio Player */
QFrame#AudioPlayerFrame {{
    background-color: {pal["bg_surface"]};
    border: 1px solid {pal["border"]};
    border-radius: 10px;
    padding: 6px 12px;
}}

QFrame#AudioPlayerFrame QPushButton {{
    background-color: {pal["btn_bg"]};
    color: {pal["btn_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 6px;
    font-weight: 700;
}}

QFrame#AudioPlayerFrame QPushButton:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

QFrame#AudioPlayerFrame QLabel {{
    color: {pal["text_primary"]};
    background: transparent;
}}

QFrame#AudioPlayerFrame QLabel#AudioTimeLabel {{
    color: {pal["text_secondary"]};
    font-size: 11px;
    font-weight: 600;
}}

QPushButton#BackButton {{
    background-color: {pal["btn_bg"]};
    color: {pal["btn_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 6px;
}}

QPushButton#BackButton:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

QPushButton#CardMenuBtn, QPushButton#CardPaletteBtn {{
    background-color: transparent;
    border: none;
    border-radius: 5px;
    padding: 2px;
}}

QPushButton#CardMenuBtn:hover, QPushButton#CardPaletteBtn:hover {{
    background-color: rgba(128, 128, 128, 0.20);
}}

/* Modern Search Bar */
QLineEdit#SearchInput {{
    background-color: {pal["input_bg"]};
    color: {pal["text_primary"]};
    border: 1px solid {pal["input_border"]};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
}}

QLineEdit#SearchInput:focus {{
    border: 2px solid {pal["accent"]};
    background-color: {pal["bg_surface"]};
}}

/* Interactive Color Filter Chips */
QPushButton#FilterPill {{
    background-color: {pal["pill_bg"]};
    color: {pal["pill_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 14px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#FilterPill:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

QPushButton#FilterPill[active="true"] {{
    background-color: {pal["accent"]};
    color: {pal["accent_text"]};
    border-color: {pal["accent"]};
    font-weight: 700;
}}

/* Editor Inputs */
QLineEdit#NoteTitleInput {{
    font-size: 22px;
    font-weight: 700;
    color: {pal["text_primary"]};
    border: 1px solid transparent;
    background-color: transparent;
    border-radius: 6px;
    padding: 6px 8px;
}}

QLineEdit#NoteTitleInput:focus {{
    border: 1px solid {pal["accent"]};
    background-color: {pal["input_bg"]};
}}

QTextEdit#MarkdownEditor {{
    border: 1px solid {pal["border"]};
    border-radius: 10px;
    background-color: {pal["input_bg"]};
    color: {pal["text_primary"]};
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 14px;
    line-height: 1.5;
    padding: 14px;
}}

QTextBrowser#MarkdownPreview {{
    border: 1px solid {pal["border"]};
    border-radius: 10px;
    background-color: {pal["input_bg"]};
    color: {pal["text_primary"]};
    padding: 14px 18px;
}}

/* Segmented View Mode Tabs */
QFrame#ModeSelectorFrame {{
    background-color: {pal["pill_bg"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 2px;
}}

QPushButton#ModeTabButton {{
    background-color: transparent;
    color: {pal["text_secondary"]};
    border: none;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#ModeTabButton:hover {{
    color: {pal["text_primary"]};
}}

QPushButton#ModeTabButton[active="true"] {{
    background-color: {pal["btn_bg"]};
    color: {pal["accent"]};
    border: 1px solid {pal["border_subtle"]};
    font-weight: 700;
}}

/* Format Toolbar */
QFrame#FormatToolbarFrame {{
    background-color: {pal["btn_bg"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 3px 6px;
}}

QPushButton#FormatButton {{
    background-color: transparent;
    color: {pal["btn_text"]};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#FormatButton:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["border"]};
}}

/* Bottom Multi-Select Action Bar */
QFrame#SelectionActionBar {{
    background-color: {pal["action_bar_bg"]};
    border: 2px solid {pal["action_bar_border"]};
    border-radius: 12px;
    padding: 8px 18px;
}}

QLabel#SelectionCountLabel {{
    font-size: 14px;
    font-weight: 700;
    color: {pal["text_primary"]};
}}

QPushButton#SelectAllButton {{
    background-color: {pal["btn_bg"]};
    color: {pal["btn_text"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}}

QPushButton#SelectAllButton:hover {{
    background-color: {pal["btn_hover"]};
    border-color: {pal["accent"]};
}}

QPushButton#DeleteSelectedButton {{
    background-color: #DC2626;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 700;
}}

QPushButton#DeleteSelectedButton:hover {{
    background-color: #B91C1C;
}}

/* Empty State Card */
QFrame#EmptyStateCard {{
    background-color: {pal["bg_surface"]};
    border: 1px dashed {pal["border"]};
    border-radius: 14px;
    padding: 32px;
}}

QLabel#EmptyStateTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {pal["text_primary"]};
}}

QLabel#EmptyStateSubtitle {{
    font-size: 13px;
    font-weight: 500;
    color: {pal["text_secondary"]};
}}

/* Menus */
QMenu {{
    background-color: {pal["menu_bg"]};
    color: {pal["text_primary"]};
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 4px;
    color: {pal["text_primary"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {pal["border_subtle"]};
    margin: 4px 6px;
}}

/* Themed Dialogs & Windows */
QDialog {{
    background-color: {pal["bg_main"]};
    color: {pal["text_primary"]};
}}

QTabWidget::pane {{
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    background-color: {pal["bg_surface"]};
    padding: 12px;
}}

QTabBar::tab {{
    background-color: {pal["btn_bg"]};
    color: {pal["text_secondary"]};
    border: 1px solid {pal["border"]};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    margin-right: 4px;
}}

QTabBar::tab:selected {{
    background-color: {pal["bg_surface"]};
    color: {pal["accent"]};
    border-color: {pal["border"]};
    border-bottom: 2px solid {pal["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {pal["btn_hover"]};
    color: {pal["text_primary"]};
}}

/* Dialogs, Flyouts & Modals */
QDialog {{
    background-color: {pal["bg_surface"]};
    color: {pal["text_primary"]};
}}

QDialog QLabel {{
    color: {pal["text_primary"]};
}}

/* Help Dialog Keyboard Badges */
QLabel.KbdBadge {{
    background-color: {pal["btn_hover"]};
    color: {pal["accent"]};
    border: 1px solid {pal["border"]};
    border-radius: 4px;
    padding: 2px 6px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-weight: 700;
    font-size: 12px;
}}
"""


def get_markdown_preview_css(theme: str = "light") -> str:
    """Generates theme-aware CSS for rendered Markdown preview."""
    if theme == "dark":
        bg_body = "#1E1F20"
        text_body = "#E3E3E3"
        heading_color = "#FFFFFF"
        code_bg = "rgba(255, 255, 255, 0.12)"
        pre_bg = "#131314"
        border_color = "#444746"
        link_color = "#8AB4F8"
        quote_border = "#8AB4F8"
        quote_text = "#C4C7C5"
    elif theme == "sepia":
        bg_body = "#FFFDF9"
        text_body = "#2D2319"
        heading_color = "#1D160F"
        code_bg = "rgba(61, 51, 42, 0.10)"
        pre_bg = "#F7F2E7"
        border_color = "#D5C7B3"
        link_color = "#8C5A2B"
        quote_border = "#8C5A2B"
        quote_text = "#574737"
    else:  # light
        bg_body = "#FFFFFF"
        text_body = "#0F172A"
        heading_color = "#0F172A"
        code_bg = "rgba(15, 23, 42, 0.08)"
        pre_bg = "#F1F5F9"
        border_color = "#CBD5E1"
        link_color = "#2563EB"
        quote_border = "#2563EB"
        quote_text = "#334155"

    return f"""
<style>
body {{
    background-color: {bg_body};
    font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
    font-size: 14px;
    color: {text_body};
    line-height: 1.6;
    margin: 8px 12px;
}}
h1, h2, h3, h4 {{
    color: {heading_color};
    margin-top: 14px;
    margin-bottom: 8px;
    font-weight: 700;
}}
h1 {{ font-size: 1.6em; border-bottom: 2px solid {border_color}; padding-bottom: 4px; }}
h2 {{ font-size: 1.3em; border-bottom: 1px solid {border_color}; padding-bottom: 3px; }}
h3 {{ font-size: 1.1em; }}
code {{
    background-color: {code_bg};
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 2px 5px;
    font-size: 88%;
    font-weight: 600;
}}
pre {{
    background-color: {pre_bg};
    border-radius: 8px;
    padding: 12px;
    overflow: auto;
    border: 1px solid {border_color};
}}
pre code {{
    background-color: transparent;
    padding: 0;
}}
blockquote {{
    border-left: 4px solid {quote_border};
    color: {quote_text};
    padding-left: 12px;
    margin-left: 0;
    font-style: italic;
}}
ul, ol {{
    padding-left: 20px;
}}
li {{
    margin-bottom: 4px;
}}
u {{
    text-decoration: underline;
}}
del, s, strike {{
    text-decoration: line-through;
    opacity: 0.70;
}}
img {{
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 10px 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    display: block;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}}
th, td {{
    border: 1px solid {border_color};
    padding: 8px 12px;
    text-align: left;
}}
th {{
    background-color: {pre_bg};
    font-weight: 700;
}}
.codehilite {{
    background-color: {pre_bg};
    border: 1px solid {border_color};
    border-radius: 8px;
    padding: 10px;
    margin: 10px 0;
}}
a {{
    color: {link_color};
    text-decoration: none;
    font-weight: 600;
}}
a:hover {{
    text-decoration: underline;
}}
</style>
"""

APP_STYLESHEET = generate_app_stylesheet("light")
MARKDOWN_PREVIEW_CSS = get_markdown_preview_css("light")
