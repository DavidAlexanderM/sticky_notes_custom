import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QUrl, QMimeData
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument

# Ensure QApplication exists for GUI component testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

import icons
from markdown_highlighter import MarkdownHighlighter
from views.editor_view import MarkdownTextEdit, NoteEditorView
from views.grid_view import StickyNotesGridView
from components.note_card import NoteCard
from components.color_picker_flyout import ColorPickerFlyout
from components.help_dialog import HelpAboutDialog
from components.share_dialog import ShareNoteDialog, strip_markdown
from theme_manager import detect_os_theme, get_theme_manager
from main import MainWindow


class TestGUIFeatures(unittest.TestCase):
    """
    Automated test suite covering SVG vector icon rendering,
    in-editor live markdown syntax highlighting, media drag-and-drop,
    and note card hover micro-interactions.
    """

    def test_svg_icons_generation(self):
        """Verify all defined vector SVG icons render valid non-null QIcons."""
        expected_icons = [
            "arrow_left", "copy", "share", "sun", "moon", "plus", "search",
            "check", "check_square", "trash", "more_horizontal", "bold",
            "italic", "underline", "strikethrough", "heading", "list", "code",
            "image", "mic", "video", "palette", "play", "pause", "external_link",
            "close", "edit"
        ]
        for name in expected_icons:
            icon = icons.get_icon(name, color="#000000", size=20)
            self.assertFalse(icon.isNull(), f"Icon '{name}' should not be null")
            pixmap = icons.render_svg_pixmap(name, color="#2563EB", size=24)
            self.assertFalse(pixmap.isNull(), f"Pixmap for '{name}' should not be null")
            self.assertEqual(pixmap.width(), 24)
            self.assertEqual(pixmap.height(), 24)

    def test_themed_icon_roles(self):
        """Verify get_themed_icon adapts to light and dark themes."""
        ico_light = icons.get_themed_icon("sun", role="primary", theme="light")
        ico_dark = icons.get_themed_icon("moon", role="primary", theme="dark")
        self.assertFalse(ico_light.isNull())
        self.assertFalse(ico_dark.isNull())

    def test_markdown_highlighter_execution(self):
        """Verify MarkdownHighlighter processes markdown elements without exception."""
        doc = QTextDocument()
        highlighter = MarkdownHighlighter(doc, theme="light")

        markdown_sample = """# Heading 1
## Heading 2
### Heading 3

**Bold text** and __also bold__
*Italic text* and _also italic_
~~Strikethrough~~
`inline code`

```python
def test():
    return True
```

- [ ] Unfinished task
- [x] Completed task

[Click Here](file:///C:/test/path/voice_note_123.m4a)
![Screenshot](file:///C:/test/path/image.png)

> Inspiring blockquote
---
"""
        # Setting plaintext triggers highlightBlock for each block
        doc.setPlainText(markdown_sample)
        self.assertEqual(doc.blockCount(), 23)

        # Switch theme dynamically
        highlighter.set_theme("dark")
        highlighter.set_theme("sepia")
        highlighter.set_theme("light")

    def test_markdown_text_edit_drag_and_drop_detection(self):
        """Verify MarkdownTextEdit detects media MIME types properly."""
        editor = MarkdownTextEdit()
        self.assertTrue(editor.acceptDrops())

        mime_image = QMimeData()
        mime_image.setUrls([QUrl.fromLocalFile("C:/test/photo.png")])
        self.assertTrue(editor.is_supported_media_mime(mime_image))

        mime_audio = QMimeData()
        mime_audio.setUrls([QUrl.fromLocalFile("C:/test/recording.m4a")])
        self.assertTrue(editor.is_supported_media_mime(mime_audio))

        mime_video = QMimeData()
        mime_video.setUrls([QUrl.fromLocalFile("C:/test/video.mp4")])
        self.assertTrue(editor.is_supported_media_mime(mime_video))

        # Non-media files should not be accepted as media insertions
        mime_text = QMimeData()
        mime_text.setUrls([QUrl.fromLocalFile("C:/test/document.exe")])
        self.assertFalse(editor.is_supported_media_mime(mime_text))

    def test_note_card_components_and_menu(self):
        """Verify NoteCard includes Quick Action menu button (⋯) and renders cleanly."""
        sample_note = {
            "id": "test_note_gui",
            "title": "GUI Overhaul Note",
            "content": "**Bold title**\n- [ ] Task 1\n🎵 [Play Voice Note: test.m4a](file:///path/test.m4a)",
            "color_hex": "#FFF9C4",
            "updated_at": "2026-09-20T10:00:00"
        }
        card = NoteCard(sample_note)
        self.assertIsNotNone(card.menu_btn)
        self.assertIsNotNone(card.palette_icon_btn)
        self.assertFalse(card.menu_btn.isHidden())
        self.assertEqual(card.title_label.text(), "GUI Overhaul Note")

        # Excerpt should clean raw media and task markers
        excerpt = card.snippet_label.text()
        self.assertNotIn("🎵", excerpt)
        self.assertNotIn("file:///", excerpt)
        self.assertIn("Bold title", excerpt)

        # Test selection mode hides menu button
        card.set_selection_mode(True)
        self.assertTrue(card.menu_btn.isHidden())
        self.assertFalse(card.check_indicator.isHidden())

        card.set_selection_mode(False)
        self.assertFalse(card.menu_btn.isHidden())
        self.assertTrue(card.check_indicator.isHidden())

    def test_note_editor_view_instantiation_and_theme_toggle(self):
        """Verify NoteEditorView initializes without missing attribute errors and handles theme switches."""
        editor_view = NoteEditorView()
        self.assertIsNotNone(editor_view.play_pause_btn)
        self.assertIsNotNone(editor_view.theme_btn)
        self.assertIsNotNone(editor_view.highlighter)

        # Trigger dynamic theme switch
        editor_view._toggle_theme()
        self.assertIsNotNone(editor_view.play_pause_btn.icon())
        self.assertFalse(editor_view.play_pause_btn.icon().isNull())
        editor_view.theme_mgr.set_theme("light")

    def test_main_window_instantiation(self):
        """Verify the full MainWindow instantiates completely without startup exceptions."""
        win = MainWindow()
        self.assertIsNotNone(win.grid_view)
        self.assertIsNotNone(win.editor_view)
        self.assertEqual(win.stacked_widget.currentIndex(), 0)

    def test_help_about_dialog_structure(self):
        """Verify HelpAboutDialog initializes with all 3 tabs and diagnostic paths."""
        dialog = HelpAboutDialog()
        self.assertEqual(dialog.tabs.count(), 3)
        self.assertEqual(dialog.tabs.tabText(0), "Keyboard Shortcuts")
        self.assertEqual(dialog.tabs.tabText(1), "Markdown & Media")
        self.assertEqual(dialog.tabs.tabText(2), "About")
        dialog.close()

    def test_color_picker_flyout_theming(self):
        """Verify ColorPickerFlyout renders and adapts to theme changes."""
        mgr = get_theme_manager()
        mgr.set_theme("dark")
        flyout_dark = ColorPickerFlyout()
        self.assertIn("#1E1F20", flyout_dark.card.styleSheet())
        flyout_dark.close()

        mgr.set_theme("light")
        flyout_light = ColorPickerFlyout()
        self.assertIn("#FFFFFF", flyout_light.card.styleSheet())
        flyout_light.close()

    def test_grid_shift_and_ctrl_selection(self):
        """Verify Shift range selection and Ctrl group selection in StickyNotesGridView."""
        grid = StickyNotesGridView()
        notes_mock = [
            {"id": f"note_{i}", "title": f"Note {i}", "content": "Sample", "color_hex": "#FFF9C4", "updated_at": "2026-09-20"}
            for i in range(5)
        ]
        grid.all_notes = notes_mock
        grid._filter_and_render_notes()
        self.assertEqual(len(grid.note_cards), 5)

        # 1. Normal click card 1 -> focused and anchor set, 0 selected
        grid._on_card_clicked("note_1", shift_held=False, ctrl_held=False)
        self.assertEqual(grid.anchor_card_index, 1)
        self.assertEqual(len(grid.selected_note_ids), 0)

        # 2. Shift+Click card 3 -> selects notes 1, 2, 3 (continuous range)
        grid._on_card_clicked("note_3", shift_held=True, ctrl_held=False)
        self.assertEqual(grid.selected_note_ids, {"note_1", "note_2", "note_3"})
        self.assertFalse(grid.action_bar.isHidden())

        # 3. Ctrl+Click card 4 -> adds note 4 to group
        grid._on_card_clicked("note_4", shift_held=False, ctrl_held=True)
        self.assertIn("note_4", grid.selected_note_ids)
        self.assertEqual(len(grid.selected_note_ids), 4)

        # 4. Ctrl+Click card 2 -> toggles note 2 off
        grid._on_card_clicked("note_2", shift_held=False, ctrl_held=True)
        self.assertNotIn("note_2", grid.selected_note_ids)
        self.assertEqual(len(grid.selected_note_ids), 3)

        # 5. Clear selection -> action bar hides
        grid._clear_selection()
        self.assertEqual(len(grid.selected_note_ids), 0)
        self.assertTrue(grid.action_bar.isHidden())

    def test_os_theme_detection(self):
        """Verify detect_os_theme returns a valid theme string ('light' or 'dark')."""
        detected = detect_os_theme()
        self.assertIn(detected, ["light", "dark"])

    def test_share_dialog_and_plain_text_stripping(self):
        """Verify ShareNoteDialog initializes and clean plain-text stripping operates properly."""
        md_sample = "# Meeting Notes\n\n**Action Items:**\n- [ ] Fix bug\n- [x] Write tests\n\nCheck [link](https://example.com) and `code`."
        plain = strip_markdown(md_sample)
        self.assertNotIn("#", plain)
        self.assertNotIn("**", plain)
        self.assertNotIn("`", plain)
        self.assertIn("Meeting Notes", plain)
        self.assertIn("https://example.com", plain)

        # Dialog instantiation and button availability
        dialog = ShareNoteDialog("Project Kickoff", md_sample)
        self.assertIsNotNone(dialog.btn_mail)
        self.assertIsNotNone(dialog.btn_whatsapp)
        self.assertIsNotNone(dialog.btn_telegram)
        self.assertIsNotNone(dialog.btn_facebook)
        self.assertIsNotNone(dialog.btn_x)
        self.assertIsNotNone(dialog.btn_copy_md)
        self.assertIsNotNone(dialog.btn_copy_txt)
        self.assertIsNotNone(dialog.btn_save_md)
        self.assertIsNotNone(dialog.btn_save_html)
        dialog.close()

    def test_share_dialog_media_extraction_and_packaging(self):
        """Verify media attachments extraction, file URL stripping, and packaging."""
        import tempfile, zipfile
        from media_manager import get_attachments_dir
        from components.share_dialog import extract_media_attachments

        # Create temporary mock attachment
        att_dir = get_attachments_dir()
        test_img = att_dir / "test_share_capture.png"
        with open(test_img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        try:
            url_str = f"file:///{test_img.resolve().as_posix()}"
            sample_content = f"Here is the report:\n![Screenshot]({url_str})\nCheck [audio](attachments/voice.wav)"
            
            # 1. Plain text stripping replaces file:/// URLs with readable label
            stripped = strip_markdown(sample_content)
            self.assertNotIn("file:///", stripped)
            self.assertIn("[Screenshot]", stripped)

            # 2. Extract media attachments
            extracted = extract_media_attachments(sample_content)
            self.assertTrue(any(p.name == "test_share_capture.png" for p in extracted))

            # 3. ShareNoteDialog with attachments has media buttons
            dialog = ShareNoteDialog("Media Note", sample_content)
            self.assertIsNotNone(dialog.btn_copy_image)
            self.assertIsNotNone(dialog.btn_copy_files)
            self.assertIsNotNone(dialog.btn_export_zip)
            self.assertIsNotNone(dialog.btn_open_folder)

            # 4. Test ZIP export package
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                tmp_zip_path = tmp_zip.name
            
            with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(tmp_zip_path, "zip")):
                dialog._export_zip_package()

            self.assertTrue(Path(tmp_zip_path).exists())
            with zipfile.ZipFile(tmp_zip_path, "r") as zf:
                namelist = zf.namelist()
                self.assertTrue(any(n.endswith(".md") for n in namelist))
                self.assertIn("attachments/test_share_capture.png", namelist)

            if Path(tmp_zip_path).exists():
                Path(tmp_zip_path).unlink(missing_ok=True)
            dialog.close()

        finally:
            if test_img.exists():
                test_img.unlink(missing_ok=True)

    def test_note_stack_icon_rendering(self):
        """Verify 3D layered note stack vector icon renders cleanly with project colors."""
        for color in ["#F9AB00", "#34A853", "#4285F4", "#EA4335"]:
            icon = icons.render_note_stack_icon(color, size=24)
            self.assertFalse(icon.isNull(), f"Note stack icon for {color} should not be null")
            pix = icons.render_note_stack_pixmap(color, size=24)
            self.assertFalse(pix.isNull(), f"Note stack pixmap for {color} should not be null")
            self.assertEqual(pix.width(), 24)
            self.assertEqual(pix.height(), 24)

    def test_color_swatches_and_sort_combo(self):
        """Verify GridView contains color swatch icons for all colors and sort combobox."""
        grid = StickyNotesGridView()
        from styles import NOTE_COLORS
        for c in NOTE_COLORS:
            hex_val = c["hex"]
            self.assertIn(hex_val, grid.pill_buttons)
            btn = grid.pill_buttons[hex_val]
            self.assertEqual(btn.text(), "", f"Color pill for {c['name']} must have no text label")
            self.assertEqual(btn.objectName(), "ColorDotPill")
            self.assertEqual(btn.width(), 24)
            self.assertEqual(btn.height(), 24)

        self.assertIsNotNone(grid.sort_combo)
        self.assertEqual(grid.sort_combo.count(), 5)
        # Verify changing sort mode updates database preference
        import database
        grid.sort_combo.setCurrentIndex(1)  # created_asc
        self.assertEqual(database.get_sort_preference(), "created_asc")
        grid.close()

    def test_help_dialog_about_storage_tab(self):
        """Verify HelpAboutDialog About tab is wrapped in QScrollArea and has copyable path inputs."""
        dialog = HelpAboutDialog()
        self.assertEqual(dialog.tabs.count(), 3)
        about_widget = dialog.tabs.widget(2)
        from PySide6.QtWidgets import QScrollArea, QLineEdit
        self.assertIsInstance(about_widget, QScrollArea)
        
        # Verify QLineEdits exist for paths inside the about widget
        line_edits = about_widget.findChildren(QLineEdit)
        self.assertGreaterEqual(len(line_edits), 2)
        for le in line_edits:
            self.assertTrue(le.isReadOnly())
            self.assertTrue(len(le.text()) > 0)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
