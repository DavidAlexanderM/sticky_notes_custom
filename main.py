import sys
from pathlib import Path

# Ensure package directory is in sys.path for direct script execution
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QVBoxLayout, QStackedWidget
)
from PySide6.QtGui import QIcon, QFont

try:
    from . import database
    from . import version
    from .styles import APP_STYLESHEET
    from .theme_manager import get_theme_manager
    from .views.grid_view import StickyNotesGridView
    from .views.editor_view import NoteEditorView
except ImportError:
    import database
    import version
    from styles import APP_STYLESHEET
    from theme_manager import get_theme_manager
    from views.grid_view import StickyNotesGridView
    from views.editor_view import NoteEditorView


class MainWindow(QMainWindow):
    """
    Main application single-window container.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(version.APP_TITLE)
        self.resize(920, 680)
        self.setMinimumSize(640, 480)

        # Initialize Database
        database.init_db()

        # Central Widget & Stacked Views
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget(central_widget)
        root_layout.addWidget(self.stacked_widget)

        # View 0: Grid of Sticky Notes
        self.grid_view = StickyNotesGridView(self)
        self.grid_view.open_note_requested.connect(self._open_note_editor)
        self.stacked_widget.addWidget(self.grid_view)

        # View 1: Note Editor
        self.editor_view = NoteEditorView(self)
        self.editor_view.back_requested.connect(self._return_to_grid)
        self.stacked_widget.addWidget(self.editor_view)

        # Load notes on launch
        self.grid_view.load_notes()

        # Check for software updates silently in background 3.5 seconds after launch
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3500, self._check_updates_silent)

    def _check_updates_silent(self):
        try:
            from updater import UpdateCheckWorker
            self._bg_update_worker = UpdateCheckWorker(parent=self)
            self._bg_update_worker.check_finished.connect(self._on_bg_update_detected)
            self._bg_update_worker.start()
        except Exception:
            pass

    def _on_bg_update_detected(self, has_update: bool, release_info: dict):
        if has_update and hasattr(self, 'grid_view') and hasattr(self.grid_view, 'show_update_available_banner'):
            self.grid_view.show_update_available_banner(release_info)

    def _open_note_editor(self, note_id: str):
        """Swaps view to editor for the selected note."""
        self.editor_view.load_note(note_id)
        self.stacked_widget.setCurrentIndex(1)

    def _return_to_grid(self):
        """Returns to the sticky notes board and refreshes cards."""
        self.grid_view.load_notes()
        self.stacked_widget.setCurrentIndex(0)


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Sticky Notes")
    
    # Modern typography
    font = QFont("Segoe UI Variable Text", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Initialize Theme Manager and apply active theme
    theme_mgr = get_theme_manager()
    app.setStyleSheet(theme_mgr.get_app_stylesheet())
    theme_mgr.theme_changed.connect(lambda _: app.setStyleSheet(theme_mgr.get_app_stylesheet()))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
