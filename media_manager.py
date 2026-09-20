import os
import sys
import shutil
import uuid
import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtGui import QGuiApplication, QScreen
from PySide6.QtMultimedia import (
    QMediaRecorder, QAudioInput, QMediaCaptureSession, 
    QMediaFormat, QMediaDevices, QScreenCapture
)

def get_available_microphones() -> list[str]:
    """Returns a list of connected microphone descriptions."""
    return [d.description() for d in QMediaDevices.audioInputs() if not d.isNull()]

def has_microphone() -> bool:
    """Checks if at least one audio capturing device (microphone) is available."""
    inputs = QMediaDevices.audioInputs()
    default_dev = QMediaDevices.defaultAudioInput()
    return len(inputs) > 0 and not default_dev.isNull()

def get_default_microphone_name() -> Optional[str]:
    """Returns the name of the default microphone or None if none found."""
    default_dev = QMediaDevices.defaultAudioInput()
    if not default_dev.isNull():
        return default_dev.description()
    return None

from security import is_safe_attachment, sanitize_filename

def get_attachments_dir() -> Path:
    """Returns the persistent directory where attachments are stored."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
    else:
        base_dir = Path(__file__).resolve().parent
    
    attachments_dir = (base_dir / "attachments").resolve()
    attachments_dir.mkdir(parents=True, exist_ok=True)
    return attachments_dir

def copy_to_attachments(source_path: str) -> Path:
    """
    Copies a media file to the attachments directory with a sanitized, collision-free filename.
    Guarantees path containment and rejects unsafe executable/script files.
    Returns the Path to the copied file.
    """
    source = Path(source_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    # Enforce security validation
    is_safe, reason = is_safe_attachment(source)
    if not is_safe:
        raise ValueError(reason)

    # Sanitize stem and suffix
    unique_id = uuid.uuid4().hex[:8]
    clean_stem = f"{source.stem[:25]}_{unique_id}"
    safe_name = sanitize_filename(clean_stem, source.suffix)

    attachments_dir = get_attachments_dir()
    dest_path = (attachments_dir / safe_name).resolve()

    # Strict path traversal containment assertion
    if not dest_path.is_relative_to(attachments_dir):
        raise PermissionError("Path traversal violation: Target location is outside the attachments directory.")

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

        # Configure reliable audio format
        m_format = QMediaFormat()
        supported_formats = m_format.supportedFileFormats(QMediaFormat.ConversionMode.Encode)
        if QMediaFormat.FileFormat.Wave in supported_formats:
            m_format.setFileFormat(QMediaFormat.FileFormat.Wave)
            m_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
            self._extension = ".wav"
        else:
            m_format.setFileFormat(QMediaFormat.FileFormat.Mpeg4Audio)
            m_format.setAudioCodec(QMediaFormat.AudioCodec.AAC)
            self._extension = ".m4a"
        self.recorder.setMediaFormat(m_format)

        # State tracking
        self._stopping = False
        self.recorder.recorderStateChanged.connect(self._on_recorder_state_changed)
        self.recorder.errorOccurred.connect(self._on_recorder_error)

        # Elapsed timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.elapsed_seconds = 0
        self.output_file_path = None

        # Fallback flush timer in case stopped state signal is delayed
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._finalize_and_verify)

    def start_recording(self) -> str:
        """Starts recording audio and returns the target file path."""
        unique_name = f"voice_note_{uuid.uuid4().hex[:8]}{self._extension}"
        target_path = get_attachments_dir() / unique_name
        self.output_file_path = str(target_path)
        self._stopping = False

        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.output_file_path))
        self.recorder.record()

        self.elapsed_seconds = 0
        self.timer.start()
        self.duration_changed.emit(0)
        return self.output_file_path

    def stop_recording(self):
        """Asynchronously stops recording and signals when file is finalized."""
        self.timer.stop()
        self._stopping = True
        self.recorder.stop()
        # Set 1500ms safety timer in case state signal doesn't fire
        self._flush_timer.start(1500)

    def _on_recorder_state_changed(self, state):
        if state == QMediaRecorder.RecorderState.StoppedState and self._stopping:
            self._flush_timer.stop()
            self._finalize_and_verify()

    def _on_recorder_error(self, error, error_string):
        self.recording_error.emit(f"Audio recording failed: {error_string}")

    def _finalize_and_verify(self):
        if not self._stopping:
            return
        self._stopping = False

        if not self.output_file_path:
            self.recording_error.emit("No output file was specified.")
            return

        out_path = Path(self.output_file_path)
        if not out_path.exists():
            self.recording_error.emit("Recording file was not created by the media system.")
            return

        size = out_path.stat().st_size
        # Minimum valid audio container size (avoiding 0-byte or empty header files)
        if size <= 350:
            try:
                os.remove(self.output_file_path)
            except Exception:
                pass
            self.recording_error.emit(
                "No audio data was captured from your microphone (0 bytes recorded).\n\n"
                "Please verify that your microphone/headset is plugged in, not muted in Windows, "
                "and that 'Microphone access for desktop apps' is enabled in Windows Privacy Settings."
            )
            return

        self.recording_finished.emit(self.output_file_path)

    def cancel_recording(self):
        """Cancels recording and cleans up temporary file."""
        self.timer.stop()
        self._flush_timer.stop()
        self._stopping = False
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


def get_available_screens() -> list[QScreen]:
    """Returns a list of connected QScreen monitor display objects."""
    app = QGuiApplication.instance()
    if app:
        return QGuiApplication.screens()
    return []


class ScreenRecorder(QObject):
    """
    Hardware-accelerated desktop screen recorder using Qt6's QScreenCapture & QMediaRecorder.
    Supports multi-monitor selection, optional microphone narration, and H.264 MP4 encoding.
    """
    duration_changed = Signal(int)       # Emits elapsed seconds
    recording_finished = Signal(str)     # Emits path to recorded MP4 file
    recording_error = Signal(str)        # Emits error description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = QMediaCaptureSession(self)
        self.screen_capture = QScreenCapture(self)
        self.audio_input = None
        self.recorder = QMediaRecorder(self)

        self.session.setScreenCapture(self.screen_capture)
        self.session.setRecorder(self.recorder)

        # Configure video media format (H.264 MP4 preferred)
        m_format = QMediaFormat()
        supported_formats = m_format.supportedFileFormats(QMediaFormat.ConversionMode.Encode)
        if QMediaFormat.FileFormat.MPEG4 in supported_formats:
            m_format.setFileFormat(QMediaFormat.FileFormat.MPEG4)
            video_codecs = m_format.supportedVideoCodecs(QMediaFormat.ConversionMode.Encode)
            if QMediaFormat.VideoCodec.H264 in video_codecs:
                m_format.setVideoCodec(QMediaFormat.VideoCodec.H264)
            elif QMediaFormat.VideoCodec.MPEG4 in video_codecs:
                m_format.setVideoCodec(QMediaFormat.VideoCodec.MPEG4)
            m_format.setAudioCodec(QMediaFormat.AudioCodec.AAC)
            self._extension = ".mp4"
        elif QMediaFormat.FileFormat.WMV in supported_formats:
            m_format.setFileFormat(QMediaFormat.FileFormat.WMV)
            self._extension = ".wmv"
        elif QMediaFormat.FileFormat.Matroska in supported_formats:
            m_format.setFileFormat(QMediaFormat.FileFormat.Matroska)
            self._extension = ".mkv"
        else:
            self._extension = ".mp4"

        self.recorder.setMediaFormat(m_format)

        # State tracking
        self._stopping = False
        self.recorder.recorderStateChanged.connect(self._on_recorder_state_changed)
        self.recorder.errorOccurred.connect(self._on_recorder_error)

        # Elapsed timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.elapsed_seconds = 0
        self.output_file_path = None

        # Fallback safety flush timer
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._finalize_and_verify)

    def start_recording(self, screen: Optional[QScreen] = None, include_audio: bool = False, audio_device_name: Optional[str] = None) -> str:
        """Starts recording screen video and returns the target file path."""
        # Set screen to capture
        if screen is None:
            screens = get_available_screens()
            screen = screens[0] if screens else None

        if screen:
            self.screen_capture.setScreen(screen)

        # Set optional audio input
        if include_audio:
            if not self.audio_input:
                self.audio_input = QAudioInput(self)
                self.session.setAudioInput(self.audio_input)
            if audio_device_name:
                devices = QMediaDevices.audioInputs()
                for d in devices:
                    if d.description() == audio_device_name:
                        self.audio_input.setDevice(d)
                        break
        else:
            if self.audio_input:
                self.session.setAudioInput(None)
                self.audio_input.deleteLater()
                self.audio_input = None

        unique_name = f"screen_recording_{uuid.uuid4().hex[:8]}{self._extension}"
        target_path = get_attachments_dir() / unique_name
        self.output_file_path = str(target_path)
        self._stopping = False

        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.output_file_path))
        self.screen_capture.start()
        self.recorder.record()

        self.elapsed_seconds = 0
        self.timer.start()
        self.duration_changed.emit(0)
        return self.output_file_path

    def stop_recording(self):
        """Asynchronously stops screen recording and finalizes MP4 file."""
        self.timer.stop()
        self._stopping = True
        self.recorder.stop()
        self.screen_capture.stop()
        self._flush_timer.start(2500)

    def _on_recorder_state_changed(self, state):
        if state == QMediaRecorder.RecorderState.StoppedState and self._stopping:
            self._flush_timer.stop()
            self._finalize_and_verify()

    def _on_recorder_error(self, error, error_string):
        self.recording_error.emit(f"Screen recording failed: {error_string}")

    def _finalize_and_verify(self):
        if not self._stopping:
            return
        self._stopping = False

        if not self.output_file_path:
            self.recording_error.emit("No output file was specified for screen recording.")
            return

        out_path = Path(self.output_file_path)
        if not out_path.exists():
            self.recording_error.emit("Screen recording file was not created by the media system.")
            return

        size = out_path.stat().st_size
        if size <= 1000:
            try:
                os.remove(self.output_file_path)
            except Exception:
                pass
            self.recording_error.emit(
                "Screen recording captured 0 frames or was stopped too quickly.\n\n"
                "Please ensure desktop capture permissions are allowed."
            )
            return

        self.recording_finished.emit(self.output_file_path)

    def cancel_recording(self):
        """Cancels recording and cleans up staging file."""
        self.timer.stop()
        self._flush_timer.stop()
        self._stopping = False
        self.recorder.stop()
        self.screen_capture.stop()
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

