import sys
from pathlib import Path

# Ensure package directory is in sys.path for direct script execution
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, 
    QVBoxLayout, QStackedWidget
)
from PySide6.QtGui import (
    QIcon, QFont, QPixmap, QPainter, 
    QColor, QPen, QPolygonF
)

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


def get_app_icon() -> QIcon:
    """
    Resolves the application yellow notepad icon across development, installed,
    and PyInstaller frozen bundles, with a programmatic high-DPI vector fallback.
    Builds a multi-resolution QIcon supporting all standard Windows taskbar and titlebar dimensions.
    """
    icon = QIcon()

    # 1. Load from file candidates (both .ico and .png)
    candidates = [
        APP_DIR / "assets" / "icon.ico",
        Path(sys.executable).parent / "assets" / "icon.ico",
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.ico",
        APP_DIR / "assets" / "icon.png",
        Path(sys.executable).parent / "assets" / "icon.png",
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icon.png",
    ]
    for p in candidates:
        if p and p.is_file():
            loaded = QIcon(str(p))
            if not loaded.isNull():
                for s in loaded.availableSizes():
                    icon.addPixmap(loaded.pixmap(s))
                if not icon.isNull() and len(icon.availableSizes()) >= 4:
                    return icon

    # 2. Programmatic vector generator: creates crisp, high-DPI icons for all Windows sizes
    for size in [16, 20, 24, 32, 40, 48, 64, 128, 256]:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pad = max(1, int(size * 0.08))
        r = max(2, int(size * 0.12))
        x0, y0 = pad, pad
        w, h = size - 2 * pad, size - 2 * pad

        # Base yellow card body
        painter.setBrush(QColor("#FFD54F"))
        painter.setPen(QPen(QColor("#FFB300"), max(1.0, size * 0.04)))
        painter.drawRoundedRect(x0, y0, w, h, r, r)

        # Folded top-right corner
        if size >= 20:
            fold = int(w * 0.32)
            fx = x0 + w - fold
            fy = y0 + fold
            painter.setBrush(QColor("#FFECB3"))
            fold_poly = QPolygonF([QPointF(fx, y0), QPointF(x0 + w, fy), QPointF(fx, fy)])
            painter.drawPolygon(fold_poly)

        # Note lines
        if size >= 24:
            painter.setPen(QPen(QColor("#BF8600"), max(1.0, size * 0.04)))
            line_x0 = x0 + int(w * 0.2)
            line_x1 = x0 + int(w * 0.8)
            start_y = y0 + int(h * 0.45)
            spacing = int((h - int(h * 0.45)) / 4)
            for i in range(3):
                ly = start_y + (i + 1) * spacing
                painter.drawLine(line_x0, ly, line_x1, ly)

        painter.end()
        icon.addPixmap(pix)

    return icon


class MainWindow(QMainWindow):
    """
    Main application single-window container.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(version.APP_NAME)
        
        # Application & Window Icon
        self.setWindowIcon(get_app_icon())

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
    # Set explicit constant AppUserModelID on Windows so taskbar & titlebar properly link the app icon
    if sys.platform == "win32":
        try:
            import ctypes
            # Constant AppUserModelID across all releases ensures taskbar shortcuts & pins remain linked
            app_id = "DavidAlexanderM.StickyNotes"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(version.APP_NAME)
    app_icon = get_app_icon()
    app.setWindowIcon(app_icon)
    
    # Modern typography
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Initialize Theme Manager and apply active theme
    theme_mgr = get_theme_manager()
    app.setStyleSheet(theme_mgr.get_app_stylesheet())
    theme_mgr.theme_changed.connect(lambda _: app.setStyleSheet(theme_mgr.get_app_stylesheet()))

    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()

    # Re-apply window icon to ensure native WM_SETICON reaches realized HWND on Windows
    if sys.platform == "win32":
        window.setWindowIcon(app_icon)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
