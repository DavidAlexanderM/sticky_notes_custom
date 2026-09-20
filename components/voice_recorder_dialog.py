from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame, QMessageBox
)
from PySide6.QtGui import QCursor

try:
    from ..media_manager import (
        VoiceRecorder, copy_to_attachments, 
        has_microphone, get_default_microphone_name
    )
except ImportError:
    from media_manager import (
        VoiceRecorder, copy_to_attachments, 
        has_microphone, get_default_microphone_name
    )

class VoiceRecorderDialog(QDialog):
    """
    Dialog for recording live audio from microphone or picking an audio file from disk.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Recording & Audio")
        self.setFixedSize(380, 270)
        self.setModal(True)
        self.result_audio_path = None

        self.recorder = VoiceRecorder(self)
        self.recorder.duration_changed.connect(self._on_duration_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        title_label = QLabel("Voice Note", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Timer Display
        self.timer_label = QLabel("00:00", self)
        self.timer_label.setStyleSheet("font-size: 32px; font-weight: 700; color: #334155;")
        layout.addWidget(self.timer_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Label & Microphone Detection
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Record / Stop Button
        self.record_btn = QPushButton(self)
        self.record_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        layout.addWidget(self.record_btn)

        # Check for microphone availability
        self.has_mic = has_microphone()
        self.mic_name = get_default_microphone_name()

        if not self.has_mic:
            self.record_btn.setEnabled(False)
            self.record_btn.setText("🚫 No Microphone Detected")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E2E8F0;
                    color: #94A3B8;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
            self.status_label.setText("No microphone connected. You can still attach audio files below.")
            self.status_label.setStyleSheet("font-size: 11px; color: #DC2626; font-weight: 500;")
        else:
            self.record_btn.setText("🔴 Start Recording")
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
            short_name = (self.mic_name[:30] + "...") if self.mic_name and len(self.mic_name) > 30 else (self.mic_name or "Ready")
            self.status_label.setText(f"🎙 {short_name}")
            self.status_label.setStyleSheet("font-size: 11px; color: #16A34A; font-weight: 500;")

        self.record_btn.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_btn)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(0, 0, 0, 0.08);")
        layout.addWidget(sep)

        # Bottom row: Attach Existing File & Cancel
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.choose_file_btn = QPushButton("📁 From File...", self)
        self.choose_file_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.choose_file_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                color: #334155;
            }
            QPushButton:hover { background-color: rgba(0, 0, 0, 0.05); }
        """)
        self.choose_file_btn.clicked.connect(self._choose_audio_file)
        bottom_row.addWidget(self.choose_file_btn)

        bottom_row.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("border: none; color: #64748B; font-weight: 600; padding: 6px 12px;")
        self.cancel_btn.clicked.connect(self._on_cancel)
        bottom_row.addWidget(self.cancel_btn)

        layout.addLayout(bottom_row)

    def _toggle_recording(self):
        if not self.recorder.is_recording():
            if not has_microphone():
                QMessageBox.warning(
                    self, 
                    "No Microphone", 
                    "No audio capture device (microphone) was detected on this PC.\n\nPlease connect a headset or microphone, or use the 'From File' button below to attach an audio file."
                )
                return
            # Start recording
            try:
                self.recorder.start_recording()
                self.record_btn.setText("⏹ Stop & Attach")
                self.record_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #0F172A;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 8px;
                        padding: 10px 20px;
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover { background-color: #334155; }
                """)
                self.status_label.setText("Recording in progress...")
                self.choose_file_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.warning(self, "Recording Error", f"Unable to access microphone: {e}")
        else:
            # Stop recording and attach
            saved_path = self.recorder.stop_recording()
            self.result_audio_path = saved_path
            self.accept()

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
