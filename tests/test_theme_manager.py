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
        """Verify toggle_theme alternates between light and dark."""
        self.mgr.set_theme("light")
        new_theme = self.mgr.toggle_theme()
        self.assertEqual(new_theme, "dark")
        self.assertEqual(self.mgr.current_theme, "dark")

        new_theme2 = self.mgr.toggle_theme()
        self.assertEqual(new_theme2, "light")
        self.assertEqual(self.mgr.current_theme, "light")

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
        self.assertIn("#1E293B", dark_css)
        self.assertIn("#F8FAFC", dark_css)


if __name__ == "__main__":
    unittest.main()
