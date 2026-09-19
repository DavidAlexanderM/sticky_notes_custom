import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sticky_notes_app import database

def test_database():
    print("Testing database operations...")
    database.init_db()
    notes = database.get_all_notes()
    print(f"Total seeded notes: {len(notes)}")
    assert len(notes) >= 1, "Database should have initial notes"

    # Test create
    new_id = database.create_note("Test Title", "Test Content in **Markdown**", "#FFCDD2")
    print(f"Created note: {new_id}")
    
    note = database.get_note(new_id)
    assert note is not None
    assert note["title"] == "Test Title"
    assert note["color_hex"] == "#FFCDD2"

    # Test update
    database.update_note(new_id, title="Updated Title", color_hex="#C8E6C9")
    updated = database.get_note(new_id)
    assert updated["title"] == "Updated Title"
    assert updated["color_hex"] == "#C8E6C9"

    # Test delete
    database.delete_note(new_id)
    deleted = database.get_note(new_id)
    assert deleted is None

    print("[SUCCESS] All database operations passed!")

def test_imports():
    print("Testing PySide6 widget imports...")
    from sticky_notes_app.styles import APP_STYLESHEET, NOTE_COLORS
    from sticky_notes_app.components.color_picker_flyout import ColorPickerFlyout
    from sticky_notes_app.components.note_card import NoteCard
    from sticky_notes_app.views.grid_view import StickyNotesGridView
    from sticky_notes_app.views.editor_view import NoteEditorView
    from sticky_notes_app.main import MainWindow
    print("[SUCCESS] All modules and Qt widgets imported successfully!")

if __name__ == "__main__":
    test_database()
    test_imports()
    print("[ALL PASSED] All verification tests passed successfully!")
