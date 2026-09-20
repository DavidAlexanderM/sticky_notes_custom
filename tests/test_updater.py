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
    get_stored_mirror_url, save_stored_mirror_url,
    parse_release_payload, DEFAULT_PUBLIC_MANIFEST_URL,
    UpdateCheckWorker
)
from components.update_dialog import UpdateDialog
from scripts.generate_release_manifest import generate_manifest


class TestUpdater(unittest.TestCase):
    """Verifies version parsing, comparison logic, mirror feeds, and update dialog states."""

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

    def test_mirror_url_storage(self):
        default_url = get_stored_mirror_url()
        self.assertTrue(default_url.startswith("http"))

        custom_url = "https://custom-mirror.example.com/version.json"
        save_stored_mirror_url(custom_url)
        self.assertEqual(get_stored_mirror_url(), custom_url)

        # Restore default
        save_stored_mirror_url(DEFAULT_PUBLIC_MANIFEST_URL)
        self.assertEqual(get_stored_mirror_url(), DEFAULT_PUBLIC_MANIFEST_URL)

    def test_parse_release_payload_mirror(self):
        mock_manifest = {
            "version": "9.9.0",
            "tag_name": "v9.9.0",
            "published_at": "2026-09-20T18:00:00Z",
            "html_url": "https://github.com/DavidAlexanderM/sticky_notes_releases/releases/tag/v9.9.0",
            "body": "- Zero-token public mirror support\n- Automated CI/CD sync",
            "asset_name": "StickyNotes_v9.9.0_Windows.zip",
            "asset_size": 75000000,
            "browser_download_url": "https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/v9.9.0/StickyNotes_v9.9.0_Windows.zip"
        }
        res = parse_release_payload(mock_manifest, source_name="public_mirror")
        self.assertEqual(res["version"], "9.9.0")
        self.assertEqual(res["tag_name"], "v9.9.0")
        self.assertEqual(res["source"], "public_mirror")
        self.assertTrue(res["has_update"])
        self.assertEqual(res["asset_name"], "StickyNotes_v9.9.0_Windows.zip")
        self.assertEqual(res["asset_size"], 75000000)

    def test_manifest_generator_script(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_file = generate_manifest(output_dir=tmp_path, tag_name="v1.5.6")
            self.assertTrue(out_file.exists())
            import json
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["version"], "1.5.6")
            self.assertEqual(data["tag_name"], "v1.5.6")
            self.assertIn("sticky_notes_releases", data["browser_download_url"])

    def test_update_dialog_instantiation_and_settings(self):
        dialog = UpdateDialog(auto_check=False)
        self.assertIsNotNone(dialog.card)
        self.assertIsNotNone(dialog.token_settings_btn)
        self.assertIsNotNone(dialog.close_btn)
        self.assertIsNotNone(dialog.source_lbl)

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
            "browser_download_url": "https://example.com/download.zip",
            "source": "public_mirror"
        }
        dialog._show_update_available(mock_release)
        self.assertEqual(dialog.release_info["version"], "1.5.9")

        # Verify token & mirror settings card rendering
        dialog._show_token_section()
        self.assertIsNotNone(dialog.mirror_input)
        self.assertIsNotNone(dialog.token_input)

        dialog.close()


if __name__ == "__main__":
    unittest.main()
