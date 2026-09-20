import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import database
from security import (
    is_safe_attachment, is_safe_url, sanitize_filename, 
    sanitize_markdown_html, DANGEROUS_EXTENSIONS
)
from media_manager import copy_to_attachments, get_attachments_dir


class TestApplicationSecurity(unittest.TestCase):
    """
    Automated security test suite covering path traversal, dangerous extension rejection,
    URL scheme sanitization, HTML/script neutralization, and SQL injection prevention.
    """

    def setUp(self):
        database.init_db()
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    # --- 1. Path Traversal & Filename Sanitization ---

    def test_sanitize_filename_strips_traversal(self):
        """Verify sanitize_filename strips path traversal characters and directory separators."""
        unsafe_stem = "../../Windows/System32/cmd"
        safe_name = sanitize_filename(unsafe_stem, ".txt")
        self.assertNotIn("/", safe_name)
        self.assertNotIn("\\", safe_name)
        self.assertNotIn("..", safe_name)
        self.assertTrue(safe_name.endswith(".txt"))

    def test_copy_to_attachments_contained_in_dir(self):
        """Verify copy_to_attachments strictly confines copied files within attachments dir."""
        sample_file = self.test_path / "valid_image.png"
        sample_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        copied_path = copy_to_attachments(str(sample_file))
        self.assertTrue(copied_path.exists())
        self.assertTrue(copied_path.resolve().is_relative_to(get_attachments_dir().resolve()))

        # Clean up copied attachment
        if copied_path.exists():
            copied_path.unlink()

    # --- 2. Dangerous Extension Rejection ---

    def test_dangerous_extensions_blocked(self):
        """Verify executable, script, and installer files are rejected from attachment."""
        test_extensions = [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".sh", ".msi", ".scr"]
        for ext in test_extensions:
            fake_file = self.test_path / f"malicious{ext}"
            fake_file.write_text("evil payload", encoding="utf-8")
            
            is_safe, msg = is_safe_attachment(fake_file)
            self.assertFalse(is_safe, f"Extension {ext} should have been marked unsafe")
            self.assertIn("prohibited", msg.lower())

            with self.assertRaises(ValueError):
                copy_to_attachments(str(fake_file))

    def test_double_extension_blocked(self):
        """Verify disguised double extensions like 'invoice.pdf.exe' are detected and blocked."""
        fake_file = self.test_path / "invoice.pdf.exe"
        fake_file.write_text("evil payload", encoding="utf-8")

        is_safe, msg = is_safe_attachment(fake_file)
        self.assertFalse(is_safe)
        self.assertIn("prohibited", msg.lower())

    # --- 3. URL Scheme & Link Sanitization ---

    def test_safe_web_urls_allowed(self):
        """Verify http, https, and mailto protocols are allowed."""
        safe_urls = [
            "https://github.com/DavidAlexanderM/sticky_notes_app",
            "http://example.com/docs",
            "mailto:developer@example.com"
        ]
        for url in safe_urls:
            is_safe, _ = is_safe_url(url)
            self.assertTrue(is_safe, f"URL should be allowed: {url}")

    def test_dangerous_schemes_blocked(self):
        """Verify javascript, file traversal, and system launcher schemes are blocked."""
        dangerous_urls = [
            "javascript:alert('XSS')",
            "shell:startup",
            "file:///C:/Windows/System32/cmd.exe",
            "powershell:Start-Process calc",
            "ms-msdt:/id PCWDiagnostic"
        ]
        for url in dangerous_urls:
            is_safe, reason = is_safe_url(url, allowed_attachments_dir=get_attachments_dir())
            self.assertFalse(is_safe, f"URL should be blocked: {url}")
            self.assertIn("Blocked", reason)

    def test_internal_attachment_url_allowed(self):
        """Verify local file:// URLs strictly inside attachments folder are allowed."""
        attachments_dir = get_attachments_dir()
        valid_local = attachments_dir / "sample_audio.m4a"
        valid_local.write_bytes(b"dummy audio")

        file_url = valid_local.as_uri()
        is_safe, _ = is_safe_url(file_url, allowed_attachments_dir=attachments_dir)
        self.assertTrue(is_safe, f"Attachment URL should be allowed: {file_url}")

        valid_local.unlink()

    # --- 4. Markdown HTML Sanitization ---

    def test_script_tag_stripped(self):
        """Verify <script> tags and payloads are completely stripped."""
        payload = "<p>Normal</p><script>alert('PWNED')</script><b>Bold</b>"
        clean = sanitize_markdown_html(payload)
        self.assertNotIn("<script", clean)
        self.assertNotIn("alert", clean)
        self.assertIn("<p>Normal</p>", clean)
        self.assertIn("<b>Bold</b>", clean)

    def test_dangerous_elements_stripped(self):
        """Verify iframes, embeds, and objects are stripped."""
        payload = '<iframe src="https://attacker.com"></iframe><embed src="flash.swf">'
        clean = sanitize_markdown_html(payload)
        self.assertNotIn("<iframe", clean)
        self.assertNotIn("<embed", clean)

    def test_inline_event_handlers_stripped(self):
        """Verify onerror, onload, and onclick handlers are removed."""
        payload = '<img src="invalid.jpg" onerror="alert(1)">'
        clean = sanitize_markdown_html(payload)
        self.assertNotIn("onerror", clean)
        self.assertNotIn("alert(1)", clean)

    # --- 5. SQL Injection Prevention ---

    def test_sql_injection_payloads_safely_handled(self):
        """Verify SQL injection payloads in title, content, or id do not corrupt SQLite database."""
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE notes; --",
            "admin'--",
            "UNION SELECT 1, 2, 3, 4, 5, 6--"
        ]

        for payload in sqli_payloads:
            # Test note creation with SQL injection payload
            note_id = database.create_note(title=payload, content=payload)
            self.assertIsNotNone(note_id)

            # Retrieve note
            note = database.get_note(note_id)
            self.assertIsNotNone(note)
            self.assertEqual(note["title"], payload)
            self.assertEqual(note["content"], payload)

            # Update note with payload
            database.update_note(note_id, title=f"Updated {payload}")
            updated = database.get_note(note_id)
            self.assertEqual(updated["title"], f"Updated {payload}")

            # Verify table still exists and schema is intact
            all_notes = database.get_all_notes()
            self.assertIsInstance(all_notes, list)

            # Clean up
            database.delete_note(note_id)


if __name__ == "__main__":
    unittest.main()
