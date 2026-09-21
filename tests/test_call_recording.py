"""
test_call_recording.py - Automated test suite for Two-Way Call Recording and WASAPI loopback.
Verifies WasapiAudioRecorder engine, audio mode dispatching, and dual-channel UI controls.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

# Ensure QApplication exists for GUI testing
app = QApplication.instance()
if app is None:
    app = QApplication([])

import media_manager
from media_manager import (
    WasapiAudioRecorder, VoiceRecorder, has_wasapi_loopback, 
    get_default_speaker_name, has_microphone, get_default_microphone_name
)
from components.voice_recorder_dialog import VoiceRecorderDialog
from components.screen_recorder_dialog import ScreenRecorderDialog


class TestCallRecording(unittest.TestCase):
    """Test suite for call audio capture and loopback recording."""

    def test_wasapi_device_detection_helpers(self):
        """Verify WASAPI loopback and microphone detection functions return expected types."""
        has_loop = has_wasapi_loopback()
        self.assertIsInstance(has_loop, bool)

        spk_name = get_default_speaker_name()
        if has_loop:
            self.assertIsNotNone(spk_name)
            self.assertIsInstance(spk_name, str)
            self.assertNotIn("[Loopback]", spk_name)

        has_mic = has_microphone()
        self.assertIsInstance(has_mic, bool)

        mic_name = get_default_microphone_name()
        if has_mic:
            self.assertIsNotNone(mic_name)
            self.assertIsInstance(mic_name, str)

    def test_wasapi_recorder_initialization(self):
        """Verify WasapiAudioRecorder initializes cleanly with all signals and attributes."""
        recorder = WasapiAudioRecorder()
        self.assertFalse(recorder.is_recording())
        self.assertEqual(recorder.elapsed_seconds, 0)
        self.assertIsNotNone(recorder.timer)
        self.assertIsNotNone(recorder.duration_changed)
        self.assertIsNotNone(recorder.recording_finished)
        self.assertIsNotNone(recorder.recording_error)

    def test_voice_recorder_wasapi_integration(self):
        """Verify VoiceRecorder initializes with both WASAPI engine and Qt fallback."""
        recorder = VoiceRecorder()
        self.assertIsNotNone(recorder.wasapi_recorder)
        self.assertIsNotNone(recorder.session)
        self.assertIsNotNone(recorder.recorder)
        self.assertIsNotNone(recorder.audio_input)
        self.assertFalse(recorder.is_recording())

    def test_voice_recorder_dialog_mode_options(self):
        """Verify VoiceRecorderDialog UI contains call recording modes and status."""
        dialog = VoiceRecorderDialog()
        self.assertIsNotNone(dialog.mode_combo)
        self.assertGreater(dialog.mode_combo.count(), 0)

        # Check that 'both' mode is available when loopback is active
        if dialog.has_loopback:
            modes = [dialog.mode_combo.itemData(i) for i in range(dialog.mode_combo.count())]
            self.assertIn("both", modes)
            self.assertIn("system", modes)
            self.assertIn("mic", modes)
            self.assertEqual(dialog.mode_combo.currentData(), "both")
        else:
            self.assertEqual(dialog.mode_combo.currentData(), "mic")

        self.assertIsNotNone(dialog.record_btn)
        self.assertIsNotNone(dialog.status_label)
        dialog.close()

    def test_screen_recorder_dialog_audio_modes(self):
        """Verify ScreenRecorderDialog contains call recording audio options."""
        dialog = ScreenRecorderDialog()
        self.assertIsNotNone(dialog.audio_check)
        self.assertIsNotNone(dialog.audio_mode_combo)

        # Toggling audio checkbox should enable/disable mode combo
        dialog.audio_check.setChecked(False)
        self.assertFalse(dialog.audio_mode_combo.isEnabled())
        dialog.audio_check.setChecked(True)
        self.assertTrue(dialog.audio_mode_combo.isEnabled())

        if has_wasapi_loopback():
            modes = [dialog.audio_mode_combo.itemData(i) for i in range(dialog.audio_mode_combo.count())]
            self.assertIn("both", modes)
            self.assertIn("system", modes)
            self.assertIn("mic", modes)
        dialog.close()

    def test_wasapi_recorder_cancel_cleans_resources(self):
        """Verify cancel_recording safely resets state and cleans resources."""
        recorder = WasapiAudioRecorder()
        recorder._is_recording = True
        recorder.cancel_recording()
        self.assertFalse(recorder.is_recording())
        self.assertIsNone(recorder.output_file_path)


if __name__ == "__main__":
    unittest.main()
