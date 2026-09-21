"""
test_proofing.py - Automated test suite for the Live Spell Checking & Proofing subsystem.
Verifies ProofingEngine, bilingual spell checking (EN/ES), markdown tokenization,
user dictionary persistence in SQLite, session-ignore, and highlighter integration.
"""

import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QTextEdit
from PySide6.QtGui import QTextDocument, QTextCharFormat

app = QApplication.instance()
if app is None:
    app = QApplication([])

import database
import i18n
from proofing_engine import ProofingEngine, get_proofing_engine
from markdown_highlighter import MarkdownHighlighter
from components.format_toolbar import FormatToolbar


class TestProofing(unittest.TestCase):
    """Test suite for the live proofing and spell checking engine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)
        self.orig_get_db_path = database.get_db_path
        self.orig_get_pref_path = database.get_preferences_path

        temp_db = self.temp_dir_path / "test_notes.db"
        temp_pref = self.temp_dir_path / "test_pref.json"
        database.get_db_path = lambda: temp_db
        database.get_preferences_path = lambda: temp_pref
        database.init_db()

        self.engine = ProofingEngine.get_instance()
        self.engine.set_enabled(True)
        self.engine.set_language("en")
        self.engine._session_ignored.clear()
        self.engine._load_user_dictionary()

    def tearDown(self):
        database.get_db_path = self.orig_get_db_path
        database.get_preferences_path = self.orig_get_pref_path
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_engine_availability(self):
        self.assertTrue(self.engine.is_available)
        self.assertTrue(self.engine.is_enabled)
        self.assertEqual(self.engine.current_language, "en")

    def test_english_spellchecking(self):
        self.engine.set_language("en")
        self.assertTrue(self.engine.is_misspelled("wrld"))
        self.assertTrue(self.engine.is_misspelled("anotehr"))
        self.assertFalse(self.engine.is_misspelled("world"))
        self.assertFalse(self.engine.is_misspelled("another"))
        self.assertFalse(self.engine.is_misspelled("Sticky"))

        # Suggestions
        suggs = self.engine.get_suggestions("wrld", max_candidates=5)
        self.assertIn("world", [s.lower() for s in suggs])

    def test_spanish_spellchecking(self):
        self.engine.set_language("es")
        self.assertEqual(self.engine.current_language, "es")

        self.assertTrue(self.engine.is_misspelled("munod"))
        self.assertTrue(self.engine.is_misspelled("hoal"))
        self.assertFalse(self.engine.is_misspelled("mundo"))
        self.assertFalse(self.engine.is_misspelled("hola"))
        self.assertFalse(self.engine.is_misspelled("médico"))

        # Suggestions
        suggs = self.engine.get_suggestions("munod", max_candidates=5)
        self.assertIn("mundo", [s.lower() for s in suggs])

    def test_markdown_line_tokenization(self):
        self.engine.set_language("en")
        # Line containing URLs, inline code, links, markdown checkboxes
        line = "Here is a [Google](https://google.com) link, `code_var`, and an email test@example.com with typo wrld"
        tokens = self.engine.tokenize_line(line)
        extracted_words = [t[0] for t in tokens]

        # Valid words and typo must be extracted
        self.assertIn("Here", extracted_words)
        self.assertIn("link", extracted_words)
        self.assertIn("wrld", extracted_words)

        # Code block, URL, email parts must NOT be extracted as checkable words
        self.assertNotIn("code_var", extracted_words)
        self.assertNotIn("https", extracted_words)
        self.assertNotIn("google.com", extracted_words)
        self.assertNotIn("test@example.com", extracted_words)

    def test_personal_dictionary_persistence(self):
        self.engine.set_language("en")
        test_custom_word = "mycustomtechword"

        # Initially misspelled
        self.assertTrue(self.engine.is_misspelled(test_custom_word))

        # Add to personal dictionary
        self.engine.add_to_personal_dictionary(test_custom_word)

        # Now it must NOT be misspelled
        self.assertFalse(self.engine.is_misspelled(test_custom_word))

        # Must be persisted in SQLite
        db_words = database.get_dictionary_words()
        self.assertIn(test_custom_word, db_words)

        # Clean up
        database.remove_dictionary_word(test_custom_word)

    def test_session_ignore_word(self):
        self.engine.set_language("en")
        word = "specialtemporayterm"

        self.assertTrue(self.engine.is_misspelled(word))
        self.engine.ignore_word(word)
        self.assertFalse(self.engine.is_misspelled(word))

    def test_proofing_toggle(self):
        self.engine.set_enabled(False)
        self.assertFalse(self.engine.is_enabled)
        # When disabled, nothing is reported as misspelled
        self.assertFalse(self.engine.is_misspelled("wrld"))
        self.assertEqual(self.engine.tokenize_line("Hello wrld"), [])

        self.engine.set_enabled(True)
        self.assertTrue(self.engine.is_enabled)
        self.assertTrue(self.engine.is_misspelled("wrld"))

    def test_highlighter_spellcheck_underline(self):
        self.engine.set_language("en")
        doc = QTextDocument("Hello wrld world")
        highlighter = MarkdownHighlighter(doc, theme="light")
        highlighter.rehighlight()

        block = doc.firstBlock()
        layout_formats = block.layout().formats()
        self.assertGreaterEqual(len(layout_formats), 1)

        # Verify that 'wrld' at start=6 length=4 has SpellCheckUnderline
        found_spellcheck = False
        for f in layout_formats:
            if f.start == 6 and f.length == 4:
                self.assertEqual(f.format.underlineStyle(), QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
                found_spellcheck = True
            elif f.start == 11:
                self.assertNotEqual(f.format.underlineStyle(), QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self.assertTrue(found_spellcheck)

    def test_format_toolbar_spellcheck_button(self):
        editor = QTextEdit()
        toolbar = FormatToolbar(editor)
        self.assertTrue(hasattr(toolbar, "btn_spell"))
        self.assertTrue(toolbar.btn_spell.isCheckable())
        self.assertTrue(toolbar.btn_spell.isChecked())

        # Toggle button
        toolbar.btn_spell.setChecked(False)
        self.assertFalse(self.engine.is_enabled)
        self.assertIn("ABC", toolbar.btn_spell.text())

        toolbar.btn_spell.setChecked(True)
        self.assertTrue(self.engine.is_enabled)
        self.assertIn("ABC✓", toolbar.btn_spell.text())


if __name__ == "__main__":
    unittest.main()
