"""
styles.py - Design system, tokenized palettes, and QSS stylesheets for Sticky Notes.
Supports Light, Dark, and Sepia themes with responsive typography and Fluent/WinUI 3 styling.
"""

from typing import Dict, Any

NOTE_COLORS = [
    {"name": "Butter Yellow", "hex": "#FFF9C4", "dark": False, "border": "#F0E68C", "dark_hex": "#3A351E"},
    {"name": "Mint Green",   "hex": "#C8E6C9", "dark": False, "border": "#A5D6A7", "dark_hex": "#1E3825"},
    {"name": "Soft Coral",   "hex": "#FFCDD2", "dark": False, "border": "#EF9A9A", "dark_hex": "#3E2224"},
    {"name": "Lavender",     "hex": "#E1BEE7", "dark": False, "border": "#CE93D8", "dark_hex": "#34203A"},
    {"name": "Sky Blue",     "hex": "#BBDEFB", "dark": False, "border": "#90CAF9", "dark_hex": "#1B2C3F"},
    {"name": "Warm Peach",   "hex": "#FFE0B2", "dark": False, "border": "#FFCC80", "dark_hex": "#3D2B1A"},
    {"name": "Soft Pink",    "hex": "#F8BBD0", "dark": False, "border": "#F48FB1", "dark_hex": "#3C1D2A"},
    {"name": "Slate Dark",   "hex": "#27272A", "dark": True,  "border": "#3F3F46", "dark_hex": "#27272A"},
]

THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg_main": "#F4F5F7",
        "bg_surface": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "text_primary": "#1A1A1A",
        "text_secondary": "#64748B",
        "text_muted": "#94A3B8",
        "border": "rgba(0, 0, 0, 0.08)",
        "border_subtle": "rgba(0, 0, 0, 0.04)",
        "accent": "#0067C0",
        "accent_hover": "#005FB8",
        "accent_pressed": "#0054A6",
        "accent_text": "#FFFFFF",
        "input_bg": "#FFFFFF",
        "input_border": "rgba(0, 0, 0, 0.12)",
        "scrollbar_handle": "rgba(0, 0, 0, 0.18)",
        "scrollbar_hover": "rgba(0, 0, 0, 0.35)",
        "shadow_color": "rgba(0, 0, 0, 0.08)",
        "card_border": "rgba(0, 0, 0, 0.07)",
        "menu_bg": "#FFFFFF",
        "toolbar_bg": "rgba(255, 255, 255, 0.95)",
    },
    "dark": {
        "bg_main": "#121214",
        "bg_surface": "#1E1E22",
        "bg_card": "#26262B",
        "text_primary": "#F4F4F5",
        "text_secondary": "#A1A1AA",
        "text_muted": "#71717A",
        "border": "rgba(255, 255, 255, 0.12)",
        "border_subtle": "rgba(255, 255, 255, 0.06)",
        "accent": "#38BDF8",
        "accent_hover": "#0EA5E9",
        "accent_pressed": "#0284C7",
        "accent_text": "#0F172A",
        "input_bg": "#1E1E22",
        "input_border": "rgba(255, 255, 255, 0.16)",
        "scrollbar_handle": "rgba(255, 255, 255, 0.22)",
        "scrollbar_hover": "rgba(255, 255, 255, 0.40)",
        "shadow_color": "rgba(0, 0, 0, 0.40)",
        "card_border": "rgba(255, 255, 255, 0.10)",
        "menu_bg": "#1E1E22",
        "toolbar_bg": "rgba(30, 30, 34, 0.95)",
    },
    "sepia": {
        "bg_main": "#F7F2E7",
        "bg_surface": "#FFFDF9",
        "bg_card": "#FFFDF9",
        "text_primary": "#3D332A",
        "text_secondary": "#786C5E",
        "text_muted": "#A89C8F",
        "border": "rgba(61, 51, 42, 0.12)",
        "border_subtle": "rgba(61, 51, 42, 0.06)",
        "accent": "#8C5A2B",
        "accent_hover": "#73471E",
        "accent_pressed": "#5A3414",
        "accent_text": "#FFFFFF",
        "input_bg": "#FFFDF9",
        "input_border": "rgba(61, 51, 42, 0.16)",
        "scrollbar_handle": "rgba(61, 51, 42, 0.20)",
        "scrollbar_hover": "rgba(61, 51, 42, 0.38)",
        "shadow_color": "rgba(61, 51, 42, 0.10)",
        "card_border": "rgba(61, 51, 42, 0.09)",
        "menu_bg": "#FFFDF9",
        "toolbar_bg": "rgba(255, 253, 249, 0.95)",
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

/* Clean Modern Scrollbars */
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
    color: {pal["text_secondary"]};
}}

/* Buttons */
QPushButton#NewNoteButton {{
    background-color: {pal["accent"]};
    color: {pal["accent_text"]};
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 18px;
}}

QPushButton#NewNoteButton:hover {{
    background-color: {pal["accent_hover"]};
}}

QPushButton#NewNoteButton:pressed {{
    background-color: {pal["accent_pressed"]};
}}

QPushButton#ThemeToggleBtn {{
    background-color: transparent;
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 14px;
    color: {pal["text_primary"]};
}}

QPushButton#ThemeToggleBtn:hover {{
    background-color: {pal["border_subtle"]};
    border-color: {pal["accent"]};
}}

QPushButton#BackButton {{
    background-color: transparent;
    border: 1px solid {pal["border"]};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 16px;
    font-weight: bold;
    color: {pal["text_primary"]};
}}

QPushButton#BackButton:hover {{
    background-color: {pal["border_subtle"]};
    border-color: {pal["accent"]};
}}

/* Modern Search Bar */
QLineEdit#SearchInput {{
    background-color: {pal["input_bg"]};
    color: {pal["text_primary"]};
    border: 1px solid {pal["input_border"]};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
}}

QLineEdit#SearchInput:focus {{
    border: 2px solid {pal["accent"]};
    background-color: {pal["bg_surface"]};
}}

/* Color Filter Chips */
QPushButton#FilterPill {{
    background-color: transparent;
    border: 1px solid {pal["border"]};
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
    color: {pal["text_secondary"]};
}}

QPushButton#FilterPill:hover {{
    background-color: {pal["border_subtle"]};
    color: {pal["text_primary"]};
}}

QPushButton#FilterPill[active="true"] {{
    background-color: {pal["accent"]};
    color: {pal["accent_text"]};
    border-color: {pal["accent"]};
    font-weight: 600;
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
QPushButton#ModeTabButton {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: {pal["text_secondary"]};
}}

QPushButton#ModeTabButton:hover {{
    color: {pal["text_primary"]};
}}

QPushButton#ModeTabButton[active="true"] {{
    color: {pal["accent"]};
    border-bottom: 2px solid {pal["accent"]};
}}

/* Empty State Card */
QFrame#EmptyStateCard {{
    background-color: {pal["bg_surface"]};
    border: 1px dashed {pal["border"]};
    border-radius: 14px;
    padding: 30px;
}}

/* Menus & Toolbars */
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
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {pal["accent"]};
    color: {pal["accent_text"]};
}}
"""


def get_markdown_preview_css(theme: str = "light") -> str:
    """Generates theme-aware CSS for rendered Markdown preview."""
    if theme == "dark":
        bg_body = "#1E1E22"
        text_body = "#E4E4E7"
        heading_color = "#FAFAFA"
        code_bg = "rgba(255, 255, 255, 0.12)"
        pre_bg = "#18181B"
        border_color = "rgba(255, 255, 255, 0.12)"
        link_color = "#38BDF8"
        quote_border = "#38BDF8"
        quote_text = "#A1A1AA"
    elif theme == "sepia":
        bg_body = "#FFFDF9"
        text_body = "#3D332A"
        heading_color = "#241D17"
        code_bg = "rgba(61, 51, 42, 0.10)"
        pre_bg = "#F7F2E7"
        border_color = "rgba(61, 51, 42, 0.12)"
        link_color = "#8C5A2B"
        quote_border = "#8C5A2B"
        quote_text = "#786C5E"
    else:  # light
        bg_body = "#FFFFFF"
        text_body = "#24292F"
        heading_color = "#1A1F2C"
        code_bg = "rgba(175, 184, 193, 0.20)"
        pre_bg = "#F6F8FA"
        border_color = "#E1E4E8"
        link_color = "#0969DA"
        quote_border = "#0067C0"
        quote_text = "#57606A"

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
    font-weight: 600;
}}
h1 {{ font-size: 1.6em; border-bottom: 1px solid {border_color}; padding-bottom: 4px; }}
h2 {{ font-size: 1.3em; border-bottom: 1px solid {border_color}; padding-bottom: 3px; }}
h3 {{ font-size: 1.1em; }}
code {{
    background-color: {code_bg};
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 2px 5px;
    font-size: 85%;
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
    border-left: 3px solid {quote_border};
    color: {quote_text};
    padding-left: 10px;
    margin-left: 0;
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
    opacity: 0.65;
}}
img {{
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 10px 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.10);
    display: block;
}}
a {{
    color: {link_color};
    text-decoration: none;
    font-weight: 500;
}}
a:hover {{
    text-decoration: underline;
}}
</style>
"""

# Backwards compatible defaults
APP_STYLESHEET = generate_app_stylesheet("light")
MARKDOWN_PREVIEW_CSS = get_markdown_preview_css("light")
