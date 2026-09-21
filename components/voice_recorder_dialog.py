from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QMessageBox, QComboBox
)
from PySide6.QtGui import QCursor

try:
    from ..media_manager import (
        VoiceRecorder, copy_to_attachments, 
        has_microphone, get_default_microphone_name,
        has_wasapi_loopback, get_default_speaker_name
    )
except ImportError:
    from media_manager import (
        VoiceRecorder, copy_to_attachments, 
        has_microphone, get_default_microphone_name,
        has_wasapi_loopback, get_default_speaker_name
    )

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES

class VoiceRecorderDialog(QDialog):
    """
    Dialog for recording live audio (call/dual channel, system audio, or microphone)
    or picking an audio file from disk.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio & Call Recording")
        self.setFixedSize(410, 315)
        self.setModal(True)
        self.result_audio_path = None

        self.theme_mgr = get_theme_manager()
        self.pal = THEME_PALETTES.get(self.theme_mgr.current_theme, THEME_PALETTES["light"])

        self.recorder = VoiceRecorder(self)
        self.recorder.duration_changed.connect(self._on_duration_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header Title
        title_label = QLabel("Audio & Call Recording", self)
        title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.pal['text_primary']};")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Audio Source Selector (Call Mode, System Audio, Mic)
        self.mode_combo = QComboBox(self)
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.pal['bg_surface']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['border']};
                selection-background-color: {self.pal['accent']};
                selection-color: {self.pal['accent_text']};
            }}
            QComboBox:disabled {{
                color: {self.pal['text_muted']};
                background-color: {self.pal['bg_main']};
            }}
        """)
        
        self.has_loopback = has_wasapi_loopback()
        self.has_mic = has_microphone()
        self.mic_name = get_default_microphone_name()
        self.spk_name = get_default_speaker_name()

        if self.has_loopback:
            self.mode_combo.addItem("🎧 Call / Meeting (Both Voices: Mic + System)", "both")
            self.mode_combo.addItem("🔊 Computer Audio Only (Callers / Media)", "system")
            self.mode_combo.addItem("🎙️ Microphone Only (Voice Memo)", "mic")
            self.mode_combo.setCurrentIndex(0)
        else:
            self.mode_combo.addItem("🎙️ Microphone Only (Voice Note)", "mic")
            self.mode_combo.setCurrentIndex(0)
        layout.addWidget(self.mode_combo)

        # Timer Display
        self.timer_label = QLabel("00:00", self)
        self.timer_label.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {self.pal['text_primary']};")
        layout.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Label showing detected devices
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.has_loopback and self.spk_name:
            mic_disp = (self.mic_name[:18] + "…") if self.mic_name and len(self.mic_name) > 18 else (self.mic_name or "Mic Ready")
            spk_disp = (self.spk_name[:18] + "…") if len(self.spk_name) > 18 else self.spk_name
            self.status_label.setText(f"🎧 System: {spk_disp} • 🎙️ Mic: {mic_disp}")
            self.status_label.setStyleSheet("font-size: 11px; color: #16A34A; font-weight: 500;")
        elif self.has_mic:
            short_name = (self.mic_name[:30] + "…") if self.mic_name and len(self.mic_name) > 30 else (self.mic_name or "Ready")
            self.status_label.setText(f"🎙 {short_name}")
            self.status_label.setStyleSheet("font-size: 11px; color: #16A34A; font-weight: 500;")
        else:
            self.status_label.setText("No microphone connected. You can still attach audio files below.")
            self.status_label.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 500;")
        layout.addWidget(self.status_label)

        # Record / Stop Button
        self.record_btn = QPushButton(self)
        self.record_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if not self.has_mic and not self.has_loopback:
            self.record_btn.setEnabled(False)
            self.record_btn.setText("🚫 No Audio Device Detected")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E2E8F0;
                    color: #94A3B8;
                    border: none;
                    border-radius: 8px;
                    padding: 9px 18px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
        else:
            self.record_btn.setText("🔴 Start Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 9px 18px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #B91C1C; }
            """)
        self.record_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_btn)

        # Wire recorder callbacks
        self.recorder.recording_finished.connect(self._on_recording_finished)
        self.recorder.recording_error.connect(self._on_recording_error)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self.pal['border']};")
        layout.addWidget(sep)

        # Bottom row: Attach Existing File & Cancel
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.choose_file_btn = QPushButton("📁 From File...", self)
        self.choose_file_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.choose_file_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.pal['btn_bg']};
                border: 1px solid {self.pal['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                color: {self.pal['btn_text']};
            }}
            QPushButton:hover {{ background-color: {self.pal['btn_hover']}; }}
        """)
        self.choose_file_btn.clicked.connect(self._choose_audio_file)
        bottom_row.addWidget(self.choose_file_btn)

        bottom_row.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet(f"border: none; color: {self.pal['text_muted']}; font-weight: 600; padding: 6px 12px;")
        self.cancel_btn.clicked.connect(self._on_cancel)
        bottom_row.addWidget(self.cancel_btn)

        layout.addLayout(bottom_row)

    def _toggle_recording(self):
        if not self.recorder.is_recording():
            mode = self.mode_combo.currentData() or "both"
            if mode == "mic" and not has_microphone():
                QMessageBox.warning(
                    self, 
                    "No Microphone", 
                    "No audio capture device (microphone) was detected on this PC.\n\nPlease connect a headset or microphone, or choose 'Computer Audio Only' to record system/call sound."
                )
                return
            # Start recording
            try:
                self.mode_combo.setEnabled(False)
                self.recorder.start_recording(mode=mode)
                self.record_btn.setText("⏹ Stop & Attach")
                self.record_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0F172A;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 8px;
                        padding: 9px 18px;
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover { background-color: #334155; }
                """)
                self.status_label.setText("🔴 Recording call & audio in progress...")
                self.choose_file_btn.setEnabled(False)
            except Exception as e:
                self.mode_combo.setEnabled(True)
                QMessageBox.warning(self, "Recording Error", f"Unable to access audio devices: {e}")
        else:
            # Stop recording and wait for finalization
            self.record_btn.setEnabled(False)
            self.record_btn.setText("⏳ Finalizing Audio...")
            self.status_label.setText("Mixing and verifying call recording...")
            self.recorder.stop_recording()

    def _on_recording_finished(self, saved_path: str):
        self.result_audio_path = saved_path
        self.accept()

    def _on_recording_error(self, err_msg: str):
        self.record_btn.setEnabled(True)
        self.record_btn.setText("🔴 Record Again")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.status_label.setText("Audio capture failed or was empty")
        self.status_label.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 500;")
        self.choose_file_btn.setEnabled(True)
        QMessageBox.warning(self, "Recording Issue", err_msg)

    def _on_duration_changed(self, seconds: int):
        mins = seconds // 60
        secs = seconds % 60
        self.timer_label.setText(f"{mins:02d}:{secs:02d}")

    def _choose_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;All Files (*.*)"
        )
        if file_path:
            copied = copy_to_attachments(file_path)
            self.result_audio_path = str(copied)
            self.accept()

    def _on_cancel(self):
        if self.recorder.is_recording():
            self.recorder.cancel_recording()
        self.reject()

    def closeEvent(self, event):
        if self.recorder.is_recording():
            self.recorder.cancel_recording()
        super().closeEvent(event)
