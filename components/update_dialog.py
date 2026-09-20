"""
update_dialog.py - Comprehensive In-App Software Update Center for Sticky Notes.
Features live GitHub API querying, private repository token authentication,
markdown changelog preview, chunked download progress, and Windows self-restart.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QFrame, QProgressBar,
    QScrollArea, QLineEdit, QMessageBox, QTextBrowser
)
from PySide6.QtGui import QDesktopServices, QCursor, QFont

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
    Modal software updater dialog supporting both public and private GitHub repositories.
    """
    def __init__(self, parent=None, auto_check: bool = True):
        super().__init__(parent)
        self.setWindowTitle(f"Sticky Notes - Check for Updates")
        self.resize(540, 500)
        self.setMinimumSize(460, 420)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])

        self.check_worker = None
        self.download_worker = None
        self.release_info = None
        self.downloaded_zip_path = None

        self._build_ui()

        if auto_check:
            self._start_check()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with Version Info
        header_frame = QFrame(self)
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.pal['bg_main']};
                border: 1px solid {self.pal['border']};
                border-radius: 10px;
                padding: 12px 16px;
            }}
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title_lbl = QLabel("Sticky Notes Update Center", header_frame)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']}; background: transparent;")
        info_col.addWidget(title_lbl)

        ver_lbl = QLabel(f"Installed Version: <b>v{__version__}</b>", header_frame)
        ver_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']}; background: transparent;")
        info_col.addWidget(ver_lbl)

        self.source_lbl = QLabel("Feed: Auto-detecting...", header_frame)
        self.source_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']}; background: transparent;")
        info_col.addWidget(self.source_lbl)

        h_layout.addLayout(info_col)
        h_layout.addStretch()

        self.status_icon_lbl = QLabel(header_frame)
        self.status_icon_lbl.setPixmap(get_themed_icon("clock", role="primary", theme=self.theme, size=28).pixmap(28, 28))
        self.status_icon_lbl.setStyleSheet("background: transparent;")
        h_layout.addWidget(self.status_icon_lbl)

        layout.addWidget(header_frame)

        # Central Dynamic Card
        self.card = QFrame(self)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.pal['bg_surface']};
                border: 1px solid {self.pal['border']};
                border-radius: 10px;
                padding: 14px;
            }}
        """)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(8, 8, 8, 8)
        self.card_layout.setSpacing(10)
        layout.addWidget(self.card, 1)

        # Bottom row
        bottom_row = QHBoxLayout()
        
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

    def _clear_card(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # --- View States ---

    def _show_checking_state(self):
        self._clear_card()
        lbl = QLabel("🔍 Checking GitHub for updates...", self.card)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.pal['text_primary']}; margin-top: 40px;")
        self.card_layout.addWidget(lbl)
        self.card_layout.addStretch()

    def _show_up_to_date(self):
        self._clear_card()
        icon_lbl = QLabel(self.card)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(get_themed_icon("check", role="accent", theme=self.theme, size=36).pixmap(36, 36))
        self.card_layout.addWidget(icon_lbl)

        title = QLabel("You're on the latest version!", self.card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(title)

        desc = QLabel(f"Sticky Notes v{__version__} is currently up to date.", self.card)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']};")
        self.card_layout.addWidget(desc)

        self.card_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        check_again_btn = QPushButton(" Check Again", self.card)
        check_again_btn.setIcon(get_themed_icon("clock", role="btn_text", theme=self.theme, size=15))
        check_again_btn.setObjectName("SelectModeButton")
        check_again_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        check_again_btn.clicked.connect(self._start_check)
        btn_row.addWidget(check_again_btn)
        btn_row.addStretch()
        self.card_layout.addLayout(btn_row)

    def _show_update_available(self, release_info: dict):
        self._clear_card()
        self.release_info = release_info

        # Top banner
        top_row = QHBoxLayout()
        badge = QLabel(f" v{release_info['version']} Available! ", self.card)
        badge.setStyleSheet(f"""
            background-color: {self.pal['accent']};
            color: {self.pal['accent_text']};
            border-radius: 6px;
            font-weight: 700;
            font-size: 12px;
            padding: 4px 8px;
        """)
        top_row.addWidget(badge)

        date_str = release_info.get("published_at", "")[:10]
        if date_str:
            date_lbl = QLabel(f"Released: {date_str}", self.card)
            date_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']};")
            top_row.addWidget(date_lbl)

        top_row.addStretch()
        self.card_layout.addLayout(top_row)

        # Release Notes Browser
        notes_browser = QTextBrowser(self.card)
        notes_browser.setOpenExternalLinks(True)
        css = get_markdown_preview_css(self.theme)
        
        try:
            import markdown2
            body_html = markdown2.markdown(release_info.get("body", "No release notes provided."))
        except Exception:
            body_html = f"<pre>{release_info.get('body', '')}</pre>"

        notes_browser.setHtml(f"<html><head>{css}</head><body>{body_html}</body></html>")
        notes_browser.setStyleSheet(f"border: 1px solid {self.pal['border']}; border-radius: 8px; background: {self.pal['bg_main']};")
        self.card_layout.addWidget(notes_browser, 1)

        # Action row
        action_row = QHBoxLayout()
        
        gh_btn = QPushButton(" View on GitHub", self.card)
        gh_btn.setIcon(get_themed_icon("external_link", role="btn_text", theme=self.theme, size=15))
        gh_btn.setObjectName("SelectModeButton")
        gh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        gh_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(release_info.get("html_url", HOMEPAGE))))
        action_row.addWidget(gh_btn)

        action_row.addStretch()

        download_btn = QPushButton("⬇ Download & Install Update", self.card)
        download_btn.setObjectName("NewNoteButton")
        download_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        download_btn.clicked.connect(self._start_download)
        action_row.addWidget(download_btn)

        self.card_layout.addLayout(action_row)

    def _show_downloading_state(self):
        self._clear_card()
        
        title = QLabel(f"Downloading Sticky Notes v{self.release_info.get('version')}...", self.card)
        title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(title)

        self.progress_bar = QProgressBar(self.card)
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
        self.card_layout.addWidget(self.progress_bar)

        self.download_meta_lbl = QLabel("Connecting...", self.card)
        self.download_meta_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']};")
        self.card_layout.addWidget(self.download_meta_lbl)

        self.card_layout.addStretch()

        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        cancel_btn = QPushButton("Cancel Download", self.card)
        cancel_btn.setObjectName("SelectModeButton")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.clicked.connect(self._cancel_download)
        cancel_row.addWidget(cancel_btn)
        self.card_layout.addLayout(cancel_row)

    def _show_install_ready(self, zip_path: str):
        self._clear_card()
        self.downloaded_zip_path = zip_path
        file_path = Path(zip_path)
        is_exe = file_path.suffix.lower() == ".exe"
        is_frozen = getattr(sys, 'frozen', False)

        icon_lbl = QLabel(self.card)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(get_themed_icon("check", role="accent", theme=self.theme, size=36).pixmap(36, 36))
        self.card_layout.addWidget(icon_lbl)

        title = QLabel("Update Downloaded & Ready!", self.card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(title)

        if is_frozen:
            msg_text = "Sticky Notes will close, install the updated files, and automatically relaunch the newest version."
        elif is_exe:
            msg_text = "The standalone Windows installer has been downloaded. Click below to run the setup wizard and update Sticky Notes."
        else:
            msg_text = f"The update archive is ready at:\n{file_path}\n\nYou are running Sticky Notes in Python development mode."

        msg = QLabel(msg_text, self.card)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']};")
        msg.setWordWrap(True)
        self.card_layout.addWidget(msg)

        self.card_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if is_frozen:
            restart_btn = QPushButton("🚀 Restart & Apply Update Now", self.card)
            restart_btn.setObjectName("NewNoteButton")
            restart_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            restart_btn.clicked.connect(self._apply_update)
            btn_row.addWidget(restart_btn)
        elif is_exe:
            run_installer_btn = QPushButton("🚀 Run Installer Now", self.card)
            run_installer_btn.setObjectName("NewNoteButton")
            run_installer_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            run_installer_btn.clicked.connect(self._apply_update)
            btn_row.addWidget(run_installer_btn)

            open_folder_btn = QPushButton("📂 Open Folder", self.card)
            open_folder_btn.setObjectName("SelectModeButton")
            open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent))))
            btn_row.addWidget(open_folder_btn)
        else:
            open_folder_btn = QPushButton("📂 Open Downloaded Package", self.card)
            open_folder_btn.setObjectName("NewNoteButton")
            open_folder_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent))))
            btn_row.addWidget(open_folder_btn)

        btn_row.addStretch()
        self.card_layout.addLayout(btn_row)

    def _show_error_or_auth(self, error_msg: str, is_auth: bool):
        self._clear_card()

        title = QLabel("🔒 GitHub Authentication Required" if is_auth else "⚠️ Update Check Error", self.card)
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#E57373' if not is_auth else self.pal['accent']};")
        self.card_layout.addWidget(title)

        desc = QLabel(error_msg, self.card)
        desc.setStyleSheet(f"font-size: 12px; color: {self.pal['text_primary']};")
        desc.setWordWrap(True)
        self.card_layout.addWidget(desc)

        if is_auth:
            self._append_token_form()
        else:
            self.card_layout.addStretch()
            retry_btn = QPushButton("Retry Check", self.card)
            retry_btn.setObjectName("SelectModeButton")
            retry_btn.clicked.connect(self._start_check)
            self.card_layout.addWidget(retry_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _append_token_form(self):
        # Section 1: Public Mirror Feed URL
        mirror_header = QLabel("<b>🌐 Public Releases Mirror Feed</b>", self.card)
        mirror_header.setStyleSheet(f"font-size: 13px; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(mirror_header)

        mirror_info = QLabel("Allows checking for and downloading updates without needing a personal GitHub token.", self.card)
        mirror_info.setStyleSheet(f"font-size: 11px; color: {self.pal['text_secondary']};")
        mirror_info.setWordWrap(True)
        self.card_layout.addWidget(mirror_info)

        self.mirror_input = QLineEdit(self.card)
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
        self.card_layout.addWidget(self.mirror_input)

        mirror_btn_row = QHBoxLayout()
        test_mirror_btn = QPushButton("📡 Test Connection", self.card)
        test_mirror_btn.setObjectName("SelectModeButton")
        test_mirror_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        test_mirror_btn.clicked.connect(self._test_feed_connection)
        mirror_btn_row.addWidget(test_mirror_btn)

        reset_mirror_btn = QPushButton("↺ Default Mirror", self.card)
        reset_mirror_btn.setObjectName("SelectModeButton")
        reset_mirror_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_mirror_btn.clicked.connect(lambda: self.mirror_input.setText(DEFAULT_PUBLIC_MANIFEST_URL))
        mirror_btn_row.addWidget(reset_mirror_btn)

        mirror_btn_row.addStretch()
        self.card_layout.addLayout(mirror_btn_row)

        # Separator
        sep = QFrame(self.card)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {self.pal['border']}; margin: 4px 0;")
        self.card_layout.addWidget(sep)

        # Section 2: GitHub Personal Access Token
        token_header = QLabel("<b>🔒 Private GitHub Access Token (Optional)</b>", self.card)
        token_header.setStyleSheet(f"font-size: 13px; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(token_header)

        token_info = QLabel("Only required if querying the private repository directly instead of the public mirror.", self.card)
        token_info.setStyleSheet(f"font-size: 11px; color: {self.pal['text_secondary']};")
        token_info.setWordWrap(True)
        self.card_layout.addWidget(token_info)

        self.token_input = QLineEdit(self.card)
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
        self.card_layout.addWidget(self.token_input)

        row = QHBoxLayout()
        link_btn = QPushButton("🌐 Generate Token on GitHub", self.card)
        link_btn.setObjectName("SelectModeButton")
        link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/settings/tokens?type=beta")))
        row.addWidget(link_btn)

        row.addStretch()

        save_btn = QPushButton("💾 Save Settings & Check", self.card)
        save_btn.setObjectName("NewNoteButton")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.clicked.connect(self._save_token_and_check)
        row.addWidget(save_btn)

        self.card_layout.addLayout(row)
        self.card_layout.addStretch()

    def _show_token_section(self):
        self._clear_card()
        title = QLabel("⚙️ Software Update Configuration", self.card)
        title.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {self.pal['text_primary']};")
        self.card_layout.addWidget(title)
        self._append_token_form()

    def _test_feed_connection(self):
        url = self.mirror_input.text().strip() if hasattr(self, 'mirror_input') else ""
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please specify a mirror URL.")
            return

        import urllib.request
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    import json
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
                f"Could not connect to mirror at:\n{url}\n\nError: {str(e)}\n\nNote: If the public mirror repository has not yet been populated, you can configure a GitHub PAT or wait for the initial GitHub Actions release."
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
        # Prefer installer (.exe) if available for seamless silent update & desktop integration
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
        if not self.downloaded_zip_path:
            return
        file_path = Path(self.downloaded_zip_path)
        is_frozen = getattr(sys, 'frozen', False)
        is_exe = file_path.suffix.lower() == ".exe"

        if is_frozen:
            apply_update_and_restart(str(file_path))
        elif is_exe:
            import os
            if hasattr(os, 'startfile'):
                os.startfile(str(file_path))
            else:
                import subprocess
                subprocess.Popen([str(file_path)])
            self.accept()
        else:
            QMessageBox.information(
                self,
                "Development Mode",
                f"Update package successfully downloaded to:\n{file_path}\n\nIn development mode, please run git pull or extract the ZIP."
            )
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.parent)))
