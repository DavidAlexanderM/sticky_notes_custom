"""
test_updater.py - Automated test suite for the Auto-Update subsystem.
Verifies semantic version comparison, GitHub token persistence,
and UpdateDialog component lifecycle.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QLabel

# Ensure QApplication exists for GUI component testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

from updater import (
    parse_version_tuple, is_newer_version,
    get_stored_github_token, save_stored_github_token,
    UpdateCheckWorker
)
from components.update_dialog import UpdateDialog


class TestUpdater(unittest.TestCase):
    """Verifies version parsing, comparison logic, and update dialog states."""

    def test_version_tuple_parsing(self):
        self.assertEqual(parse_version_tuple("1.5.4"), (1, 5, 4))
        self.assertEqual(parse_version_tuple("v1.5.4"), (1, 5, 4))
        self.assertEqual(parse_version_tuple("V2.0.1"), (2, 0, 1))
        self.assertEqual(parse_version_tuple("1.5"), (1, 5, 0))
        self.assertEqual(parse_version_tuple("v1.5.5-alpha"), (1, 5, 5))

    def test_version_comparison(self):
        # Strictly newer
        self.assertTrue(is_newer_version("1.5.5", "1.5.4"))
        self.assertTrue(is_newer_version("v1.6.0", "1.5.4"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertTrue(is_newer_version("1.5.4.1", "1.5.4"))

        # Same or older
        self.assertFalse(is_newer_version("1.5.4", "1.5.4"))
        self.assertFalse(is_newer_version("v1.5.4", "1.5.4"))
        self.assertFalse(is_newer_version("1.5.3", "1.5.4"))
        self.assertFalse(is_newer_version("1.4.99", "1.5.4"))

    def test_token_storage(self):
        # Save dummy test token
        test_token = "ghp_test_token_12345"
        save_stored_github_token(test_token)
        loaded = get_stored_github_token()
        self.assertEqual(loaded, test_token)

        # Clear token
        save_stored_github_token("")
        self.assertIsNone(get_stored_github_token())

    def test_update_dialog_instantiation(self):
        dialog = UpdateDialog(auto_check=False)
        self.assertIsNotNone(dialog.card)
        self.assertIsNotNone(dialog.token_settings_btn)
        self.assertIsNotNone(dialog.close_btn)

        # Verify up to date view rendering
        dialog._show_up_to_date()
        labels = [lbl.text() for lbl in dialog.card.findChildren(QLabel)]
        self.assertTrue(any("latest version" in t for t in labels))

        # Verify update available view rendering
        mock_release = {
            "version": "1.5.9",
            "tag_name": "v1.5.9",
            "body": "### Changes\n- Cool new feature\n- Bug fix",
            "html_url": "https://github.com/DavidAlexanderM/sticky_notes_app/releases/tag/v1.5.9",
            "published_at": "2026-09-20T12:00:00Z",
            "asset_name": "StickyNotes_v1.5.9_Windows.zip",
            "asset_size": 74000000,
            "browser_download_url": "https://example.com/download.zip"
        }
        dialog._show_update_available(mock_release)
        self.assertEqual(dialog.release_info["version"], "1.5.9")

        dialog.close()


if __name__ == "__main__":
    unittest.main()
