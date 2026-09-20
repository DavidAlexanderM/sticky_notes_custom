import os
import sys
import shutil
import uuid
import re
from pathlib import Path
from typing import Optional

import subprocess
import time
from PySide6.QtCore import QObject, Signal, QUrl, QTimer, QThread
from PySide6.QtGui import QGuiApplication, QScreen, QImage
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


class FrameCaptureThread(QThread):
    """
    Dedicated background thread capturing desktop frames via QScreen.grabWindow
    and encoding directly to H.264 MP4 using FFmpeg without DXGI permission restrictions.
    """
    frame_captured = Signal()
    capture_error = Signal(str)

    def __init__(self, screen: Optional[QScreen], output_file: str, fps: int = 15, parent=None):
        super().__init__(parent)
        self.screen = screen or QGuiApplication.primaryScreen()
        self.output_file = output_file
        self.fps = fps
        self.running = False
        self.proc = None
        self.frame_count = 0
        self.error_message = None

    def run(self):
        try:
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            geo = self.screen.geometry() if self.screen else QGuiApplication.primaryScreen().geometry()
            w = geo.width() - (geo.width() % 2)
            h = geo.height() - (geo.height() % 2)

            cmd = [
                ffmpeg_bin, "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-s", f"{w}x{h}",
                "-pix_fmt", "bgra",
                "-r", str(self.fps),
                "-i", "-",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-movflags", "+faststart",
                self.output_file
            ]

            creationflags = 0x08000000 if sys.platform == "win32" else 0
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags
            )
            self.running = True
            interval = 1.0 / self.fps

            while self.running:
                t0 = time.time()
                pix = self.screen.grabWindow(0, 0, 0, w, h)
                img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                try:
                    self.proc.stdin.write(img.constBits().tobytes())
                    self.frame_count += 1
                except Exception as e:
                    self.error_message = str(e)
                    break

                elapsed = time.time() - t0
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            if self.proc and self.proc.stdin:
                try:
                    self.proc.stdin.close()
                    self.proc.wait(timeout=6)
                except Exception:
                    self.proc.kill()
        except Exception as e:
            self.error_message = str(e)
            self.capture_error.emit(str(e))

    def stop(self):
        self.running = False
        self.wait(timeout=6000)


class ScreenRecorder(QObject):
    """
    High-performance desktop screen recorder.
    Combines QScreen frame capture with hardware/FFmpeg H.264 encoding to bypass
    DXGI permission barriers, ensuring smooth, crash-free video recording on all Windows setups.
    """
    duration_changed = Signal(int)       # Emits elapsed seconds
    recording_finished = Signal(str)     # Emits path to recorded MP4 file
    recording_error = Signal(str)        # Emits error description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.capture_thread = None
        self.voice_recorder = None
        self._temp_video_path = None
        self._temp_audio_path = None
        self.output_file_path = None
        self._include_audio = False
        self._is_recording = False
        self._extension = ".mp4"

        # Qt Fallback engine components
        self.session = QMediaCaptureSession(self)
        self.screen_capture = QScreenCapture(self)
        self.audio_input = None
        self.recorder = QMediaRecorder(self)
        self.session.setScreenCapture(self.screen_capture)
        self.session.setRecorder(self.recorder)

        # Elapsed timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.elapsed_seconds = 0

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self._finalize_and_verify)

    def start_recording(self, screen: Optional[QScreen] = None, include_audio: bool = False, audio_device_name: Optional[str] = None) -> str:
        """Starts recording screen video and returns target file path."""
        if screen is None:
            screens = get_available_screens()
            screen = screens[0] if screens else QGuiApplication.primaryScreen()

        self._include_audio = include_audio
        unique_name = f"screen_recording_{uuid.uuid4().hex[:8]}.mp4"
        target_path = get_attachments_dir() / unique_name
        self.output_file_path = str(target_path)
        self.elapsed_seconds = 0

        ffmpeg_bin = shutil.which("ffmpeg")

        if ffmpeg_bin:
            # Primary Engine: FrameCaptureThread (100% reliable, no DXGI access errors)
            if include_audio:
                self._temp_video_path = str(get_attachments_dir() / f"temp_vid_{uuid.uuid4().hex[:8]}.mp4")
                self._temp_audio_path = str(get_attachments_dir() / f"temp_aud_{uuid.uuid4().hex[:8]}.wav")
                video_out = self._temp_video_path

                self.voice_recorder = VoiceRecorder(self)
                self.voice_recorder.output_file_path = self._temp_audio_path
                self.voice_recorder.recorder.setOutputLocation(QUrl.fromLocalFile(self._temp_audio_path))
                self.voice_recorder.recorder.record()
            else:
                video_out = self.output_file_path
                self._temp_video_path = None
                self._temp_audio_path = None

            self.capture_thread = FrameCaptureThread(screen, video_out, fps=15, parent=self)
            self.capture_thread.start()
        else:
            # Fallback Engine: Qt QScreenCapture
            m_format = QMediaFormat()
            m_format.setFileFormat(QMediaFormat.FileFormat.MPEG4)
            m_format.setVideoCodec(QMediaFormat.VideoCodec.H264)
            if include_audio:
                m_format.setAudioCodec(QMediaFormat.AudioCodec.AAC)
                if not self.audio_input:
                    self.audio_input = QAudioInput(self)
                    self.session.setAudioInput(self.audio_input)
            self.recorder.setMediaFormat(m_format)
            self.screen_capture.setScreen(screen)
            self.recorder.setOutputLocation(QUrl.fromLocalFile(self.output_file_path))
            self.screen_capture.start()
            self.recorder.record()

        self._is_recording = True
        self.timer.start()
        self.duration_changed.emit(0)
        return self.output_file_path

    def stop_recording(self):
        """Stops active recording, muxes audio if needed, and finalizes MP4 file."""
        if not self._is_recording:
            return
        self.timer.stop()
        self._is_recording = False

        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread = None

            if self._include_audio and self.voice_recorder:
                try:
                    self.voice_recorder.recorder.stop()
                    time.sleep(0.3)
                except Exception:
                    pass

            if self._include_audio and self._temp_video_path and self._temp_audio_path:
                ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
                creationflags = 0x08000000 if sys.platform == "win32" else 0
                has_audio = Path(self._temp_audio_path).exists() and Path(self._temp_audio_path).stat().st_size > 350
                if has_audio and Path(self._temp_video_path).exists():
                    mux_cmd = [
                        ffmpeg_bin, "-y",
                        "-i", self._temp_video_path,
                        "-i", self._temp_audio_path,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        "-movflags", "+faststart",
                        self.output_file_path
                    ]
                    subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags, timeout=10)
                elif Path(self._temp_video_path).exists():
                    shutil.move(self._temp_video_path, self.output_file_path)

                for p in (self._temp_video_path, self._temp_audio_path):
                    if p and Path(p).exists():
                        try: os.remove(p)
                        except Exception: pass
                self._temp_video_path = None
                self._temp_audio_path = None

            self._finalize_and_verify()
        else:
            # Fallback Qt engine
            self.recorder.stop()
            self.screen_capture.stop()
            self._flush_timer.start(2500)

    def cancel_recording(self):
        """Cancels recording and cleans up temporary files."""
        self.timer.stop()
        self._flush_timer.stop()
        self._is_recording = False
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread = None
        if self.voice_recorder:
            try: self.voice_recorder.recorder.stop()
            except Exception: pass
        if hasattr(self, 'recorder'):
            self.recorder.stop()
            self.screen_capture.stop()
        for p in (self.output_file_path, self._temp_video_path, self._temp_audio_path):
            if p and Path(p).exists():
                try: os.remove(p)
                except Exception: pass
        self.output_file_path = None

    def _finalize_and_verify(self):
        if not self.output_file_path:
            self.recording_error.emit("No output file was specified for screen recording.")
            return

        out_path = Path(self.output_file_path)
        if not out_path.exists():
            self.recording_error.emit(
                "Recording file was not created by the media system.\n\n"
                "Please verify that desktop capture permissions are enabled in Windows."
            )
            return

        size = out_path.stat().st_size
        if size <= 500:
            try:
                os.remove(self.output_file_path)
            except Exception:
                pass
            self.recording_error.emit(
                "Screen recording captured 0 frames or was stopped too quickly (under 1 second).\n\n"
                "Please record for at least 2-3 seconds."
            )
            return

        self.recording_finished.emit(self.output_file_path)

    def is_recording(self) -> bool:
        return self._is_recording

    def _on_tick(self):
        self.elapsed_seconds += 1
        self.duration_changed.emit(self.elapsed_seconds)

