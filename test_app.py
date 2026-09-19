import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(PROJECT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR.parent))

try:
    from sticky_notes_app import database
except ImportError:
    import database

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

    # Test duplicate
    dup_id = database.duplicate_note(new_id)
    dup_note = database.get_note(dup_id)
    assert dup_note is not None
    assert dup_note["title"] == "Test Title (Copy)"
    assert dup_note["content"] == "Test Content in **Markdown**"
    assert dup_note["color_hex"] == "#FFCDD2"
    print(f"Duplicated note: {dup_id}")

    # Test bulk delete
    bulk_1 = database.create_note("Bulk 1", "Content 1")
    bulk_2 = database.create_note("Bulk 2", "Content 2")
    database.delete_multiple_notes([bulk_1, bulk_2, new_id, dup_id])
    assert database.get_note(bulk_1) is None
    assert database.get_note(bulk_2) is None
    assert database.get_note(new_id) is None
    assert database.get_note(dup_id) is None

    print("[SUCCESS] All database operations (including duplicate and bulk delete) passed!")

def test_imports():
    print("Testing PySide6 widget imports...")
    try:
        from sticky_notes_app.styles import APP_STYLESHEET, NOTE_COLORS
        from sticky_notes_app.components.color_picker_flyout import ColorPickerFlyout
        from sticky_notes_app.components.note_card import NoteCard
        from sticky_notes_app.views.grid_view import StickyNotesGridView
        from sticky_notes_app.views.editor_view import NoteEditorView
        from sticky_notes_app.main import MainWindow
    except ImportError:
        from styles import APP_STYLESHEET, NOTE_COLORS
        from components.color_picker_flyout import ColorPickerFlyout
        from components.note_card import NoteCard
        from views.grid_view import StickyNotesGridView
        from views.editor_view import NoteEditorView
        from main import MainWindow
    print("[SUCCESS] All modules and Qt widgets imported successfully!")

if __name__ == "__main__":
    test_database()
    test_imports()
    print("[ALL PASSED] All verification tests passed successfully!")
