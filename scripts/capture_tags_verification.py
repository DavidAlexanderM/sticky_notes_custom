import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QPoint

import database
import i18n
from theme_manager import get_theme_manager
from main import MainWindow
from components.tag_selector_flyout import TagSelectorFlyout

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    theme_mgr = get_theme_manager()
    app.setStyleSheet(theme_mgr.get_app_stylesheet())

    # Ensure custom tags exist for Danielle
    database.init_db()
    database.create_custom_tag("Danielle's Projects", "#8B5CF6")
    database.create_custom_tag("University Research", "#EC4899")
    database.create_custom_tag("Client Follow-up", "#10B981")

    # Assign tags to visible free notes
    notes = database.get_all_notes("all")
    free_notes = [n for n in notes if n.get("project_id", "default") == "default"]
    if len(free_notes) >= 1:
        database.set_note_tags(free_notes[0]["id"], ["Danielle's Projects", "Urgent"])
    if len(free_notes) >= 2:
        database.set_note_tags(free_notes[1]["id"], ["University Research", "To-Do"])
    if len(free_notes) >= 3:
        database.set_note_tags(free_notes[2]["id"], ["Ideas", "Client Follow-up"])
    if len(free_notes) >= 4:
        database.set_note_tags(free_notes[3]["id"], ["Work", "Danielle's Projects"])

    # Instantiate MainWindow
    win = MainWindow()
    win.resize(1180, 750)
    win.show()

    # Process events to allow UI layout and render
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    # Capture 1: Board with Tag Side Panel in English
    artifacts_dir = Path(r"C:\Users\evion\.gemini\antigravity\brain\91649549-e45d-4eac-8bbb-65bfebabec43")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    pix1 = win.grab()
    pix1.save(str(artifacts_dir / "screenshot_tags_en.png"))
    print("[OK] Captured screenshot_tags_en.png")

    # Toggle to Spanish
    win.grid_view._toggle_language()
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    pix2 = win.grab()
    pix2.save(str(artifacts_dir / "screenshot_tags_es.png"))
    print("[OK] Captured screenshot_tags_es.png")

    # Switch back to English
    win.grid_view._toggle_language()
    app.processEvents()

    # Show and capture Tag Selector Flyout directly
    if free_notes:
        flyout = TagSelectorFlyout(free_notes[0]["id"])
        flyout.show()
        app.processEvents()
        time.sleep(0.3)
        app.processEvents()
        pix3 = flyout.grab()
        pix3.save(str(artifacts_dir / "screenshot_tag_flyout.png"))
        print("[OK] Captured screenshot_tag_flyout.png")
        flyout.close()

    win.close()
    print("[ALL SCREENSHOTS CAPTURED SUCCESSFULLY]")

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
