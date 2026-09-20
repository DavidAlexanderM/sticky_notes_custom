"""
screen_recorder_dialog.py - Desktop Screen Recording Interface for Sticky Notes.
Features display monitor selection, optional microphone narration, and a floating
HUD overlay controller during active screen capture.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QFrame, QMessageBox
)
from PySide6.QtGui import QCursor, QScreen

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES
    from ..icons import get_themed_icon
    from ..media_manager import ScreenRecorder, get_available_screens, get_available_microphones
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES
    from icons import get_themed_icon
    from media_manager import ScreenRecorder, get_available_screens, get_available_microphones


class ScreenRecordingOverlay(QWidget):
    """
    Compact, draggable floating HUD widget that stays on top during active screen capture.
    Provides live timer feedback, stop, and cancel controls without obstructing the desktop.
    """
    stop_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = QPoint()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)

        # Container pill
        self.pill = QFrame(self)
        self.pill.setStyleSheet("""
            QFrame {
                background-color: #1E1F20;
                border: 1px solid #444746;
                border-radius: 18px;
                padding: 4px 12px;
            }
        """)
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(8, 4, 8, 4)
        pill_layout.setSpacing(10)

        # Pulsing REC indicator
        self.rec_lbl = QLabel("🔴 REC", self.pill)
        self.rec_lbl.setStyleSheet("color: #FF5252; font-weight: 700; font-size: 12px; background: transparent;")
        pill_layout.addWidget(self.rec_lbl)

        # Elapsed time display
        self.time_lbl = QLabel("00:00", self.pill)
        self.time_lbl.setStyleSheet("color: #FFFFFF; font-weight: 600; font-size: 13px; font-family: monospace; background: transparent;")
        pill_layout.addWidget(self.time_lbl)

        # Stop recording button
        self.stop_btn = QPushButton("⏹ Stop", self.pill)
        self.stop_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        pill_layout.addWidget(self.stop_btn)

        # Cancel button
        self.cancel_btn = QPushButton("✕", self.pill)
        self.cancel_btn.setToolTip("Cancel recording (discard)")
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #333537;
                color: #E3E3E3;
                border: none;
                border-radius: 12px;
                width: 24px;
                height: 24px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #444746;
                color: #FFFFFF;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
        pill_layout.addWidget(self.cancel_btn)

        layout.addWidget(self.pill)
        self.adjustSize()

    def update_time(self, seconds: int):
        m, s = divmod(seconds, 60)
        self.time_lbl.setText(f"{m:02d}:{s:02d}")

    # Draggable floating HUD support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class ScreenRecorderDialog(QDialog):
    """
    Setup dialog and orchestrator for desktop screen recording.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Desktop Screen")
        self.setFixedSize(440, 320)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])

        self.recorder = ScreenRecorder(self)
        self.overlay: Optional[ScreenRecordingOverlay] = None
        self.result_video_path: Optional[str] = None

        self.recorder.duration_changed.connect(self._on_duration_changed)
        self.recorder.recording_finished.connect(self._on_recording_finished)
        self.recorder.recording_error.connect(self._on_recording_error)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(get_themed_icon("video", role="primary", theme=self.theme, size=26).pixmap(26, 26))
        header.addWidget(icon_lbl)

        title_lbl = QLabel("Desktop Screen Recorder", self)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Card container
        card = QFrame(self)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.pal['bg_surface']};
                border: 1px solid {self.pal['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # Display selection
        disp_lbl = QLabel("<b>Select Display / Screen:</b>", card)
        disp_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_primary']};")
        card_layout.addWidget(disp_lbl)

        self.screen_combo = QComboBox(card)
        self.screens = get_available_screens()
        for idx, screen in enumerate(self.screens):
            geo = screen.geometry()
            name = screen.name() or f"Display {idx + 1}"
            self.screen_combo.addItem(f"{name} ({geo.width()}x{geo.height()})", screen)
        self.screen_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 5px 8px;
            }}
        """)
        card_layout.addWidget(self.screen_combo)

        # Audio narration toggle
        self.audio_check = QCheckBox("🎙️ Record Microphone Narration", card)
        self.audio_check.setStyleSheet(f"color: {self.pal['text_primary']}; font-size: 12px;")
        self.audio_check.toggled.connect(self._on_audio_toggled)
        card_layout.addWidget(self.audio_check)

        self.mic_combo = QComboBox(card)
        mics = get_available_microphones()
        if mics:
            for mic in mics:
                self.mic_combo.addItem(mic)
        else:
            self.mic_combo.addItem("Default Microphone")
        self.mic_combo.setEnabled(False)
        self.mic_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 5px 8px;
            }}
            QComboBox:disabled {{
                color: {self.pal['text_muted']};
                background: {self.pal['bg_main']};
            }}
        """)
        card_layout.addWidget(self.mic_combo)

        layout.addWidget(card)

        # Action buttons
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("SelectModeButton")
        self.cancel_btn.setFixedSize(85, 32)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        btn_row.addStretch()

        self.start_btn = QPushButton("🔴 Start Recording", self)
        self.start_btn.setObjectName("NewNoteButton")
        self.start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_btn.setFixedHeight(32)
        self.start_btn.clicked.connect(self._start_capture)
        btn_row.addWidget(self.start_btn)

        layout.addLayout(btn_row)

    def _on_audio_toggled(self, checked: bool):
        self.mic_combo.setEnabled(checked)

    def _start_capture(self):
        selected_screen = self.screen_combo.currentData()
        include_audio = self.audio_check.isChecked()
        mic_device = self.mic_combo.currentText() if include_audio else None

        try:
            self.recorder.start_recording(
                screen=selected_screen,
                include_audio=include_audio,
                audio_device_name=mic_device
            )
        except Exception as e:
            QMessageBox.critical(self, "Recording Error", f"Failed to start screen capture: {str(e)}")
            return

        # Hide setup dialog
        self.hide()

        # Launch floating overlay
        self.overlay = ScreenRecordingOverlay()
        self.overlay.stop_clicked.connect(self._stop_capture)
        self.overlay.cancel_clicked.connect(self._cancel_capture)

        # Position overlay at bottom-right or top-center of the selected screen
        if selected_screen:
            geo = selected_screen.geometry()
            x = geo.x() + geo.width() - 250
            y = geo.y() + geo.height() - 100
            self.overlay.move(x, y)
        else:
            self.overlay.move(100, 100)

        self.overlay.show()

    def _stop_capture(self):
        if self.overlay:
            self.overlay.stop_btn.setEnabled(False)
            self.overlay.stop_btn.setText("Finalizing...")
        self.recorder.stop_recording()

    def _cancel_capture(self):
        self.recorder.cancel_recording()
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.reject()

    def _on_duration_changed(self, seconds: int):
        if self.overlay:
            self.overlay.update_time(seconds)

    def _on_recording_finished(self, file_path: str):
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.result_video_path = file_path
        self.accept()

    def _on_recording_error(self, error_msg: str):
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        self.show()
        QMessageBox.warning(self, "Recording Notice", error_msg)
