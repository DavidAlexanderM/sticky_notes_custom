from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsDropShadowEffect, QFrame
)
from PySide6.QtGui import QColor, QCursor

try:
    from ..styles import NOTE_COLORS, THEME_PALETTES
    from ..theme_manager import get_theme_manager
    from ..icons import get_icon, get_themed_icon
except ImportError:
    from styles import NOTE_COLORS, THEME_PALETTES
    from theme_manager import get_theme_manager
    from icons import get_icon, get_themed_icon


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
                border: 2px solid #2563EB;
            }}
        """)


class ColorPickerFlyout(QFrame):
    """
    Floating context menu / flyout for picking note colors and quick actions.
    Dynamically themes to Light, Dark, and Sepia mode to eliminate jarring white popups.
    """
    color_selected = Signal(str)
    duplicate_requested = Signal()
    share_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("FlyoutContainer")
        
        self.theme_mgr = get_theme_manager()
        theme = self.theme_mgr.current_theme
        pal = THEME_PALETTES.get(theme, THEME_PALETTES["light"])
        is_dark = self.theme_mgr.is_dark_mode()

        # Outer layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Card container with soft elevation shadow
        self.card = QFrame(self)
        self.card.setObjectName("FlyoutCard")
        
        card_bg = pal.get("bg_surface", "#1E293B" if is_dark else "#FFFFFF")
        card_border = pal.get("border", "#475569" if is_dark else "#CBD5E1")
        text_primary = pal.get("text_primary", "#F8FAFC" if is_dark else "#0F172A")
        text_muted = pal.get("text_muted", "#94A3B8" if is_dark else "#64748B")
        border_subtle = pal.get("border_subtle", "#334155" if is_dark else "#E2E8F0")
        btn_hover = pal.get("btn_hover", "#334155" if is_dark else "#F1F5F9")
        del_hover = "rgba(220, 38, 38, 0.25)" if is_dark else "#FEE2E2"

        self.card.setStyleSheet(f"""
            QFrame#FlyoutCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 80 if is_dark else 40))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(6)
        card_layout.setContentsMargins(8, 8, 8, 8)

        # Title
        title = QLabel("Note Color", self.card)
        title.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {text_muted}; text-transform: uppercase; letter-spacing: 0.5px; background: transparent;")
        card_layout.addWidget(title)

        # Swatches Row 1 & Row 2
        swatch_layout1 = QHBoxLayout()
        swatch_layout1.setSpacing(6)
        swatch_layout2 = QHBoxLayout()
        swatch_layout2.setSpacing(6)

        for i, item in enumerate(NOTE_COLORS):
            btn = ColorCircleButton(item["hex"], item["name"], item["border"], self.card)
            btn.clicked.connect(lambda _, hex_val=item["hex"]: self._on_color_picked(hex_val))
            if i < 4:
                swatch_layout1.addWidget(btn)
            else:
                swatch_layout2.addWidget(btn)

        card_layout.addLayout(swatch_layout1)
        card_layout.addLayout(swatch_layout2)

        # Separator line
        sep = QFrame(self.card)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {border_subtle}; max-height: 1px; border: none; margin: 4px 0;")
        card_layout.addWidget(sep)

        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {text_primary};
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {pal.get('accent', '#38BDF8' if is_dark else '#2563EB')};
            }}
        """

        # Duplicate Action Button with Vector Icon
        dup_btn = QPushButton(" Duplicate Note", self.card)
        dup_btn.setIcon(get_themed_icon("copy", role="primary", theme=theme, size=15))
        dup_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        dup_btn.setStyleSheet(btn_style)
        dup_btn.clicked.connect(self._on_duplicate_clicked)
        card_layout.addWidget(dup_btn)

        # Share Action Button with Vector Icon
        share_btn = QPushButton(" Share / Export...", self.card)
        share_btn.setIcon(get_themed_icon("share", role="primary", theme=theme, size=15))
        share_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        share_btn.setStyleSheet(btn_style)
        share_btn.clicked.connect(self._on_share_clicked)
        card_layout.addWidget(share_btn)

        # Delete Action Button with Vector Icon
        del_btn = QPushButton(" Delete Note", self.card)
        del_btn.setIcon(get_icon("trash", color="#EF4444", size=15))
        del_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #EF4444;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {del_hover};
                color: #DC2626;
            }}
        """)
        del_btn.clicked.connect(self._on_delete_clicked)
        card_layout.addWidget(del_btn)

        main_layout.addWidget(self.card)

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
