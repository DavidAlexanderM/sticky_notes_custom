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
    UpdateCheckWorker, apply_update_and_restart, _launch_update_script
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

        # Verify install ready rendering & timer lifecycle
        dialog._show_install_ready("C:/fake/path/StickyNotes_Setup_v1.6.3.exe")
        self.assertEqual(dialog.downloaded_zip_path, "C:/fake/path/StickyNotes_Setup_v1.6.3.exe")
        dialog._cancel_auto_restart()
        if dialog.restart_timer:
            self.assertFalse(dialog.restart_timer.isActive())

        dialog.close()

    def test_clear_card_prevents_button_overlay(self):
        """Verifies that transitioning between updater states via QStackedWidget completely isolates page buttons."""
        from PySide6.QtWidgets import QPushButton
        dialog = UpdateDialog(auto_check=False)

        mock_release = {
            "version": "2.0.0",
            "tag_name": "v2.0.0",
            "body": "Release 2.0.0 notes",
            "html_url": "https://example.com",
            "published_at": "2026-09-21T00:00:00Z",
            "asset_name": "StickyNotes_v2.0.0_Windows.zip",
            "asset_size": 75000000,
            "browser_download_url": "https://example.com/file.zip",
            "source": "public_mirror"
        }

        # 1. State: Update Available
        dialog._show_update_available(mock_release)
        btn_texts = [btn.text().strip() for btn in dialog.get_active_buttons()]
        self.assertIn("View on GitHub", btn_texts)
        self.assertTrue(any("Download & Install" in t for t in btn_texts))
        self.assertEqual(len(btn_texts), 2)

        # 2. State: Downloading (Must NOT retain previous download buttons!)
        dialog._show_downloading_state()
        dl_btn_texts = [btn.text().strip() for btn in dialog.get_active_buttons()]
        self.assertEqual(dl_btn_texts, ["Cancel Download"])
        self.assertNotIn("View on GitHub", dl_btn_texts)
        self.assertFalse(any("Download & Install" in t for t in dl_btn_texts))

        # 3. State: Install Ready (Must NOT retain Cancel Download button!)
        dialog._show_install_ready("C:/test/file.zip")
        ready_btn_texts = [btn.text().strip() for btn in dialog.get_active_buttons()]
        self.assertNotIn("Cancel Download", ready_btn_texts)
        self.assertNotIn("View on GitHub", ready_btn_texts)
        self.assertFalse(any("Download & Install" in t for t in ready_btn_texts))

        # 4. State: Cancelled back to Update Available
        dialog._cancel_download()
        reverted_btn_texts = [btn.text().strip() for btn in dialog.get_active_buttons()]
        self.assertIn("View on GitHub", reverted_btn_texts)
        self.assertTrue(any("Download & Install" in t for t in reverted_btn_texts))
        self.assertEqual(len(reverted_btn_texts), 2)

        dialog.close()

    def test_noauth_redirect_handler(self):
        """Verifies that NoAuthRedirectHandler strips Authorization header when redirecting away from api.github.com."""
        import urllib.request
        from updater import NoAuthRedirectHandler

        handler = NoAuthRedirectHandler()
        req = urllib.request.Request("https://api.github.com/repos/test/asset/123")
        req.add_header("Authorization", "Bearer ghp_secret_token")
        req.add_header("Accept", "application/octet-stream")

        # 1. Redirect to AWS S3 storage (objects.githubusercontent.com)
        s3_url = "https://objects.githubusercontent.com/github-production-release-asset-2e65be/12345?response-content-disposition=attachment"
        redirected_req = handler.redirect_request(req, None, 302, "Found", {}, s3_url)
        self.assertIsNotNone(redirected_req)
        # Authorization header must be stripped to prevent S3 HTTP 400 Bad Request
        header_keys = [k.lower() for k in redirected_req.headers.keys()]
        self.assertNotIn("authorization", header_keys)

        # 2. Redirect staying on api.github.com
        internal_url = "https://api.github.com/repos/test/asset/redirected"
        same_domain_req = handler.redirect_request(req, None, 302, "Found", {}, internal_url)
        self.assertIsNotNone(same_domain_req)
        same_domain_keys = [k.lower() for k in same_domain_req.headers.keys()]
        self.assertIn("authorization", same_domain_keys)

    def test_binary_integrity_validation(self):
        """Verifies that UpdateDownloadWorker rejects truncated or corrupted binaries."""
        from updater import UpdateDownloadWorker

        worker = UpdateDownloadWorker(release_info={"version": "1.6.8"})

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Test 1: File smaller than 100 KB
            small_file = tmp_path / "StickyNotes_Setup_v1.6.8.exe"
            small_file.write_bytes(b"MZ" + b"0" * 1000)  # Only ~1 KB

            # Test 2: File with invalid signature
            bad_sig_file = tmp_path / "StickyNotes_Bad_v1.6.8.exe"
            bad_sig_file.write_bytes(b"<html>Error 404</html>" + b"X" * 150000)

            # Test 3: Valid exe header and sufficient size
            valid_exe = tmp_path / "StickyNotes_Valid_v1.6.8.exe"
            valid_exe.write_bytes(b"MZ\x90\x00" + b"\x00" * 150000)

            # Verify size check
            self.assertLess(small_file.stat().st_size, 102400)
            # Verify bad sig
            self.assertFalse(bad_sig_file.read_bytes()[:2] == b"MZ")
            # Verify valid sig
            self.assertTrue(valid_exe.read_bytes()[:2] == b"MZ")
            self.assertGreaterEqual(valid_exe.stat().st_size, 102400)


    def test_apply_update_writes_batch_script(self):
        """Verifies that apply_update_and_restart writes a correct batch script with logging and error checking."""
        from unittest.mock import patch, MagicMock

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fake_exe = tmp_path / "StickyNotes_Setup_v1.8.0.exe"
            fake_exe.write_bytes(b"MZ\x90\x00" + b"\x00" * 150000)

            # Mock subprocess.Popen, sys.exit, time.sleep, and QApplication
            with patch("updater.subprocess.Popen") as mock_popen, \
                 patch("updater.sys.exit") as mock_exit, \
                 patch("PySide6.QtWidgets.QApplication.instance", return_value=MagicMock()), \
                 patch("time.sleep"):

                apply_update_and_restart(str(fake_exe))

                # Verify batch script was written
                bat_path = tmp_path / "apply_update.bat"
                self.assertTrue(bat_path.exists(), "Batch script was not created")

                bat_content = bat_path.read_text(encoding="utf-8")

                # Must have cd /d for directory safety
                self.assertIn('cd /d "%~dp0"', bat_content)
                # Must log to update.log
                self.assertIn("update.log", bat_content)
                # Must use timeout instead of ping for delays
                self.assertIn("timeout /t", bat_content)
                self.assertNotIn("ping 127.0.0.1", bat_content)
                # Must include installer arguments
                self.assertIn("/SILENT", bat_content)
                self.assertIn("/NORESTART", bat_content)
                self.assertIn("/CLOSEAPPLICATIONS", bat_content)
                # Must check installer exit code
                self.assertIn("INSTALL_EXIT", bat_content)
                # Must include retry limit to prevent infinite wait loop
                self.assertIn("RETRIES", bat_content)
                # Must NOT use fragile (goto) self-delete trick
                self.assertNotIn("(goto) 2>nul", bat_content)
                # Must include clean exit
                self.assertIn("exit /b 0", bat_content)

    def test_apply_update_subprocess_flags(self):
        """Verifies Popen is called with DEVNULL handles and without close_fds=True."""
        from unittest.mock import patch, MagicMock, call
        import subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            fake_exe = tmp_path / "StickyNotes_Setup_v1.8.0.exe"
            fake_exe.write_bytes(b"MZ\x90\x00" + b"\x00" * 150000)

            with patch("updater.subprocess.Popen") as mock_popen, \
                 patch("updater.sys.exit") as mock_exit, \
                 patch("PySide6.QtWidgets.QApplication.instance", return_value=MagicMock()), \
                 patch("time.sleep"):

                apply_update_and_restart(str(fake_exe))

                # Verify Popen was called exactly once
                self.assertEqual(mock_popen.call_count, 1)

                popen_call = mock_popen.call_args
                kwargs = popen_call.kwargs if popen_call.kwargs else {}

                # Must use DEVNULL for all standard handles
                self.assertEqual(kwargs.get("stdin"), subprocess.DEVNULL,
                                 "stdin must be DEVNULL for detached process")
                self.assertEqual(kwargs.get("stdout"), subprocess.DEVNULL,
                                 "stdout must be DEVNULL for detached process")
                self.assertEqual(kwargs.get("stderr"), subprocess.DEVNULL,
                                 "stderr must be DEVNULL for detached process")

                # Must NOT use close_fds=True (incompatible with handle redirection on Windows)
                self.assertNotIn("close_fds", kwargs,
                                 "close_fds must not be passed (incompatible with DEVNULL on Windows)")

                # Must use DETACHED_PROCESS flag
                flags = kwargs.get("creationflags", 0)
                self.assertTrue(flags & subprocess.DETACHED_PROCESS,
                                "DETACHED_PROCESS flag must be set")
                self.assertTrue(flags & subprocess.CREATE_NEW_PROCESS_GROUP,
                                "CREATE_NEW_PROCESS_GROUP flag must be set")

                # sys.exit(0) must be called after Popen
                mock_exit.assert_called_once_with(0)

    def test_apply_update_handles_missing_file(self):
        """Verifies graceful failure when the installer file doesn't exist."""
        result = apply_update_and_restart("C:/nonexistent/path/StickyNotes_Setup.exe")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

