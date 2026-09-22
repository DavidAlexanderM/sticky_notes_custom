"""
test_share_dialog.py - Automated test suite for the OS-Level Sharing Integration.
Verifies Windows native share hooks, direct desktop application protocols (WhatsApp, Telegram,
SMS, Mail, Teams), draggable note chip MIME generation, and media packaging.
"""

import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl

# Ensure QApplication exists for GUI component testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

from components.share_dialog import (
    ShareNoteDialog, strip_markdown, extract_media_attachments,
    stage_share_files, invoke_windows_share_ui, invoke_windows_open_with,
    DraggableNoteChip
)


class TestShareDialog(unittest.TestCase):
    """Verifies OS-level sharing integration and desktop protocol handling."""

    def test_strip_markdown(self):
        sample = "# Heading\n\n**Bold** and *Italic* and `code` with ~~strike~~.\n> Quote\n[Web Link](https://google.com)\n![Photo](file:///C:/test.png)"
        cleaned = strip_markdown(sample)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("~~", cleaned)
        self.assertNotIn("file:///", cleaned)
        self.assertIn("Bold", cleaned)
        self.assertIn("https://google.com", cleaned)
        self.assertIn("[Photo]", cleaned)

    def test_stage_share_files(self):
        title = "Sprint Planning 2026"
        content = "Task 1: Complete testing\nTask 2: Release v1.7.0"
        staged = stage_share_files(title, content)
        self.assertTrue(staged.exists())
        text = staged.read_text(encoding="utf-8")
        self.assertIn("Sprint Planning", text)
        self.assertIn("Release v1.7.0", text)

    def test_dialog_buttons_and_os_controls(self):
        dialog = ShareNoteDialog("Executive Brief", "Key takeaways for Q3")
        # OS Native buttons
        self.assertIsNotNone(dialog.btn_win_share)
        self.assertIsNotNone(dialog.btn_open_with)
        self.assertIsNotNone(dialog.btn_sms)
        self.assertIsNotNone(dialog.btn_open_folder)
        self.assertIsNotNone(dialog.drag_chip)

        # Direct desktop app buttons
        self.assertIsNotNone(dialog.btn_whatsapp)
        self.assertIsNotNone(dialog.btn_telegram)
        self.assertIsNotNone(dialog.btn_mail)
        self.assertIsNotNone(dialog.btn_teams)
        self.assertIsNotNone(dialog.btn_facebook)
        self.assertIsNotNone(dialog.btn_x)

        # Document export & clipboard buttons
        self.assertIsNotNone(dialog.btn_copy_rich)
        self.assertIsNotNone(dialog.btn_copy_txt)
        self.assertIsNotNone(dialog.btn_copy_md)
        self.assertIsNotNone(dialog.btn_save_md)
        self.assertIsNotNone(dialog.btn_save_html)

        dialog.close()

    def test_draggable_chip_mime_data(self):
        dialog = ShareNoteDialog("Drag Test", "Drag this note into WhatsApp or Explorer")
        mime = dialog._get_drag_mime_data()
        self.assertIsNotNone(mime)
        self.assertTrue(mime.hasText())
        self.assertIn("Drag Test", mime.text())
        self.assertTrue(mime.hasHtml())
        self.assertTrue(mime.hasUrls())
        self.assertTrue(len(mime.urls()) >= 1)
        dialog.close()

    def test_whatsapp_native_protocol_dispatch(self):
        dialog = ShareNoteDialog("Secret Memo", "Confidential meeting details")
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            mock_open.return_value = True
            dialog._share_via_whatsapp()
            self.assertTrue(mock_open.called)
            called_url = mock_open.call_args[0][0].toString()
            self.assertTrue(called_url.startswith("whatsapp://send?text="))
            self.assertIn("Secret", called_url)
        dialog.close()

    def test_telegram_native_protocol_dispatch(self):
        dialog = ShareNoteDialog("Announcement", "Launch date confirmed")
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            mock_open.return_value = True
            dialog._share_via_telegram()
            self.assertTrue(mock_open.called)
            called_url = mock_open.call_args[0][0].toString()
            self.assertTrue(called_url.startswith("tg://msg?text="))
            self.assertIn("Announcement", called_url)
        dialog.close()

    def test_sms_native_protocol_dispatch(self):
        dialog = ShareNoteDialog("Quick Ping", "See you at 3pm")
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            mock_open.return_value = True
            dialog._share_via_sms()
            self.assertTrue(mock_open.called)
            called_url = mock_open.call_args[0][0].toString()
            self.assertTrue(called_url.startswith("sms:?body="))
        dialog.close()

    def test_teams_native_protocol_dispatch(self):
        dialog = ShareNoteDialog("Team Sync", "Review the presentation")
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            mock_open.return_value = True
            dialog._share_via_teams()
            self.assertTrue(mock_open.called)
            called_url = mock_open.call_args[0][0].toString()
            self.assertTrue(called_url.startswith("msteams:/l/chat/0/0?users=&message="))
        dialog.close()

    def test_windows_share_ui_verb_execution(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            tf.write(b"Windows OS Share Test")
            temp_path = Path(tf.name)

        try:
            # invoke_windows_share_ui should execute cleanly on Windows
            # and return boolean without throwing unhandled exceptions
            res = invoke_windows_share_ui(temp_path)
            self.assertIsInstance(res, bool)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_rich_clipboard_copy(self):
        dialog = ShareNoteDialog("Rich Note", "### Section 1\n- Item A\n- Item B")
        with patch.object(QApplication.clipboard(), "setMimeData") as mock_set:
            dialog._copy_rich_text()
            self.assertTrue(mock_set.called)
            passed_mime = mock_set.call_args[0][0]
            self.assertTrue(passed_mime.hasText())
            self.assertTrue(passed_mime.hasHtml())
            self.assertIn("Item A", passed_mime.text())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
