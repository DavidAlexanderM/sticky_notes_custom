"""
share_dialog.py - Comprehensive Multi-App and OS Sharing Center for Sticky Notes.
Interfaces with Windows native protocols, messaging applications (Mail, WhatsApp, Telegram),
social platforms, and file export options with full theme integration.
"""

import re
import urllib.parse
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QScrollArea, QFrame,
    QGridLayout, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtGui import QDesktopServices, QCursor, QFont

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES, get_markdown_preview_css
    from ..icons import get_themed_icon
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES, get_markdown_preview_css
    from icons import get_themed_icon


def strip_markdown(text: str) -> str:
    """Removes common markdown formatting syntax for clean plain-text sharing."""
    # Remove headings
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold / italic
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    # Remove strikethrough
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    # Convert links [text](url) to text (url)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)
    # Remove inline code `code`
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class ShareNoteDialog(QDialog):
    """
    Rich modal sharing center enabling one-click transmission of sticky notes
    to Email, WhatsApp, Telegram, Facebook, X, system clipboard, and files.
    """
    def __init__(self, note_title: str, note_content: str, parent=None):
        super().__init__(parent)
        self.note_title = (note_title or "").strip() or "Untitled Note"
        self.note_content = note_content or ""
        self.plain_content = strip_markdown(self.note_content)

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])
        self.is_dark = self.theme_mgr.is_dark_mode()

        self.setWindowTitle(f"Share Note - {self.note_title}")
        self.resize(520, 560)
        self.setMinimumSize(440, 480)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # 1. Note Summary Card
        summary_card = QFrame(self)
        summary_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.pal['bg_main']};
                border: 1px solid {self.pal['border']};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        sum_layout = QVBoxLayout(summary_card)
        sum_layout.setSpacing(6)

        title_lbl = QLabel(self.note_title, summary_card)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.pal['text_primary']}; background: transparent;")
        title_lbl.setWordWrap(True)
        sum_layout.addWidget(title_lbl)

        # Character & Word count
        words = len(self.plain_content.split()) if self.plain_content else 0
        chars = len(self.plain_content)
        meta_text = f"📊 {words} words • {chars} characters"
        
        snippet = self.plain_content[:140] + ("..." if len(self.plain_content) > 140 else "")
        if snippet:
            snip_lbl = QLabel(f'"{snippet}"', summary_card)
            snip_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']}; font-style: italic; background: transparent;")
            snip_lbl.setWordWrap(True)
            sum_layout.addWidget(snip_lbl)

        meta_lbl = QLabel(meta_text, summary_card)
        meta_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {self.pal['text_muted']}; background: transparent;")
        sum_layout.addWidget(meta_lbl)

        main_layout.addWidget(summary_card)

        # 2. Action Groups (Scrollable)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(16)

        # Section A: Send to App / Messaging
        sec1_title = QLabel("Send to Apps & Messaging", content_widget)
        sec1_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(sec1_title)

        grid_apps = QGridLayout()
        grid_apps.setSpacing(10)

        # Email
        self.btn_mail = self._create_action_btn(" Default Email Client", "mail", "Open Outlook, Windows Mail, or Thunderbird")
        self.btn_mail.clicked.connect(self._share_via_email)
        grid_apps.addWidget(self.btn_mail, 0, 0)

        # WhatsApp
        self.btn_whatsapp = self._create_action_btn(" WhatsApp", "message_circle", "Send via WhatsApp Desktop or Web")
        self.btn_whatsapp.clicked.connect(self._share_via_whatsapp)
        grid_apps.addWidget(self.btn_whatsapp, 0, 1)

        # Telegram
        self.btn_telegram = self._create_action_btn(" Telegram", "send", "Send via Telegram Desktop or Web")
        self.btn_telegram.clicked.connect(self._share_via_telegram)
        grid_apps.addWidget(self.btn_telegram, 1, 0)

        # Facebook
        self.btn_facebook = self._create_action_btn(" Facebook", "globe", "Share to Facebook feed or messages")
        self.btn_facebook.clicked.connect(self._share_via_facebook)
        grid_apps.addWidget(self.btn_facebook, 1, 1)

        # X / Twitter
        self.btn_x = self._create_action_btn(" X (Twitter)", "external_link", "Post note snippet to X")
        self.btn_x.clicked.connect(self._share_via_x)
        grid_apps.addWidget(self.btn_x, 2, 0, 1, 2)

        content_layout.addLayout(grid_apps)

        # Section B: Clipboard & File Export
        sec2_title = QLabel("Clipboard & File Export", content_widget)
        sec2_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 8px;")
        content_layout.addWidget(sec2_title)

        grid_files = QGridLayout()
        grid_files.setSpacing(10)

        # Copy Markdown
        self.btn_copy_md = self._create_action_btn(" Copy Markdown", "copy", "Copy formatted markdown syntax")
        self.btn_copy_md.clicked.connect(self._copy_markdown)
        grid_files.addWidget(self.btn_copy_md, 0, 0)

        # Copy Plain Text
        self.btn_copy_txt = self._create_action_btn(" Copy Plain Text", "copy", "Copy text without markdown symbols")
        self.btn_copy_txt.clicked.connect(self._copy_plain_text)
        grid_files.addWidget(self.btn_copy_txt, 0, 1)

        # Save as Markdown
        self.btn_save_md = self._create_action_btn(" Export as .md", "file_text", "Save as local Markdown file")
        self.btn_save_md.clicked.connect(self._export_markdown_file)
        grid_files.addWidget(self.btn_save_md, 1, 0)

        # Save as HTML
        self.btn_save_html = self._create_action_btn(" Export as .html", "globe", "Save as styled standalone webpage")
        self.btn_save_html.clicked.connect(self._export_html_file)
        grid_files.addWidget(self.btn_save_html, 1, 1)

        content_layout.addLayout(grid_files)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # 3. Status Toast / Feedback Label
        self.status_feedback = QLabel("", self)
        self.status_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_feedback.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.pal['accent']};")
        self.status_feedback.setVisible(False)
        main_layout.addWidget(self.status_feedback)

        # 4. Bottom Controls
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        close_btn = QPushButton("Close", self)
        close_btn.setObjectName("SelectModeButton")
        close_btn.setFixedSize(90, 32)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        main_layout.addLayout(bottom_row)

    def _create_action_btn(self, text: str, icon_name: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setIcon(get_themed_icon(icon_name, role="btn_text", theme=self.theme, size=16))
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setFixedHeight(40)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.pal['btn_bg']};
                color: {self.pal['btn_text']};
                border: 1px solid {self.pal['border']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {self.pal['btn_hover']};
                border-color: {self.pal['accent']};
            }}
        """)
        return btn

    def _show_toast(self, message: str):
        """Displays transient status feedback."""
        self.status_feedback.setText(f"✓ {message}")
        self.status_feedback.setVisible(True)

    # --- Sharing Handlers ---

    def _get_full_text(self) -> str:
        return f"{self.note_title}\n\n{self.plain_content}" if self.plain_content else self.note_title

    def _get_full_markdown(self) -> str:
        return f"# {self.note_title}\n\n{self.note_content}" if self.note_content else f"# {self.note_title}"

    def _share_via_email(self):
        subject = urllib.parse.quote(self.note_title)
        body = urllib.parse.quote(self.plain_content)
        mailto_url = f"mailto:?subject={subject}&body={body}"
        QDesktopServices.openUrl(QUrl(mailto_url))
        self._show_toast("Launched Email client!")

    def _share_via_whatsapp(self):
        text = urllib.parse.quote(self._get_full_text())
        whatsapp_url = f"https://api.whatsapp.com/send?text={text}"
        QDesktopServices.openUrl(QUrl(whatsapp_url))
        self._show_toast("Opening WhatsApp...")

    def _share_via_telegram(self):
        text = urllib.parse.quote(self._get_full_text())
        telegram_url = f"https://t.me/share/url?url=&text={text}"
        QDesktopServices.openUrl(QUrl(telegram_url))
        self._show_toast("Opening Telegram...")

    def _share_via_facebook(self):
        text = urllib.parse.quote(self._get_full_text())
        # Facebook share dialog
        fb_url = f"https://www.facebook.com/sharer/sharer.php?quote={text}"
        QDesktopServices.openUrl(QUrl(fb_url))
        self._show_toast("Opening Facebook...")

    def _share_via_x(self):
        full = self._get_full_text()
        snippet = (full[:260] + "...") if len(full) > 260 else full
        text = urllib.parse.quote(snippet)
        x_url = f"https://twitter.com/intent/tweet?text={text}"
        QDesktopServices.openUrl(QUrl(x_url))
        self._show_toast("Opening X...")

    def _copy_markdown(self):
        QApplication.clipboard().setText(self._get_full_markdown())
        self._show_toast("Markdown copied to clipboard!")

    def _copy_plain_text(self):
        QApplication.clipboard().setText(self._get_full_text())
        self._show_toast("Plain text copied to clipboard!")

    def _export_markdown_file(self):
        safe_title = "".join(c for c in self.note_title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as Markdown", f"{safe_title}.md", "Markdown Files (*.md)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._get_full_markdown())
            self._show_toast(f"Saved to {Path(file_path).name}!")

    def _export_html_file(self):
        try:
            import markdown2
            html_body = markdown2.markdown(self.note_content, extras=["fenced-code-blocks", "tables", "task_list", "strike"])
        except Exception:
            html_body = f"<pre>{self.note_content}</pre>"

        safe_title = "".join(c for c in self.note_title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Note as HTML", f"{safe_title}.html", "HTML Files (*.html)")
        if file_path:
            css = get_markdown_preview_css(self.theme)
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.note_title}</title>
    {css}
</head>
<body>
    <h1>{self.note_title}</h1>
    {html_body}
</body>
</html>"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            self._show_toast(f"Saved to {Path(file_path).name}!")
