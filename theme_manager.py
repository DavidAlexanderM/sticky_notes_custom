"""
theme_manager.py - Centralized Theme Management System for Sticky Notes.
Supports Light, Dark, and Sepia themes with persistent settings, dynamic signal dispatching,
and real-time automatic synchronization with the Windows OS theme.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer, QCoreApplication, QAbstractNativeEventFilter


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


class _WindowsThemeEventFilter(QAbstractNativeEventFilter):
    """Listens for WM_SETTINGCHANGE (0x001A) on Windows to detect instant OS theme changes."""
    def __init__(self, theme_manager: 'ThemeManager'):
        super().__init__()
        self.theme_mgr = theme_manager

    def nativeEventFilter(self, eventType, message):
        if eventType in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            try:
                import ctypes
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                # 0x001A = WM_SETTINGCHANGE
                if msg.message == 0x001A:
                    self.theme_mgr.check_os_theme_change()
            except Exception:
                pass
        return False, 0


class ThemeManager(QObject):
    """
    Manages application theme state, stylesheet generation, persistent preferences,
    and real-time automatic synchronization with the host operating system.
    """
    theme_changed = Signal(str)  # Emits effective theme name ('light', 'dark', 'sepia')

    SUPPORTED_THEMES = ["light", "dark", "sepia", "system"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preferred_theme = "system"
        self._last_detected_os_theme = detect_os_theme()
        self._current_theme = self._last_detected_os_theme
        self._load_preferences()

        # Infallible 1.5s background polling fallback for headless / registry changes
        self._os_monitor_timer = QTimer(self)
        self._os_monitor_timer.setInterval(1500)
        self._os_monitor_timer.timeout.connect(self.check_os_theme_change)
        self._os_monitor_timer.start()

        self._native_filter: Optional[_WindowsThemeEventFilter] = None
        self._install_native_listener()

    def _install_native_listener(self):
        """Attaches native event filter to QCoreApplication if running on Windows."""
        if sys.platform == "win32":
            app = QCoreApplication.instance()
            if app and not self._native_filter:
                try:
                    self._native_filter = _WindowsThemeEventFilter(self)
                    app.installNativeEventFilter(self._native_filter)
                except Exception:
                    pass

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

    def check_os_theme_change(self):
        """Checks if the operating system theme has changed and notifies subscribers."""
        detected = detect_os_theme()
        if detected != self._last_detected_os_theme:
            self._last_detected_os_theme = detected
            if self._preferred_theme == "system":
                self._current_theme = detected
                self.theme_changed.emit(self.current_theme)

    @property
    def current_theme(self) -> str:
        """Returns the active rendered theme ('light', 'dark', 'sepia')."""
        if self._preferred_theme == "system":
            return self._last_detected_os_theme
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
        """
        Cycles theme state: System (Auto) -> Dark -> Light -> System (Auto).
        Returns the new effective rendered theme name.
        """
        if self._preferred_theme == "system":
            new_pref = "light" if self.is_dark_mode() else "dark"
        elif self._preferred_theme == "dark":
            new_pref = "light"
        elif self._preferred_theme == "light":
            new_pref = "system"
        else:
            new_pref = "system"

        self.set_theme(new_pref)
        return self.current_theme

    def get_app_stylesheet(self) -> str:
        """Generates full QSS for the current active theme."""
        try:
            from styles import generate_app_stylesheet
            return generate_app_stylesheet(self.current_theme)
        except ImportError:
            from .styles import generate_app_stylesheet
            return generate_app_stylesheet(self.current_theme)

    def get_markdown_css(self) -> str:
        """Generates Markdown preview CSS matching the active theme."""
        try:
            from styles import get_markdown_preview_css
            return get_markdown_preview_css(self.current_theme)
        except ImportError:
            from .styles import get_markdown_preview_css
            return get_markdown_preview_css(self.current_theme)


# Global singleton instance
_GLOBAL_THEME_MANAGER: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Returns the shared ThemeManager singleton instance."""
    global _GLOBAL_THEME_MANAGER
    if _GLOBAL_THEME_MANAGER is None:
        _GLOBAL_THEME_MANAGER = ThemeManager()
    return _GLOBAL_THEME_MANAGER
