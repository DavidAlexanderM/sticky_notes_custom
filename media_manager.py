import os
import sys
import shutil
import uuid
import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtMultimedia import (
    QMediaRecorder, QAudioInput, QMediaCaptureSession, 
    QMediaFormat
)

def get_attachments_dir() -> Path:
    """Returns the persistent directory where attachments are stored."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
    else:
        base_dir = Path(__file__).resolve().parent
    
    attachments_dir = base_dir / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    return attachments_dir

def copy_to_attachments(source_path: str) -> Path:
    """
    Copies a media file to the attachments directory with a sanitized, collision-free filename.
    Returns the Path to the copied file.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    # Sanitize stem
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', source.stem)[:30]
    unique_id = uuid.uuid4().hex[:8]
    target_filename = f"{clean_stem}_{unique_id}{source.suffix.lower()}"
    
    dest_path = get_attachments_dir() / target_filename
    shutil.copy2(source, dest_path)
    return dest_path

class VoiceRecorder(QObject):
    """
    Helper class for recording voice notes from the default system microphone.
    """
    duration_changed = Signal(int)       # Emits elapsed seconds
    recording_finished = Signal(str)     # Emits path to recorded file
    recording_error = Signal(str)        # Emits error description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = QMediaCaptureSession(self)
        self.audio_input = QAudioInput(self)
        self.recorder = QMediaRecorder(self)

        self.session.setAudioInput(self.audio_input)
        self.session.setRecorder(self.recorder)

        # Configure high quality compressed audio format
        m_format = QMediaFormat()
        m_format.setFileFormat(QMediaFormat.FileFormat.MPEG4)
        m_format.setAudioCodec(QMediaFormat.AudioCodec.AAC)
        self.recorder.setMediaFormat(m_format)

        # Elapsed timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.elapsed_seconds = 0
        self.output_file_path = None

    def start_recording(self) -> str:
        """Starts recording audio and returns the target file path."""
        unique_name = f"voice_note_{uuid.uuid4().hex[:8]}.m4a"
        target_path = get_attachments_dir() / unique_name
        self.output_file_path = str(target_path)

        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.output_file_path))
        self.recorder.record()

        self.elapsed_seconds = 0
        self.timer.start()
        self.duration_changed.emit(0)
        return self.output_file_path

    def stop_recording(self) -> Optional[str]:
        """Stops recording and returns the path to the saved audio file."""
        self.timer.stop()
        self.recorder.stop()
        if self.output_file_path and Path(self.output_file_path).exists():
            self.recording_finished.emit(self.output_file_path)
            return self.output_file_path
        return self.output_file_path

    def cancel_recording(self):
        """Cancels recording and cleans up temporary file."""
        self.timer.stop()
        self.recorder.stop()
        if self.output_file_path and Path(self.output_file_path).exists():
            try:
                os.remove(self.output_file_path)
            except Exception:
                pass
        self.output_file_path = None

    def is_recording(self) -> bool:
        return self.recorder.recorderState() == QMediaRecorder.RecorderState.RecordingState

    def _on_tick(self):
        self.elapsed_seconds += 1
        self.duration_changed.emit(self.elapsed_seconds)
