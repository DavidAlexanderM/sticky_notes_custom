from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsDropShadowEffect, QFrame
)
from PySide6.QtGui import QColor, QCursor
try:
    from ..styles import NOTE_COLORS
except ImportError:
    from styles import NOTE_COLORS

class ColorCircleButton(QPushButton):
    """Circular color swatch button."""
    def __init__(self, color_hex: str, color_name: str, border_color: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(26, 26)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(color_name)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                border: 2px solid {border_color};
                border-radius: 13px;
            }}
            QPushButton:hover {{
                border: 2px solid #005FB8;
                transform: scale(1.1);
            }}
        """)

class ColorPickerFlyout(QFrame):
    """
    Floating context menu / flyout for picking note colors and quick actions.
    """
    color_selected = Signal(str)
    duplicate_requested = Signal()
    share_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("FlyoutContainer")
        
        # Outer layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Card container with shadow
        card = QFrame(self)
        card.setObjectName("FlyoutCard")
        card.setStyleSheet("""
            QFrame#FlyoutCard {
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)
        card_layout.setContentsMargins(8, 8, 8, 8)

        # Title
        title = QLabel("Note Color", card)
        title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;")
        card_layout.addWidget(title)

        # Swatches Row 1 & Row 2
        swatch_layout1 = QHBoxLayout()
        swatch_layout1.setSpacing(6)
        swatch_layout2 = QHBoxLayout()
        swatch_layout2.setSpacing(6)

        for i, item in enumerate(NOTE_COLORS):
            btn = ColorCircleButton(item["hex"], item["name"], item["border"], card)
            btn.clicked.connect(lambda _, hex_val=item["hex"]: self._on_color_picked(hex_val))
            if i < 4:
                swatch_layout1.addWidget(btn)
            else:
                swatch_layout2.addWidget(btn)

        card_layout.addLayout(swatch_layout1)
        card_layout.addLayout(swatch_layout2)

        # Separator line
        sep = QFrame(card)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(0, 0, 0, 0.08);")
        card_layout.addWidget(sep)

        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #334155;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """

        # Duplicate Action Button
        dup_btn = QPushButton("📋 Duplicate Note", card)
        dup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        dup_btn.setStyleSheet(btn_style)
        dup_btn.clicked.connect(self._on_duplicate_clicked)
        card_layout.addWidget(dup_btn)

        # Share Action Button
        share_btn = QPushButton("↗ Share / Export...", card)
        share_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        share_btn.setStyleSheet(btn_style)
        share_btn.clicked.connect(self._on_share_clicked)
        card_layout.addWidget(share_btn)

        # Delete Action Button
        del_btn = QPushButton("🗑 Delete Note", card)
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #DC2626;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
            }
        """)
        del_btn.clicked.connect(self._on_delete_clicked)
        card_layout.addWidget(del_btn)

        main_layout.addWidget(card)

    def _on_color_picked(self, hex_code: str):
        self.color_selected.emit(hex_code)
        self.close()

    def _on_duplicate_clicked(self):
        self.duplicate_requested.emit()
        self.close()

    def _on_share_clicked(self):
        self.share_requested.emit()
        self.close()

    def _on_delete_clicked(self):
        self.delete_requested.emit()
        self.close()

