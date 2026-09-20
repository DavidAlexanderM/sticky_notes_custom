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
from components.project_dialog import NewProjectDialog, ManageProjectsDialog
from views.grid_view import StickyNotesGridView
from views.editor_view import NoteEditorView


class TestProjectStacks(unittest.TestCase):
    """
    Automated test suite verifying Project Stacks and Note Collections:
    - Multi-project database architecture and note count tracking
    - Note creation under active project stacks
    - Filtered note retrieval by project stack and 'all' notes overview
    - Moving notes between project stacks (single and batch)
    - Safe deletion with automatic zero-data-loss reassignment to default
    - UI dialogs (NewProjectDialog, ManageProjectsDialog)
    - GridView and EditorView project stack switcher integration
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

    def tearDown(self):
        database.get_db_path = self.orig_get_db_path
        database.get_preferences_path = self.orig_get_pref_path
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_default_project_exists(self):
        """Verify the 'default' project exists with name 'General Notes'."""
        projects = database.get_all_projects()
        default_proj = next((p for p in projects if p["id"] == "default"), None)
        self.assertIsNotNone(default_proj)
        self.assertEqual(default_proj["name"], "General Notes")

    def test_create_and_get_project(self):
        """Verify creating a project stack and retrieving its properties."""
        p_id = database.create_project("Doctora Research", color_hex="#8AB4F8")
        self.assertTrue(bool(p_id))

        proj = database.get_project(p_id)
        self.assertIsNotNone(proj)
        self.assertEqual(proj["name"], "Doctora Research")
        self.assertEqual(proj["color_hex"], "#8AB4F8")

    def test_update_project(self):
        """Verify updating project stack name and color."""
        p_id = database.create_project("Temp Stack", color_hex="#81C995")
        database.update_project(p_id, name="Updated Stack", color_hex="#FDD663")

        proj = database.get_project(p_id)
        self.assertEqual(proj["name"], "Updated Stack")
        self.assertEqual(proj["color_hex"], "#FDD663")

    def test_notes_assigned_to_project_and_filtering(self):
        """Verify notes created under a project stack are properly categorized and filtered."""
        p_id = database.create_project("Personal", color_hex="#FF8BCB")

        # Create note under custom project
        n1 = database.create_note(title="Project Note 1", content="Content 1", project_id=p_id)
        # Create note under default
        n2 = database.create_note(title="General Note 1", content="Content 2", project_id="default")

        # Check project notes
        project_notes = database.get_all_notes(project_id=p_id)
        project_note_ids = [n["id"] for n in project_notes]
        self.assertIn(n1, project_note_ids)
        self.assertNotIn(n2, project_note_ids)

        # Check all notes overview
        all_notes = database.get_all_notes(project_id="all")
        all_note_ids = [n["id"] for n in all_notes]
        self.assertIn(n1, all_note_ids)
        self.assertIn(n2, all_note_ids)

        # Check note count on project
        projects = database.get_all_projects()
        p_item = next(p for p in projects if p["id"] == p_id)
        self.assertGreaterEqual(p_item["note_count"], 1)

    def test_move_notes_to_project(self):
        """Verify moving notes between project stacks."""
        p1 = database.create_project("Stack Alpha", color_hex="#8AB4F8")
        p2 = database.create_project("Stack Beta", color_hex="#C58AF9")

        note_id = database.create_note(title="Movable Note", content="Move me", project_id=p1)
        
        # Verify in p1
        self.assertEqual(database.get_note(note_id)["project_id"], p1)

        # Move to p2
        database.move_notes_to_project([note_id], p2)
        self.assertEqual(database.get_note(note_id)["project_id"], p2)

    def test_delete_project_reassigns_notes_safely(self):
        """Verify deleting a project stack reassigns all its notes to 'default' with zero data loss."""
        p_id = database.create_project("Temporary Stack", color_hex="#FCAD70")
        note_id = database.create_note(title="Safety Note", content="Must not be deleted", project_id=p_id)

        # Ensure note is in p_id
        self.assertEqual(database.get_note(note_id)["project_id"], p_id)

        # Delete project
        result = database.delete_project(p_id)
        self.assertTrue(result)

        # Project should be gone
        self.assertIsNone(database.get_project(p_id))

        # Note should still exist and now belong to 'default'
        reassigned_note = database.get_note(note_id)
        self.assertIsNotNone(reassigned_note)
        self.assertEqual(reassigned_note["project_id"], "default")

    def test_default_project_cannot_be_deleted(self):
        """Verify the 'default' project stack cannot be deleted."""
        result = database.delete_project("default")
        self.assertFalse(result)
        self.assertIsNotNone(database.get_project("default"))

    def test_active_project_preference(self):
        """Verify setting and getting the active project ID preference."""
        p_id = database.create_project("Active Test", color_hex="#78D9EC")
        database.set_active_project_id(p_id)
        self.assertEqual(database.get_active_project_id(), p_id)

        database.set_active_project_id("default")
        self.assertEqual(database.get_active_project_id(), "default")

    def test_new_project_dialog_ui(self):
        """Verify NewProjectDialog initializes correctly and can validate inputs."""
        dlg = NewProjectDialog()
        self.assertEqual(dlg.windowTitle(), "Create New Project Stack")
        self.assertIsNotNone(dlg.name_input)
        self.assertGreater(len(dlg.color_buttons), 0)
        dlg.close()

    def test_manage_projects_dialog_ui(self):
        """Verify ManageProjectsDialog populates existing project stacks."""
        dlg = ManageProjectsDialog()
        self.assertGreaterEqual(dlg.list_widget.count(), 1)
        dlg.close()

    def test_grid_view_project_switcher(self):
        """Verify StickyNotesGridView displays the Project Switcher button and switches stacks."""
        grid = StickyNotesGridView()
        self.assertTrue(hasattr(grid, "project_btn"))
        self.assertTrue(hasattr(grid, "active_project_id"))

        # Switch to "all"
        grid._switch_active_project("all")
        self.assertEqual(grid.active_project_id, "all")
        self.assertIn("All Notes", grid.project_btn.text())

        # Switch back to "default"
        grid._switch_active_project("default")
        self.assertEqual(grid.active_project_id, "default")
        grid.close()

    def test_editor_view_project_stack_badge(self):
        """Verify NoteEditorView displays the project badge and updates when note is loaded."""
        editor = NoteEditorView()
        self.assertTrue(hasattr(editor, "project_badge_btn"))
        self.assertTrue(hasattr(editor, "current_project_id"))

        # Create note under default and load it
        note_id = database.create_note(title="Editor Project Test", content="Hello", project_id="default")
        editor.load_note(note_id)
        self.assertEqual(editor.current_project_id, "default")
        self.assertIn("General Notes", editor.project_badge_btn.text())
        editor.close()


if __name__ == "__main__":
    unittest.main()
