"""
update_dialog.py - Comprehensive In-App Software Update Center for Sticky Notes.
Features live GitHub API querying, private repository token authentication,
markdown changelog preview, chunked download progress, and Windows self-restart.
Uses QStackedWidget to permanently eliminate layout overlap during state transitions.
"""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QFrame, QProgressBar,
    QLineEdit, QMessageBox, QTextBrowser, QStackedWidget
)
from PySide6.QtGui import QDesktopServices, QCursor

try:
    from ..version import __version__, HOMEPAGE
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES, get_markdown_preview_css
    from ..icons import get_themed_icon
    from ..updater import (
        UpdateCheckWorker, UpdateDownloadWorker, apply_update_and_restart,
        get_stored_github_token, save_stored_github_token,
        get_stored_mirror_url, save_stored_mirror_url, DEFAULT_PUBLIC_MANIFEST_URL
    )
except ImportError:
    from version import __version__, HOMEPAGE
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES, get_markdown_preview_css
    from icons import get_themed_icon
    from updater import (
        UpdateCheckWorker, UpdateDownloadWorker, apply_update_and_restart,
        get_stored_github_token, save_stored_github_token,
        get_stored_mirror_url, save_stored_mirror_url, DEFAULT_PUBLIC_MANIFEST_URL
    )


class UpdateDialog(QDialog):
    """
    Modal software updater dialog supporting both public mirror and private GitHub repositories.
    Uses QStackedWidget for glitch-free, non-overlapping state transitions.
    """
    def __init__(self, parent=None, auto_check: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Sticky Notes - Check for Updates")
        self.resize(580, 520)
        self.setMinimumSize(500, 460)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])

        self.check_worker = None
        self.download_worker = None
        self.release_info = None
        self.downloaded_zip_path = None
        self.restart_timer = None
        self.auto_restart_seconds = 3

        self._build_ui()

        if auto_check:
            self._start_check()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with Version Info
        header_frame = QFrame(self)
        header_frame.setObjectName("HeaderFrame")
        header_frame.setStyleSheet(f"""
            QFrame#HeaderFrame {{
                background-color: {self.pal['bg_main']};
                border: 1px solid {self.pal['border']};
                border-radius: 10px;
            }}
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(16, 12, 16, 12)
        
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title_lbl = QLabel("Sticky Notes Update Center", header_frame)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']}; background: transparent; border: none;")
        info_col.addWidget(title_lbl)

        ver_lbl = QLabel(f"Installed Version: <b>v{__version__}</b>", header_frame)
        ver_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']}; background: transparent; border: none;")
        info_col.addWidget(ver_lbl)

        self.source_lbl = QLabel("Feed: Auto-detecting...", header_frame)
        self.source_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']}; background: transparent; border: none;")
        info_col.addWidget(self.source_lbl)

        h_layout.addLayout(info_col)
        h_layout.addStretch()

        self.status_icon_lbl = QLabel(header_frame)
        self.status_icon_lbl.setPixmap(get_themed_icon("clock", role="primary", theme=self.theme, size=28).pixmap(28, 28))
        self.status_icon_lbl.setStyleSheet("background: transparent; border: none;")
        h_layout.addWidget(self.status_icon_lbl)

        layout.addWidget(header_frame)

        # Central Dynamic Card (Houses QStackedWidget)
        self.card = QFrame(self)
        self.card.setObjectName("CentralCard")
        self.card.setStyleSheet(f"""
            QFrame#CentralCard {{
                background-color: {self.pal['bg_surface']};
                border: 1px solid {self.pal['border']};
                border-radius: 10px;
            }}
        """)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(16, 16, 16, 16)
        self.card_layout.setSpacing(12)

        # QStackedWidget contains dedicated, isolated pages
        self.stack = QStackedWidget(self.card)
        self.card_layout.addWidget(self.stack)

        self._build_stack_pages()

        layout.addWidget(self.card, 1)

        # Bottom row
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)
        
        self.token_settings_btn = QPushButton("⚙️ Update Settings...", self)
        self.token_settings_btn.setObjectName("SelectModeButton")
        self.token_settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.token_settings_btn.clicked.connect(self._show_token_section)
        bottom_row.addWidget(self.token_settings_btn)

        bottom_row.addStretch()

        self.close_btn = QPushButton("Close", self)
        self.close_btn.setObjectName("SelectModeButton")
        self.close_btn.setFixedSize(90, 32)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.reject)
        bottom_row.addWidget(self.close_btn)

        layout.addLayout(bottom_row)

        self._show_checking_state()

    def _build_stack_pages(self):
        """Constructs static pages inside the stacked widget."""
        # Page 0: Checking
        self.page_checking = QWidget(self.stack)
        p0_layout = QVBoxLayout(self.page_checking)
        p0_layout.setContentsMargins(0, 20, 0, 0)
        self.checking_lbl = QLabel("🔍 Checking GitHub for updates...", self.page_checking)
        self.checking_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.checking_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.pal['text_primary']}; margin-top: 40px;")
        p0_layout.addWidget(self.checking_lbl)
        p0_layout.addStretch()
        self.stack.addWidget(self.page_checking)

        # Page 1: Up to Date
        self.page_up_to_date = QWidget(self.stack)
        p1_layout = QVBoxLayout(self.page_up_to_date)
        p1_layout.setContentsMargins(0, 10, 0, 0)
        p1_layout.setSpacing(8)
        
        uptodate_icon = QLabel(self.page_up_to_date)
        uptodate_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uptodate_icon.setPixmap(get_themed_icon("check", role="accent", theme=self.theme, size=36).pixmap(36, 36))
        p1_layout.addWidget(uptodate_icon)

        uptodate_title = QLabel("You're on the latest version!", self.page_up_to_date)
        uptodate_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uptodate_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        p1_layout.addWidget(uptodate_title)

        uptodate_desc = QLabel(f"Sticky Notes v{__version__} is currently up to date.", self.page_up_to_date)
        uptodate_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uptodate_desc.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']};")
        p1_layout.addWidget(uptodate_desc)
        p1_layout.addStretch()

        p1_btn_row = QHBoxLayout()
        p1_btn_row.addStretch()
        check_again_btn = QPushButton(" Check Again", self.page_up_to_date)
        check_again_btn.setIcon(get_themed_icon("clock", role="btn_text", theme=self.theme, size=15))
        check_again_btn.setObjectName("SelectModeButton")
        check_again_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        check_again_btn.clicked.connect(self._start_check)
        p1_btn_row.addWidget(check_again_btn)
        p1_btn_row.addStretch()
        p1_layout.addLayout(p1_btn_row)
        self.stack.addWidget(self.page_up_to_date)

        # Page 2: Update Available
        self.page_available = QWidget(self.stack)
        p2_layout = QVBoxLayout(self.page_available)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        p2_layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.avail_badge = QLabel(self.page_available)
        self.avail_badge.setStyleSheet(f"""
            background-color: {self.pal['accent']};
            color: {self.pal['accent_text']};
            border-radius: 6px;
            font-weight: 700;
            font-size: 12px;
            padding: 4px 8px;
            border: none;
        """)
        top_row.addWidget(self.avail_badge)

        self.avail_date_lbl = QLabel(self.page_available)
        self.avail_date_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']}; border: none; background: transparent;")
        top_row.addWidget(self.avail_date_lbl)
        top_row.addStretch()
        p2_layout.addLayout(top_row)

        self.notes_browser = QTextBrowser(self.page_available)
        self.notes_browser.setOpenExternalLinks(True)
        self.notes_browser.setMinimumHeight(130)
        self.notes_browser.setStyleSheet(f"QTextBrowser {{ border: 1px solid {self.pal['border']}; border-radius: 8px; background-color: {self.pal['bg_main']}; }}")
        p2_layout.addWidget(self.notes_browser, 1)

        p2_action_row = QHBoxLayout()
        p2_action_row.setContentsMargins(0, 4, 0, 0)
        p2_action_row.setSpacing(10)

        self.avail_gh_btn = QPushButton(" View on GitHub", self.page_available)
        self.avail_gh_btn.setIcon(get_themed_icon("external_link", role="btn_text", theme=self.theme, size=15))
        self.avail_gh_btn.setObjectName("SelectModeButton")
        self.avail_gh_btn.setFixedHeight(34)
        self.avail_gh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.avail_gh_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.release_info.get("html_url", HOMEPAGE) if self.release_info else HOMEPAGE)))
        p2_action_row.addWidget(self.avail_gh_btn)

        p2_action_row.addStretch()

        self.avail_dl_btn = QPushButton("⬇ Download & Install Update", self.page_available)
        self.avail_dl_btn.setObjectName("NewNoteButton")
        self.avail_dl_btn.setFixedHeight(34)
        self.avail_dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.avail_dl_btn.clicked.connect(self._start_download)
        p2_action_row.addWidget(self.avail_dl_btn)
        p2_layout.addLayout(p2_action_row)
        self.stack.addWidget(self.page_available)

        # Page 3: Downloading
        self.page_downloading = QWidget(self.stack)
        p3_layout = QVBoxLayout(self.page_downloading)
        p3_layout.setContentsMargins(0, 10, 0, 0)
        p3_layout.setSpacing(12)

        self.dl_title_lbl = QLabel("Downloading Sticky Notes...", self.page_downloading)
        self.dl_title_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.pal['text_primary']};")
        p3_layout.addWidget(self.dl_title_lbl)

        self.progress_bar = QProgressBar(self.page_downloading)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self.pal['border']};
                border-radius: 6px;
                text-align: center;
                height: 22px;
                color: {self.pal['text_primary']};
                background: {self.pal['bg_main']};
            }}
            QProgressBar::chunk {{
                background-color: {self.pal['accent']};
                border-radius: 5px;
            }}
        """)
        p3_layout.addWidget(self.progress_bar)

        self.download_meta_lbl = QLabel("Connecting...", self.page_downloading)
        self.download_meta_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']};")
        p3_layout.addWidget(self.download_meta_lbl)
        p3_layout.addStretch()

        p3_cancel_row = QHBoxLayout()
        p3_cancel_row.setContentsMargins(0, 8, 0, 0)
        p3_cancel_row.addStretch()
        cancel_btn = QPushButton("Cancel Download", self.page_downloading)
        cancel_btn.setObjectName("SelectModeButton")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self._cancel_download)
        p3_cancel_row.addWidget(cancel_btn)
        p3_layout.addLayout(p3_cancel_row)
        self.stack.addWidget(self.page_downloading)

        # Page 4: Install Ready
        self.page_install_ready = QWidget(self.stack)
        self.p4_layout = QVBoxLayout(self.page_install_ready)
        self.p4_layout.setContentsMargins(0, 10, 0, 0)
        self.p4_layout.setSpacing(8)

        ready_icon = QLabel(self.page_install_ready)
        ready_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ready_icon.setPixmap(get_themed_icon("check", role="accent", theme=self.theme, size=36).pixmap(36, 36))
        self.p4_layout.addWidget(ready_icon)

        ready_title = QLabel("Update Downloaded & Ready!", self.page_install_ready)
        ready_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ready_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        self.p4_layout.addWidget(ready_title)

        self.install_msg_lbl = QLabel(self.page_install_ready)
        self.install_msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.install_msg_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']};")
        self.install_msg_lbl.setWordWrap(True)
        self.p4_layout.addWidget(self.install_msg_lbl)

        self.countdown_lbl = QLabel(self.page_install_ready)
        self.countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {self.pal['accent']}; margin-top: 4px;")
        self.p4_layout.addWidget(self.countdown_lbl)

        self.p4_layout.addStretch()

        self.install_btn_row = QHBoxLayout()
        self.install_btn_row.setContentsMargins(0, 8, 0, 0)
        self.install_btn_row.setSpacing(10)
        self.p4_layout.addLayout(self.install_btn_row)
        self.stack.addWidget(self.page_install_ready)

        # Page 5: Settings / Configuration
        self.page_settings = QWidget(self.stack)
        p5_layout = QVBoxLayout(self.page_settings)
        p5_layout.setContentsMargins(0, 0, 0, 0)
        p5_layout.setSpacing(8)

        settings_title = QLabel("⚙️ Software Update Configuration", self.page_settings)
        settings_title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {self.pal['text_primary']};")
        p5_layout.addWidget(settings_title)

        mirror_header = QLabel("<b>🌐 Public Releases Mirror Feed</b>", self.page_settings)
        mirror_header.setStyleSheet(f"font-size: 13px; color: {self.pal['text_primary']};")
        p5_layout.addWidget(mirror_header)

        mirror_info = QLabel("Allows checking for and downloading updates without needing a personal GitHub token.", self.page_settings)
        mirror_info.setStyleSheet(f"font-size: 11px; color: {self.pal['text_secondary']};")
        mirror_info.setWordWrap(True)
        p5_layout.addWidget(mirror_info)

        self.mirror_input = QLineEdit(self.page_settings)
        self.mirror_input.setPlaceholderText("Mirror manifest URL (e.g. https://.../version.json)")
        self.mirror_input.setText(get_stored_mirror_url())
        self.mirror_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        p5_layout.addWidget(self.mirror_input)

        mirror_btn_row = QHBoxLayout()
        test_mirror_btn = QPushButton("📡 Test Connection", self.page_settings)
        test_mirror_btn.setObjectName("SelectModeButton")
        test_mirror_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        test_mirror_btn.clicked.connect(self._test_feed_connection)
        mirror_btn_row.addWidget(test_mirror_btn)

        reset_mirror_btn = QPushButton("↺ Default Mirror", self.page_settings)
        reset_mirror_btn.setObjectName("SelectModeButton")
        reset_mirror_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_mirror_btn.clicked.connect(lambda: self.mirror_input.setText(DEFAULT_PUBLIC_MANIFEST_URL))
        mirror_btn_row.addWidget(reset_mirror_btn)
        mirror_btn_row.addStretch()
        p5_layout.addLayout(mirror_btn_row)

        sep = QFrame(self.page_settings)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self.pal['border']}; margin: 4px 0;")
        p5_layout.addWidget(sep)

        token_header = QLabel("<b>🔒 Private GitHub Access Token (Optional)</b>", self.page_settings)
        token_header.setStyleSheet(f"font-size: 13px; color: {self.pal['text_primary']};")
        p5_layout.addWidget(token_header)

        token_info = QLabel("Only required if querying the private repository directly instead of the public mirror.", self.page_settings)
        token_info.setStyleSheet(f"font-size: 11px; color: {self.pal['text_secondary']};")
        token_info.setWordWrap(True)
        p5_layout.addWidget(token_info)

        self.token_input = QLineEdit(self.page_settings)
        self.token_input.setPlaceholderText("Paste GitHub Personal Access Token (ghp_... or github_pat_...)")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        existing = get_stored_github_token()
        if existing:
            self.token_input.setText(existing)
        self.token_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self.pal['input_bg']};
                color: {self.pal['text_primary']};
                border: 1px solid {self.pal['input_border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: monospace;
            }}
        """)
        p5_layout.addWidget(self.token_input)

        row = QHBoxLayout()
        link_btn = QPushButton("🌐 Generate Token on GitHub", self.page_settings)
        link_btn.setObjectName("SelectModeButton")
        link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/settings/tokens?type=beta")))
        row.addWidget(link_btn)
        row.addStretch()

        save_btn = QPushButton("💾 Save Settings & Check", self.page_settings)
        save_btn.setObjectName("NewNoteButton")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(self._save_token_and_check)
        row.addWidget(save_btn)
        p5_layout.addLayout(row)
        p5_layout.addStretch()
        self.stack.addWidget(self.page_settings)

        # Page 6: Error
        self.page_error = QWidget(self.stack)
        p6_layout = QVBoxLayout(self.page_error)
        p6_layout.setContentsMargins(0, 20, 0, 0)
        p6_layout.setSpacing(10)

        self.error_title_lbl = QLabel(self.page_error)
        self.error_title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #E57373;")
        p6_layout.addWidget(self.error_title_lbl)

        self.error_desc_lbl = QLabel(self.page_error)
        self.error_desc_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_primary']};")
        self.error_desc_lbl.setWordWrap(True)
        p6_layout.addWidget(self.error_desc_lbl)
        p6_layout.addStretch()

        p6_row = QHBoxLayout()
        p6_row.addStretch()
        retry_btn = QPushButton("Retry Check", self.page_error)
        retry_btn.setObjectName("SelectModeButton")
        retry_btn.clicked.connect(self._start_check)
        p6_row.addWidget(retry_btn)
        p6_layout.addLayout(p6_row)
        self.stack.addWidget(self.page_error)

    def _clear_card(self):
        """Maintained for test and caller compatibility; QStackedWidget natively handles clean state switching."""
        pass

    def get_active_buttons(self) -> list:
        """Returns the list of QPushButtons on the currently displayed page."""
        cur = self.stack.currentWidget()
        return cur.findChildren(QPushButton) if cur else []

    # --- View State Transitions ---

    def _show_checking_state(self):
        self.stack.setCurrentWidget(self.page_checking)

    def _show_up_to_date(self):
        self.stack.setCurrentWidget(self.page_up_to_date)

    def _show_update_available(self, release_info: dict):
        self.release_info = release_info

        ver = release_info.get("version", "Unknown")
        self.avail_badge.setText(f" v{ver} Available! ")

        date_str = release_info.get("published_at", "")[:10]
        self.avail_date_lbl.setText(f"Released: {date_str}" if date_str else "")

        css = get_markdown_preview_css(self.theme)
        try:
            import markdown2
            body_html = markdown2.markdown(release_info.get("body", "No release notes provided."))
        except Exception:
            body_html = f"<pre>{release_info.get('body', '')}</pre>"

        self.notes_browser.setHtml(f"<html><head>{css}</head><body>{body_html}</body></html>")
        self.stack.setCurrentWidget(self.page_available)

    def _show_downloading_state(self):
        ver = self.release_info.get("version", "") if self.release_info else ""
        self.dl_title_lbl.setText(f"Downloading Sticky Notes v{ver}..." if ver else "Downloading update...")
        self.progress_bar.setValue(0)
        self.download_meta_lbl.setText("Connecting to server...")
        self.stack.setCurrentWidget(self.page_downloading)

    def _show_install_ready(self, zip_path: str):
        self.downloaded_zip_path = zip_path
        file_path = Path(zip_path)
        is_exe = file_path.suffix.lower() == ".exe"
        is_frozen = getattr(sys, 'frozen', False)

        if is_frozen:
            msg_text = "Sticky Notes will close, install the updated files, and automatically relaunch the newest version."
        elif is_exe:
            msg_text = "The standalone Windows installer has been downloaded. Click below to run the setup wizard and update Sticky Notes."
        else:
            msg_text = f"The update archive is ready at:\n{file_path}\n\nYou are running Sticky Notes in Python development mode."

        self.install_msg_lbl.setText(msg_text)

        # Clear previous dynamic buttons in install_btn_row
        while self.install_btn_row.count():
            item = self.install_btn_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.install_btn_row.addStretch()

        if is_frozen:
            self.auto_restart_seconds = 3
            self.countdown_lbl.setText(f"Restarting to apply update in {self.auto_restart_seconds} seconds...")
            self.countdown_lbl.setVisible(True)

            if not self.restart_timer:
                self.restart_timer = QTimer(self)
                self.restart_timer.timeout.connect(self._on_restart_timer_tick)
            self.restart_timer.start(1000)

            restart_btn = QPushButton("🚀 Restart Now", self.page_install_ready)
            restart_btn.setObjectName("NewNoteButton")
            restart_btn.setFixedHeight(34)
            restart_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            restart_btn.clicked.connect(self._apply_update)
            self.install_btn_row.addWidget(restart_btn)

            cancel_auto_btn = QPushButton("Cancel Auto-Restart", self.page_install_ready)
            cancel_auto_btn.setObjectName("SelectModeButton")
            cancel_auto_btn.setFixedHeight(34)
            cancel_auto_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            cancel_auto_btn.clicked.connect(self._cancel_auto_restart)
            self.install_btn_row.addWidget(cancel_auto_btn)
        elif is_exe:
            self.countdown_lbl.setVisible(False)
            run_installer_btn = QPushButton("🚀 Run Installer Now", self.page_install_ready)
            run_installer_btn.setObjectName("NewNoteButton")
            run_installer_btn.setFixedHeight(34)
            run_installer_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            run_installer_btn.clicked.connect(self._apply_update)
            self.install_btn_row.addWidget(run_installer_btn)

            open_folder_btn = QPushButton("📂 Open Folder", self.page_install_ready)
            open_folder_btn.setObjectName("SelectModeButton")
            open_folder_btn.setFixedHeight(34)
            open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent))))
            self.install_btn_row.addWidget(open_folder_btn)
        else:
            self.countdown_lbl.setVisible(False)
            open_folder_btn = QPushButton("📂 Open Downloaded Package", self.page_install_ready)
            open_folder_btn.setObjectName("NewNoteButton")
            open_folder_btn.setFixedHeight(34)
            open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent))))
            self.install_btn_row.addWidget(open_folder_btn)

        self.install_btn_row.addStretch()
        self.stack.setCurrentWidget(self.page_install_ready)

    def _on_restart_timer_tick(self):
        self.auto_restart_seconds -= 1
        if self.auto_restart_seconds > 0:
            if hasattr(self, 'countdown_lbl'):
                self.countdown_lbl.setText(f"Restarting to apply update in {self.auto_restart_seconds} seconds...")
        else:
            if self.restart_timer:
                self.restart_timer.stop()
            self._apply_update()

    def _cancel_auto_restart(self):
        if self.restart_timer:
            self.restart_timer.stop()
        if hasattr(self, 'countdown_lbl'):
            self.countdown_lbl.setText("Auto-restart cancelled. Click 'Restart Now' when you are ready.")

    def _show_error_or_auth(self, error_msg: str, is_auth: bool):
        if is_auth:
            self._show_token_section()
        else:
            self.error_title_lbl.setText("⚠️ Update Check Error")
            self.error_desc_lbl.setText(error_msg)
            self.stack.setCurrentWidget(self.page_error)

    def _show_token_section(self):
        self.mirror_input.setText(get_stored_mirror_url())
        tok = get_stored_github_token()
        if tok:
            self.token_input.setText(tok)
        self.stack.setCurrentWidget(self.page_settings)

    def _test_feed_connection(self):
        url = self.mirror_input.text().strip() if hasattr(self, 'mirror_input') else ""
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please specify a mirror URL.")
            return

        import urllib.request
        import json
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    version_str = data.get("version") or data.get("tag_name", "Unknown")
                    QMessageBox.information(
                        self,
                        "Connection Successful",
                        f"Successfully reached mirror feed!\n\nLatest reported version: {version_str}\nStatus: HTTP 200 OK"
                    )
                else:
                    QMessageBox.warning(self, "Mirror Warning", f"Mirror returned HTTP {resp.status}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Mirror Unreachable",
                f"Could not connect to mirror at:\n{url}\n\nError: {str(e)}"
            )

    # --- Actions ---

    def _start_check(self):
        self._show_checking_state()
        token = get_stored_github_token()
        mirror_url = get_stored_mirror_url()
        self.check_worker = UpdateCheckWorker(token=token, mirror_url=mirror_url, parent=self)
        self.check_worker.check_finished.connect(self._on_check_finished)
        self.check_worker.check_failed.connect(self._on_check_failed)
        self.check_worker.start()

    def _on_check_finished(self, has_update: bool, release_info: dict):
        if hasattr(self, 'source_lbl'):
            src = release_info.get("source", "mirror")
            if src == "public_mirror":
                self.source_lbl.setText("🌐 Source: Public Mirror (Zero-Token)")
            elif src == "private_repo":
                self.source_lbl.setText("🔒 Source: GitHub Private API (Authenticated)")
            else:
                self.source_lbl.setText(f"📡 Source: {src}")

        if has_update:
            self._show_update_available(release_info)
        else:
            self._show_up_to_date()

    def _on_check_failed(self, error_msg: str, is_auth: bool):
        if hasattr(self, 'source_lbl'):
            self.source_lbl.setText("⚠️ Feed: Connection Failed")
        self._show_error_or_auth(error_msg, is_auth)

    def _save_token_and_check(self):
        if hasattr(self, 'mirror_input'):
            mirror_url = self.mirror_input.text().strip()
            if mirror_url:
                save_stored_mirror_url(mirror_url)

        if hasattr(self, 'token_input'):
            token = self.token_input.text().strip()
            save_stored_github_token(token)

        QMessageBox.information(self, "Settings Saved", "Update settings saved successfully.")
        self._start_check()

    def _start_download(self, use_installer: bool = False):
        if not self.release_info:
            return
        self._show_downloading_state()
        token = get_stored_github_token()
        has_installer = bool(self.release_info.get("installer_url"))
        download_installer = use_installer or has_installer
        self.download_worker = UpdateDownloadWorker(
            self.release_info, token=token, use_installer=download_installer, parent=self
        )
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.download_failed.connect(self._on_download_failed)
        self.download_worker.start()

    def _on_download_progress(self, downloaded: int, total: int, percent: float):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(percent))
        if hasattr(self, 'download_meta_lbl'):
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.download_meta_lbl.setText(f"{dl_mb:.1f} MB / {tot_mb:.1f} MB ({percent:.0f}%)")

    def _cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.cancel()
        self._show_update_available(self.release_info)

    def _on_download_finished(self, file_path: str):
        self._show_install_ready(file_path)

    def _on_download_failed(self, err_msg: str):
        QMessageBox.warning(self, "Download Error", err_msg)
        if self.release_info:
            self._show_update_available(self.release_info)
        else:
            self._show_up_to_date()

    def _apply_update(self):
        if self.restart_timer:
            self.restart_timer.stop()
        if not self.downloaded_zip_path:
            return
        file_path = Path(self.downloaded_zip_path)
        is_frozen = getattr(sys, 'frozen', False)
        is_exe = file_path.suffix.lower() == ".exe"

        try:
            if is_frozen:
                # Production mode: launch batch script that replaces files and restarts
                apply_update_and_restart(str(file_path))
            elif is_exe:
                # Development mode with .exe installer: just run the installer directly
                import os
                if hasattr(os, 'startfile'):
                    os.startfile(str(file_path))
                else:
                    import subprocess
                    subprocess.Popen(
                        [str(file_path)],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                self.accept()
            else:
                # Development mode with .zip: just show the download location
                QMessageBox.information(
                    self,
                    "Development Mode",
                    f"Update package successfully downloaded to:\n{file_path}\n\nIn development mode, please run git pull or extract the ZIP."
                )
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))
        except SystemExit:
            # apply_update_and_restart() calls sys.exit(0) on success — let it through
            raise
        except Exception as e:
            QMessageBox.critical(
                self,
                "Update Failed",
                f"Failed to apply the update:\n\n{str(e)}\n\n"
                f"The downloaded installer is at:\n{file_path}\n\n"
                f"You can run it manually to update."
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))

    def closeEvent(self, event):
        if self.restart_timer:
            self.restart_timer.stop()
        super().closeEvent(event)

    def reject(self):
        if self.restart_timer:
            self.restart_timer.stop()
        super().reject()
