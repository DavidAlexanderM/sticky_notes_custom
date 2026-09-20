"""
theme_manager.py - Centralized Theme Management System for Sticky Notes.
Supports Light, Dark, and Sepia themes with persistent settings and dynamic signal dispatching.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal


def get_preferences_path() -> Path:
    """Returns the persistent path for storing user preferences."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
    else:
        base_dir = Path(__file__).resolve().parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "preferences.json"


def detect_os_theme() -> str:
    """Detects whether the operating system is currently in Dark or Light mode."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if val == 1 else "dark"
        except Exception:
            pass
    return "light"


class ThemeManager(QObject):
    """
    Manages application theme state, stylesheet generation, and persistent preferences.
    Supports system OS detection, Light, Dark, and Sepia themes.
    """
    theme_changed = Signal(str)  # Emits effective theme name ('light', 'dark', 'sepia')

    SUPPORTED_THEMES = ["light", "dark", "sepia", "system"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preferred_theme = "system"
        self._current_theme = detect_os_theme()
        self._load_preferences()

    def _load_preferences(self):
        """Loads saved theme preference from disk."""
        pref_file = get_preferences_path()
        if pref_file.exists():
            try:
                with open(pref_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    theme = data.get("theme", "system")
                    if theme in self.SUPPORTED_THEMES:
                        self._preferred_theme = theme
                        self._current_theme = detect_os_theme() if theme == "system" else theme
            except Exception:
                self._preferred_theme = "system"
                self._current_theme = detect_os_theme()

    def _save_preferences(self):
        """Persists current theme preference to disk."""
        pref_file = get_preferences_path()
        try:
            with open(pref_file, "w", encoding="utf-8") as f:
                json.dump({"theme": self._preferred_theme}, f, indent=2)
        except Exception:
            pass

    @property
    def current_theme(self) -> str:
        """Returns the active rendered theme ('light', 'dark', 'sepia')."""
        if self._preferred_theme == "system":
            return detect_os_theme()
        return self._current_theme

    @property
    def preferred_theme(self) -> str:
        """Returns the configured preference ('system', 'light', 'dark', 'sepia')."""
        return self._preferred_theme

    def is_dark_mode(self) -> bool:
        return self.current_theme == "dark"

    def is_system_theme(self) -> bool:
        return self._preferred_theme == "system"

    def set_theme(self, theme_name: str):
        """Sets active theme and notifies all subscribers."""
        clean_theme = theme_name.lower().strip()
        if clean_theme not in self.SUPPORTED_THEMES:
            clean_theme = "system"

        old_rendered = self.current_theme
        self._preferred_theme = clean_theme
        self._current_theme = detect_os_theme() if clean_theme == "system" else clean_theme
        self._save_preferences()

        if self.current_theme != old_rendered or clean_theme == "system":
            self.theme_changed.emit(self.current_theme)

    def toggle_theme(self) -> str:
        """Toggles between light and dark themes and returns new effective theme name."""
        new_theme = "light" if self.is_dark_mode() else "dark"
        self.set_theme(new_theme)
        return new_theme

    def get_app_stylesheet(self) -> str:
        """Generates full QSS for the current active theme."""
        try:
            from styles import generate_app_stylesheet
            return generate_app_stylesheet(self._current_theme)
        except ImportError:
            from .styles import generate_app_stylesheet
            return generate_app_stylesheet(self._current_theme)

    def get_markdown_css(self) -> str:
        """Generates Markdown preview CSS matching the active theme."""
        try:
            from styles import get_markdown_preview_css
            return get_markdown_preview_css(self._current_theme)
        except ImportError:
            from .styles import get_markdown_preview_css
            return get_markdown_preview_css(self._current_theme)


# Global singleton instance
_GLOBAL_THEME_MANAGER: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Returns the shared ThemeManager singleton instance."""
    global _GLOBAL_THEME_MANAGER
    if _GLOBAL_THEME_MANAGER is None:
        _GLOBAL_THEME_MANAGER = ThemeManager()
    return _GLOBAL_THEME_MANAGER
