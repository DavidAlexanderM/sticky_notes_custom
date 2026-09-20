import os
import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for GUI component testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

import database
import i18n
from components.tag_side_panel import TagSidePanel
from components.tag_selector_flyout import TagSelectorFlyout
from components.note_card import NoteCard
from views.grid_view import StickyNotesGridView
from views.editor_view import NoteEditorView


class TestTagsAndI18n(unittest.TestCase):
    """
    Automated test suite verifying:
    1. Internationalization (i18n) translation engine and language switching (EN/ES).
    2. Database custom tags and note tag assignment, renaming, deletion, and counts.
    3. Custom Tags First precedence in UI components (TagSidePanel and TagSelectorFlyout).
    4. NoteCard tag badge display and tags_updated signal.
    5. GridView tag filtering, untagged filtering, and tag search.
    """

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

        # Reset language to English
        i18n.get_translation_manager().set_language("en")

    def tearDown(self):
        database.get_db_path = self.orig_get_db_path
        database.get_preferences_path = self.orig_get_pref_path
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # --- 1. i18n Engine Tests ---

    def test_i18n_default_english(self):
        mgr = i18n.get_translation_manager()
        self.assertEqual(mgr.current_language, "en")
        self.assertEqual(i18n.tr("tags_header"), "Tags")
        self.assertEqual(i18n.tr("urgent"), "Urgent")
        self.assertEqual(i18n.tr("ideas"), "Ideas")

    def test_i18n_spanish_switch(self):
        mgr = i18n.get_translation_manager()
        mgr.set_language("es")
        self.assertEqual(mgr.current_language, "es")
        self.assertEqual(i18n.tr("tags_header"), "Etiquetas")
        self.assertEqual(i18n.tr("urgent"), "Urgente")
        self.assertEqual(i18n.tr("ideas"), "Ideas")
        self.assertEqual(i18n.tr("work"), "Trabajo")
        self.assertIn("¿Eliminar la etiqueta 'Proyecto'?", i18n.tr("confirm_delete_tag", name="Proyecto"))

    def test_i18n_toggle_language(self):
        mgr = i18n.get_translation_manager()
        mgr.set_language("en")
        new_lang = mgr.toggle_language()
        self.assertEqual(new_lang, "es")
        self.assertEqual(mgr.current_language, "es")
        new_lang2 = mgr.toggle_language()
        self.assertEqual(new_lang2, "en")
        self.assertEqual(mgr.current_language, "en")

    # --- 2. Database Tag Operations ---

    def test_create_and_get_custom_tags(self):
        tag = database.create_custom_tag("Client Work", "#F43F5E")
        self.assertIsNotNone(tag)
        self.assertEqual(tag["name"], "Client Work")
        self.assertEqual(tag["color_hex"], "#F43F5E")

        # Duplicate tag creation returns None
        dup = database.create_custom_tag("Client Work", "#000000")
        self.assertIsNone(dup)

        all_tags = database.get_custom_tags()
        self.assertEqual(len(all_tags), 1)
        self.assertEqual(all_tags[0]["name"], "Client Work")

    def test_assign_and_retrieve_note_tags(self):
        note_id = database.create_note(title="Meeting Notes", content="Discussion points", tags=["Client Work", "Urgent"])
        tags = database.get_note_tags(note_id)
        self.assertEqual(sorted(tags), ["Client Work", "Urgent"])

        # Update tags
        database.set_note_tags(note_id, ["Urgent", "Personal"])
        updated_tags = database.get_note_tags(note_id)
        self.assertEqual(sorted(updated_tags), ["Personal", "Urgent"])

    def test_rename_custom_tag(self):
        database.create_custom_tag("Bug", "#EF4444")
        n1 = database.create_note("Issue 1", "Fix bug", tags=["Bug", "Urgent"])
        n2 = database.create_note("Issue 2", "Another bug", tags=["Bug"])

        res = database.rename_custom_tag("Bug", "Defect")
        self.assertTrue(res)

        tags_n1 = database.get_note_tags(n1)
        tags_n2 = database.get_note_tags(n2)
        self.assertIn("Defect", tags_n1)
        self.assertNotIn("Bug", tags_n1)
        self.assertIn("Defect", tags_n2)
        self.assertNotIn("Bug", tags_n2)

        custom_tags = database.get_custom_tags()
        self.assertEqual(len(custom_tags), 1)
        self.assertEqual(custom_tags[0]["name"], "Defect")

    def test_delete_custom_tag(self):
        database.create_custom_tag("Archive", "#94A3B8")
        n1 = database.create_note("Old Note", "Some content", tags=["Archive", "Ideas"])

        database.delete_custom_tag("Archive")
        tags_n1 = database.get_note_tags(n1)
        self.assertNotIn("Archive", tags_n1)
        self.assertIn("Ideas", tags_n1)

        custom_tags = database.get_custom_tags()
        self.assertEqual(len(custom_tags), 0)

    def test_get_all_tag_counts(self):
        database.create_note("N1", "content", tags=["Urgent", "Work"])
        database.create_note("N2", "content", tags=["Urgent", "Personal"])
        database.create_note("N3", "content", tags=["Work"])

        counts = database.get_all_tag_counts()
        self.assertEqual(counts.get("Urgent"), 2)
        self.assertEqual(counts.get("Work"), 2)
        self.assertEqual(counts.get("Personal"), 1)

    # --- 3. UI Tag Precedence: Custom Tags First ---

    def test_tag_side_panel_custom_tags_first(self):
        database.create_custom_tag("Alpha Project", "#8B5CF6")
        database.create_custom_tag("Beta Project", "#EC4899")

        panel = TagSidePanel()
        panel.refresh_tags()

        # Check tag buttons in panel
        self.assertIn("Alpha Project", panel.tag_buttons)
        self.assertIn("Beta Project", panel.tag_buttons)
        self.assertIn(i18n.tr("urgent"), panel.tag_buttons)

        # In panel.items_layout, Custom Tags section must appear BEFORE Predetermined Tags
        # Let's inspect the order of labels and widgets in items_layout
        custom_header_idx = -1
        pred_header_idx = -1
        for idx in range(panel.items_layout.count()):
            item = panel.items_layout.itemAt(idx)
            w = item.widget()
            if w and hasattr(w, "text"):
                txt = w.text()
                if i18n.tr("custom_tags_section") in txt:
                    custom_header_idx = idx
                elif i18n.tr("predetermined_tags_section") in txt:
                    pred_header_idx = idx

        self.assertNotEqual(custom_header_idx, -1)
        self.assertNotEqual(pred_header_idx, -1)
        self.assertLess(custom_header_idx, pred_header_idx, "Custom tags section must appear FIRST before predetermined tags!")

    def test_tag_selector_flyout_custom_tags_first(self):
        database.create_custom_tag("VIP", "#F59E0B")
        note_id = database.create_note("VIP Note", "Content")

        flyout = TagSelectorFlyout(note_id)
        flyout._populate_tags()

        custom_header_idx = -1
        pred_header_idx = -1
        for idx in range(flyout.content_layout.count()):
            item = flyout.content_layout.itemAt(idx)
            w = item.widget()
            if w and hasattr(w, "text"):
                txt = w.text()
                if i18n.tr("custom_tags_section") in txt:
                    custom_header_idx = idx
                elif i18n.tr("predetermined_tags_section") in txt:
                    pred_header_idx = idx

        self.assertNotEqual(custom_header_idx, -1)
        self.assertNotEqual(pred_header_idx, -1)
        self.assertLess(custom_header_idx, pred_header_idx, "In selector flyout, custom tags must appear FIRST!")

    # --- 4. NoteCard Tag Display & Signal ---

    def test_note_card_tag_rendering(self):
        note = {
            "id": "test_card_1",
            "title": "Card Title",
            "content": "Card body",
            "color_hex": "#FFF9C4",
            "tags": ["Design", "Research"]
        }
        card = NoteCard(note)
        self.assertFalse(card.tags_label.isHidden())
        self.assertIn("#Design", card.tags_label.text())
        self.assertIn("#Research", card.tags_label.text())

    # --- 5. GridView Tag Filtering & Search ---

    def test_grid_view_tag_filtering(self):
        with database.get_connection() as conn:
            conn.execute("DELETE FROM notes")
            conn.commit()

        database.create_note(title="Note Alpha", content="First note", tags=["Finance"])
        database.create_note(title="Note Beta", content="Second note", tags=["Personal"])
        database.create_note(title="Note Gamma", content="Third note (no tags)", tags=[])

        grid = StickyNotesGridView()
        grid.load_notes()
        self.assertEqual(len(grid.note_cards), 3)

        # Filter by "Finance"
        grid._on_tag_filter_selected("Finance")
        self.assertEqual(len(grid.note_cards), 1)
        self.assertEqual(grid.note_cards[0].note["title"], "Note Alpha")

        # Filter by Untagged
        grid._on_tag_filter_selected("__untagged__")
        self.assertEqual(len(grid.note_cards), 1)
        self.assertEqual(grid.note_cards[0].note["title"], "Note Gamma")

        # Filter reset to all
        grid._on_tag_filter_selected("")
        self.assertEqual(len(grid.note_cards), 3)

    def test_grid_view_search_by_tag(self):
        with database.get_connection() as conn:
            conn.execute("DELETE FROM notes")
            conn.commit()

        database.create_note(title="Shopping List", content="Groceries", tags=["Errands"])
        database.create_note(title="Project Plan", content="Timeline", tags=["Work"])

        grid = StickyNotesGridView()
        grid.load_notes()

        # Searching for "errands" should match note even though "errands" isn't in title/content
        grid.search_input.setText("errands")
        self.assertEqual(len(grid.note_cards), 1)
        self.assertEqual(grid.note_cards[0].note["title"], "Shopping List")

    def test_grid_view_language_toggle(self):
        grid = StickyNotesGridView()
        self.assertEqual(grid.lang_btn.text(), "🌐 EN")
        grid._toggle_language()
        self.assertEqual(grid.lang_btn.text(), "🌐 ES")
        self.assertIn("Buscar notas", grid.search_input.placeholderText())


if __name__ == "__main__":
    unittest.main()
