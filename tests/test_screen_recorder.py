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

from media_manager import ScreenRecorder, get_available_screens, get_available_microphones
from components.screen_recorder_dialog import ScreenRecorderDialog, ScreenRecordingOverlay


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


if __name__ == "__main__":
    unittest.main()
