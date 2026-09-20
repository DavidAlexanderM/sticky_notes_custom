import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_manager import ThemeManager, get_theme_manager
from styles import generate_app_stylesheet, get_markdown_preview_css, THEME_PALETTES


class TestThemeManager(unittest.TestCase):
    """
    Automated test suite verifying the ThemeManager subsystem,
    stylesheet generators, persistence, and signal dispatching.
    """

    def setUp(self):
        self.mgr = ThemeManager()
        self.mgr.set_theme("light")

    def test_supported_themes(self):
        """Verify supported themes are light, dark, sepia."""
        self.assertIn("light", self.mgr.SUPPORTED_THEMES)
        self.assertIn("dark", self.mgr.SUPPORTED_THEMES)
        self.assertIn("sepia", self.mgr.SUPPORTED_THEMES)

    def test_set_theme_and_signal(self):
        """Verify set_theme switches state and emits signal."""
        emitted = []
        self.mgr.theme_changed.connect(lambda t: emitted.append(t))

        self.mgr.set_theme("dark")
        self.assertEqual(self.mgr.current_theme, "dark")
        self.assertTrue(self.mgr.is_dark_mode())
        self.assertIn("dark", emitted)

        # Reset to light
        self.mgr.set_theme("light")
        self.assertEqual(self.mgr.current_theme, "light")
        self.assertFalse(self.mgr.is_dark_mode())
        self.assertIn("light", emitted)

    def test_toggle_theme(self):
        """Verify toggle_theme cycles through dark, light, and system."""
        self.mgr.set_theme("dark")
        new_theme = self.mgr.toggle_theme()
        self.assertEqual(new_theme, "light")

        # From light, toggle returns to system (auto)
        new_theme2 = self.mgr.toggle_theme()
        self.assertTrue(self.mgr.is_system_theme())

    def test_realtime_os_theme_detection(self):
        """Verify check_os_theme_change emits theme_changed when OS switches."""
        emitted = []
        self.mgr.set_theme("system")
        self.mgr.theme_changed.connect(lambda t: emitted.append(t))

        # Simulate OS theme switch
        self.mgr._last_detected_os_theme = "light"
        import theme_manager
        orig_detect = theme_manager.detect_os_theme
        try:
            theme_manager.detect_os_theme = lambda: "dark"
            self.mgr.check_os_theme_change()
            self.assertEqual(self.mgr.current_theme, "dark")
            self.assertIn("dark", emitted)
        finally:
            theme_manager.detect_os_theme = orig_detect

    def test_stylesheet_generation(self):
        """Verify QSS stylesheets are generated for each theme."""
        for theme in ["light", "dark", "sepia"]:
            qss = generate_app_stylesheet(theme)
            self.assertIsInstance(qss, str)
            self.assertIn("QMainWindow", qss)
            self.assertIn("SearchInput", qss)
            self.assertIn("ThemeToggleBtn", qss)
            self.assertIn("FilterPill", qss)

    def test_markdown_css_generation(self):
        """Verify Markdown preview CSS adjusts background and text for dark/light."""
        light_css = get_markdown_preview_css("light")
        self.assertIn("#FFFFFF", light_css)

        dark_css = get_markdown_preview_css("dark")
        self.assertIn("#1E1F20", dark_css)
        self.assertIn("#E3E3E3", dark_css)


if __name__ == "__main__":
    unittest.main()
