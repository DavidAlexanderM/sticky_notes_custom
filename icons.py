"""
icons.py - Pure PySide6 SVG Vector Icon Engine for Sticky Notes.
Generates razor-sharp, resolution-independent QIcon and QPixmap objects
dynamically tinted to match Light, Dark, and Sepia themes.
"""

from typing import Dict, Optional
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

try:
    from .styles import THEME_PALETTES
    from .theme_manager import get_theme_manager
except ImportError:
    from styles import THEME_PALETTES
    from theme_manager import get_theme_manager

# Standard 24x24 Lucide / Fluent vector SVG path fragments
SVG_PATHS: Dict[str, str] = {
    "arrow_left": '<line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>',
    "share": '<circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>',
    "sun": '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line>',
    "search": '<circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>',
    "check": '<polyline points="20 6 9 17 4 12"></polyline>',
    "check_square": '<polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>',
    "square": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>',
    "trash": '<polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>',
    "more_horizontal": '<circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none"></circle><circle cx="19" cy="12" r="1.8" fill="currentColor" stroke="none"></circle><circle cx="5" cy="12" r="1.8" fill="currentColor" stroke="none"></circle>',
    "bold": '<path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"></path>',
    "italic": '<line x1="19" y1="4" x2="10" y2="4"></line><line x1="14" y1="20" x2="5" y2="20"></line><line x1="15" y1="4" x2="9" y2="20"></line>',
    "underline": '<path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"></path><line x1="4" y1="21" x2="20" y2="21"></line>',
    "strikethrough": '<path d="M16 6a4 4 0 0 0-8 0c0 4 8 2 8 6a4 4 0 0 1-8 0"></path><line x1="4" y1="12" x2="20" y2="12"></line>',
    "heading": '<path d="M6 12h12"></path><path d="M6 4v16"></path><path d="M18 4v16"></path>',
    "list": '<line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><circle cx="4" cy="6" r="1.5" fill="currentColor" stroke="none"></circle><circle cx="4" cy="12" r="1.5" fill="currentColor" stroke="none"></circle><circle cx="4" cy="18" r="1.5" fill="currentColor" stroke="none"></circle>',
    "code": '<polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline>',
    "mic": '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line>',
    "video": '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>',
    "palette": '<circle cx="13.5" cy="6.5" r=".6" fill="currentColor" stroke="none"></circle><circle cx="17.5" cy="10.5" r=".6" fill="currentColor" stroke="none"></circle><circle cx="8.5" cy="7.5" r=".6" fill="currentColor" stroke="none"></circle><circle cx="6.5" cy="12.5" r=".6" fill="currentColor" stroke="none"></circle><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.6-.7 1.6-1.6 0-.4-.2-.8-.4-1.1-.3-.3-.4-.7-.4-1.1 0-.9.7-1.6 1.6-1.6H16c3.3 0 6-2.7 6-6 0-4.4-4.5-8-10-8z"></path>',
    "play": '<polygon points="6 4 19 12 6 20 6 4" fill="currentColor" stroke="none"></polygon>',
    "pause": '<rect x="6" y="5" width="3.5" height="14" rx="1" fill="currentColor" stroke="none"></rect><rect x="14.5" y="5" width="3.5" height="14" rx="1" fill="currentColor" stroke="none"></rect>',
    "external_link": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line>',
    "close": '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>',
    "clock": '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>',
    "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>',
    "pin": '<path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4a2 2 0 0 0-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41 0-.55-.23-1.06-.59-1.42z"></path><circle cx="9" cy="9" r="2"></circle>',
    "help_circle": '<circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line>',
    "info": '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>',
    "keyboard": '<rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect><line x1="6" y1="8" x2="6" y2="8"></line><line x1="10" y1="8" x2="10" y2="8"></line><line x1="14" y1="8" x2="14" y2="8"></line><line x1="18" y1="8" x2="18" y2="8"></line><line x1="6" y1="12" x2="6" y2="12"></line><line x1="10" y1="12" x2="10" y2="12"></line><line x1="14" y1="12" x2="14" y2="12"></line><line x1="18" y1="12" x2="18" y2="12"></line><line x1="7" y1="16" x2="17" y2="16"></line>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line>',
    "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline>',
    "mail": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline>',
    "message_circle": '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>',
    "file_text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line>',
    "globe": '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>'
}

_ICON_CACHE: Dict[str, QIcon] = {}


def render_svg_pixmap(name: str, color: str = "#000000", size: int = 20) -> QPixmap:
    """Renders an SVG path into a crisp transparent QPixmap."""
    path_data = SVG_PATHS.get(name)
    if not path_data:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        return pix

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" color="{color}">
{path_data}
</svg>"""

    svg_bytes = QByteArray(svg_content.encode("utf-8"))
    renderer = QSvgRenderer(svg_bytes)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()

    return pixmap


def get_icon(name: str, color: str = "#0F172A", size: int = 20) -> QIcon:
    """Returns a QIcon for a given SVG name, color, and pixel size with caching."""
    cache_key = f"{name}_{color}_{size}"
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    pixmap = render_svg_pixmap(name, color=color, size=size)
    icon = QIcon(pixmap)
    _ICON_CACHE[cache_key] = icon
    return icon


def get_themed_icon(
    name: str, 
    role: str = "primary", 
    theme: Optional[str] = None, 
    size: int = 20
) -> QIcon:
    """
    Returns an icon dynamically tinted based on active theme role:
    - primary: main button / label text
    - secondary: subtle icon
    - accent: bright accent color (blue/sky)
    - muted: dimmed slate
    - danger: red warning color
    - white: pure white
    """
    if theme is None:
        try:
            theme = get_theme_manager().current_theme
        except Exception:
            theme = "light"

    pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

    color_map = {
        "primary": pal.get("text_primary", "#0F172A"),
        "secondary": pal.get("text_secondary", "#334155"),
        "accent": pal.get("accent", "#2563EB"),
        "muted": pal.get("text_muted", "#64748B"),
        "danger": "#DC2626",
        "white": "#FFFFFF",
        "btn_text": pal.get("btn_text", "#0F172A"),
    }

    color = color_map.get(role, pal.get("text_primary", "#0F172A"))
    return get_icon(name, color=color, size=size)
