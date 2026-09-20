import os
import sys
import unittest
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
from views.editor_view import MarkdownTextEdit
from components.note_card import NoteCard


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


if __name__ == "__main__":
    unittest.main()
