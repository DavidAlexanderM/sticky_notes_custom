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
    from .views.grid_view import StickyNotesGridView
    from .views.editor_view import NoteEditorView
except ImportError:
    import database
    import version
    from styles import APP_STYLESHEET
    from views.grid_view import StickyNotesGridView
    from views.editor_view import NoteEditorView

class MainWindow(QMainWindow):
    """
    Main application single-window container.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(version.APP_TITLE)
        self.resize(880, 640)
        self.setMinimumSize(620, 460)

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
    
    # Modern Segoe UI typography
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Apply stylesheet
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
