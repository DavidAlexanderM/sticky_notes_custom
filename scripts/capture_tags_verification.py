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
from components.help_dialog import HelpAboutDialog

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    theme_mgr = get_theme_manager()
    app.setStyleSheet(theme_mgr.get_app_stylesheet())

    database.init_db()
    database.create_custom_tag("Danielle's Projects", "#8B5CF6")
    database.create_custom_tag("University Research", "#EC4899")
    database.create_custom_tag("Client Follow-up", "#10B981")

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

    win = MainWindow()
    win.resize(1180, 750)
    win.show()

    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    artifacts_dir = Path(r"C:\Users\evion\.gemini\antigravity\brain\91649549-e45d-4eac-8bbb-65bfebabec43")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    from i18n import get_translation_manager
    i18n_mgr = get_translation_manager()

    # 1. Ensure English and capture Board
    i18n_mgr.set_language("en")
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    pix1 = win.grab()
    pix1.save(str(artifacts_dir / "screenshot_board_fullwidth_en.png"))
    print("[OK] Captured screenshot_board_fullwidth_en.png")

    # 2. Switch explicitly to Spanish and capture Board
    i18n_mgr.set_language("es")
    app.processEvents()
    time.sleep(0.4)
    app.processEvents()

    pix2 = win.grab()
    pix2.save(str(artifacts_dir / "screenshot_board_fullwidth_es.png"))
    print("[OK] Captured screenshot_board_fullwidth_es.png")

    # 3. Open Help dialog in Spanish and capture
    help_dlg = HelpAboutDialog(win)
    help_dlg.show()
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    pix_help = help_dlg.grab()
    pix_help.save(str(artifacts_dir / "screenshot_help_es.png"))
    print("[OK] Captured screenshot_help_es.png")
    help_dlg.close()

    # 4. Open note in editor to verify the dedicated Editor Tags Bar
    if free_notes:
        win._open_note_editor(free_notes[0]["id"])
        app.processEvents()
        time.sleep(0.4)
        app.processEvents()

        pix_editor = win.grab()
        pix_editor.save(str(artifacts_dir / "screenshot_editor_tags_bar.png"))
        print("[OK] Captured screenshot_editor_tags_bar.png")

    win.close()
    print("[ALL SCREENSHOTS CAPTURED SUCCESSFULLY]")

if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
