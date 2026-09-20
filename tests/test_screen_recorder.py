"""
test_screen_recorder.py - Automated test suite for the Desktop Screen Recording subsystem.
Verifies ScreenRecorder engine initialization, screen discovery, and UI dialog lifecycle.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaFormat

# Ensure QApplication exists for GUI component testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

from media_manager import ScreenRecorder, FrameCaptureThread, get_available_screens, get_available_microphones
from components.screen_recorder_dialog import ScreenRecorderDialog, ScreenRecordingOverlay, RecordingCompleteDialog
from components.format_toolbar import FormatToolbar
from PySide6.QtWidgets import QTextEdit


class TestScreenRecorder(unittest.TestCase):
    """Test suite for ScreenRecorder engine and UI overlay components."""

    def test_screen_discovery(self):
        screens = get_available_screens()
        self.assertIsInstance(screens, list)
        # At least 1 screen must be detected in GUI session
        if screens:
            self.assertGreater(screens[0].geometry().width(), 0)
            self.assertGreater(screens[0].geometry().height(), 0)

    def test_screen_recorder_engine_init(self):
        recorder = ScreenRecorder()
        self.assertIsNotNone(recorder.session)
        self.assertIsNotNone(recorder.screen_capture)
        self.assertIsNotNone(recorder.recorder)
        self.assertFalse(recorder.is_recording())
        self.assertIn(recorder._extension, [".mp4", ".wmv", ".mkv"])

    def test_frame_capture_thread_init(self):
        screens = get_available_screens()
        screen = screens[0] if screens else None
        thread = FrameCaptureThread(screen, "dummy.mp4", fps=15)
        self.assertEqual(thread.fps, 15)
        self.assertEqual(thread.output_file, "dummy.mp4")
        self.assertFalse(thread.running)

    def test_overlay_hud_widget(self):
        overlay = ScreenRecordingOverlay()
        self.assertIsNotNone(overlay.pill)
        self.assertIsNotNone(overlay.time_lbl)
        self.assertIsNotNone(overlay.stop_btn)
        self.assertIsNotNone(overlay.cancel_btn)

        # Test formatted time update
        overlay.update_time(75)
        self.assertEqual(overlay.time_lbl.text(), "01:15")

        overlay.update_time(0)
        self.assertEqual(overlay.time_lbl.text(), "00:00")
        overlay.close()

    def test_recorder_dialog_instantiation(self):
        dialog = ScreenRecorderDialog()
        self.assertIsNotNone(dialog.screen_combo)
        self.assertIsNotNone(dialog.audio_check)
        self.assertIsNotNone(dialog.mic_combo)
        self.assertIsNotNone(dialog.start_btn)
        self.assertIsNotNone(dialog.cancel_btn)

        # Verify audio toggle behavior
        self.assertFalse(dialog.audio_check.isChecked())
        self.assertFalse(dialog.mic_combo.isEnabled())

        dialog.audio_check.setChecked(True)
        self.assertTrue(dialog.mic_combo.isEnabled())

        dialog.audio_check.setChecked(False)
        self.assertFalse(dialog.mic_combo.isEnabled())

        dialog.close()

    def test_recording_complete_dialog(self):
        # Create a dummy test file
        test_file = PROJECT_ROOT / "test_recording_complete.mp4"
        test_file.write_bytes(b"\x00" * 2048)
        try:
            dialog = RecordingCompleteDialog(str(test_file), duration=85)
            self.assertEqual(dialog.duration, 85)
            self.assertIsNotNone(dialog.path_edit)
            self.assertEqual(dialog.path_edit.text(), str(test_file.resolve()))
            self.assertIsNotNone(dialog.play_btn)
            self.assertIsNotNone(dialog.folder_btn)
            self.assertIsNotNone(dialog.copy_btn)

            # Test copy action
            dialog._copy_path()
            self.assertEqual(dialog.copy_btn.text(), "✓ Copied!")
            dialog.close()
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_format_toolbar_open_attachments_signal(self):
        editor = QTextEdit()
        toolbar = FormatToolbar(editor)
        received = []
        toolbar.open_attachments_requested.connect(lambda: received.append(True))
        toolbar.open_attachments_requested.emit()
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0])


if __name__ == "__main__":
    unittest.main()
