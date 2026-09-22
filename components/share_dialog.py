"""
share_dialog.py - Comprehensive Multi-App and OS Sharing Center for Sticky Notes.
Features direct Windows OS-level sharing integration (Windows System Share flyout,
'Open With' system dialog, Phone Link SMS), native desktop application protocol handlers
(WhatsApp Desktop, Telegram Desktop, Mail, Teams) with zero browser redirects,
native interactive drag-and-drop into external apps, and rich clipboard/file export.
"""

import os
import re
import sys
import zipfile
import tempfile
import subprocess
import urllib.parse
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, QMimeData
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QScrollArea, QFrame,
    QGridLayout, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtGui import QDesktopServices, QCursor, QFont, QImage, QDrag

try:
    from ..theme_manager import get_theme_manager
    from ..styles import THEME_PALETTES, get_markdown_preview_css
    from ..icons import get_themed_icon
    from ..media_manager import get_attachments_dir
except ImportError:
    from theme_manager import get_theme_manager
    from styles import THEME_PALETTES, get_markdown_preview_css
    from icons import get_themed_icon
    from media_manager import get_attachments_dir


def strip_markdown(text: str) -> str:
    """Removes common markdown formatting syntax for clean plain-text sharing without broken local links."""
    # Convert local file image embeds ![alt](file:///...) to [Image: alt] or [Image]
    def _clean_img(match):
        alt = match.group(1).strip()
        url = match.group(2).strip()
        if url.startswith("file:") or "attachments" in url or re.search(r'\.(png|jpe?g|gif|webp|bmp)', url, re.I):
            label = alt if alt else "Image"
            return f"[{label}]"
        return f"[{alt}] ({url})" if alt else f"({url})"

    text = re.sub(r'!\[(.*?)\]\((.*?)\)', _clean_img, text)

    # Convert links [text](url) -> if local file, keep [text], if web url keep text (url)
    def _clean_link(match):
        label = match.group(1).strip()
        url = match.group(2).strip()
        if url.startswith("file:") or "attachments" in url:
            return f"[{label}]"
        return f"{label} ({url})" if label else url

    text = re.sub(r'\[(.*?)\]\((.*?)\)', _clean_link, text)

    # Remove headings
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold / italic
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    # Remove strikethrough
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    # Remove inline code `code`
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_media_attachments(content: str) -> List[Path]:
    """
    Extracts existing local media attachment file Paths from markdown content.
    Supports file:/// URIs, relative attachments/ paths, and bare filenames.
    """
    if not content:
        return []

    attachments_dir = get_attachments_dir()
    found: List[Path] = []
    seen = set()

    patterns = [
        r'\[.*?\]\((file:///[^)]+)\)',
        r'!\[.*?\]\((file:///[^)]+)\)',
        r'\[.*?\]\((attachments/[^)]+)\)',
        r'!\[.*?\]\((attachments/[^)]+)\)',
        r'\[.*?\]\((attachments\\[^)]+)\)',
        r'!\[.*?\]\((attachments\\[^)]+)\)',
    ]

    raw_urls = []
    for pat in patterns:
        for match in re.findall(pat, content):
            raw_urls.append(match.strip())

    for u in raw_urls:
        p: Path = None
        if u.startswith("file:"):
            local = QUrl(u).toLocalFile()
            if local:
                p = Path(local)
        elif u.startswith("attachments/") or u.startswith("attachments\\"):
            p = (attachments_dir / Path(u).name).resolve()
        else:
            p = (attachments_dir / Path(u).name).resolve()

        if p and p.exists() and p.is_file():
            canon = str(p.resolve()).lower()
            if canon not in seen:
                seen.add(canon)
                found.append(p)

    return found


def stage_share_files(title: str, content: str, attachments: Optional[List[Path]] = None) -> Path:
    """
    Writes a clean, formatted text export of the note to a temporary staging
    folder so Windows Shell and external applications can access the file.
    """
    share_dir = Path(tempfile.gettempdir()) / "StickyNotes_Share"
    share_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
    staged_path = share_dir / f"{safe_title}.txt"
    try:
        full_text = f"{title}\n\n{content}".strip()
        staged_path.write_text(full_text, encoding="utf-8")
    except Exception:
        pass
    return staged_path


def invoke_windows_share_ui(file_path: Path, hwnd: Optional[int] = None) -> bool:
    """
    Invokes the native Windows OS Share flyout on the given file path
    via the Windows Shell Application COM interface (&Share verb).
    """
    if sys.platform != "win32":
        return False
    try:
        if hwnd:
            try:
                import win32gui
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("Shell.Application")
        folder = shell.Namespace(str(file_path.parent.resolve()))
        if not folder:
            return False
        item = folder.ParseName(file_path.name)
        if not item:
            return False
        for v in item.Verbs():
            name_clean = v.Name.lower().replace("&", "").strip()
            if name_clean in ("share", "compartir", "partager", "freigeben"):
                v.DoIt()
                return True
    except Exception as e:
        print(f"[WARN] invoke_windows_share_ui failed: {e}")
    return False


def invoke_windows_open_with(file_path: Path) -> bool:
    """
    Opens the official Windows 'Open With...' system dialog for the specified file.
    """
    if sys.platform != "win32":
        return False
    try:
        subprocess.Popen(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", str(file_path.resolve())])
        return True
    except Exception as e:
        print(f"[WARN] invoke_windows_open_with failed: {e}")
    return False


class DraggableNoteChip(QFrame):
    """
    Interactive UI card that allows clicking and dragging the note content
    or its attachments directly into external Windows applications (WhatsApp Desktop,
    Telegram, Outlook, Windows Explorer, Word, etc.).
    """
    def __init__(self, get_drag_data_callback, pal: dict, parent=None):
        super().__init__(parent)
        self.get_drag_data = get_drag_data_callback
        self.pal = pal
        self._drag_start_pos = None
        self.setObjectName("DraggableNoteChip")
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self.setToolTip("Click and drag this note directly into WhatsApp, Telegram, Outlook, or Windows Explorer")

        self.setStyleSheet(f"""
            QFrame#DraggableNoteChip {{
                background-color: {self.pal['bg_surface']};
                border: 2px dashed {self.pal['accent']};
                border-radius: 8px;
                padding: 10px 14px;
            }}
            QFrame#DraggableNoteChip:hover {{
                background-color: {self.pal['btn_hover']};
                border-style: solid;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(get_themed_icon("paperclip", role="accent", theme=self.pal.get("theme", "light"), size=22).pixmap(22, 22))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel("✋ Drag Note to Any Desktop App", self)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {self.pal['accent']}; border: none; background: transparent;")
        text_col.addWidget(title_lbl)

        desc_lbl = QLabel("Click and drop into WhatsApp Desktop, Telegram, Outlook, or File Explorer", self)
        desc_lbl.setStyleSheet(f"font-size: 11px; color: {self.pal['text_muted']}; border: none; background: transparent;")
        text_col.addWidget(desc_lbl)
        layout.addLayout(text_col, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not self._drag_start_pos:
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = self.get_drag_data()
        if mime:
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self._drag_start_pos = None


class ShareNoteDialog(QDialog):
    """
    Rich modal sharing center enabling one-click transmission of sticky notes
    using native Windows OS sharing, direct desktop app protocols (WhatsApp Desktop,
    Telegram Desktop, Email, Teams, Phone Link SMS), drag-and-drop, and rich clipboard/file export.
    """
    def __init__(self, note_title: str, note_content: str, parent=None):
        super().__init__(parent)
        self.note_title = (note_title or "").strip() or "Untitled Note"
        self.note_content = note_content or ""
        self.plain_content = strip_markdown(self.note_content)

        # Detect and extract media attachments
        self.attachments = extract_media_attachments(self.note_content)
        self.image_attachments = [p for p in self.attachments if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')]
        self.audio_attachments = [p for p in self.attachments if p.suffix.lower() in ('.wav', '.mp3', '.m4a', '.aac', '.ogg')]
        self.video_attachments = [p for p in self.attachments if p.suffix.lower() in ('.mp4', '.webm', '.mkv', '.mov')]

        self.btn_copy_image = None
        self.btn_copy_files = None
        self.btn_export_zip = None
        self.btn_open_folder = None

        self.theme_mgr = get_theme_manager()
        self.theme = self.theme_mgr.current_theme
        self.pal = THEME_PALETTES.get(self.theme, THEME_PALETTES["light"])
        self.is_dark = self.theme_mgr.is_dark_mode()

        self.setWindowTitle(f"Share Note - {self.note_title}")
        self.resize(540, 680)
        self.setMinimumSize(460, 560)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

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
        meta_parts = [f"📊 {words} words • {chars} characters"]

        if self.attachments:
            att_desc = []
            if self.image_attachments:
                att_desc.append(f"{len(self.image_attachments)} image{'s' if len(self.image_attachments) > 1 else ''}")
            if self.audio_attachments:
                att_desc.append(f"{len(self.audio_attachments)} audio note{'s' if len(self.audio_attachments) > 1 else ''}")
            if self.video_attachments:
                att_desc.append(f"{len(self.video_attachments)} video{'s' if len(self.video_attachments) > 1 else ''}")
            meta_parts.append(f"📎 {len(self.attachments)} attached ({', '.join(att_desc)})")

        snippet = self.plain_content[:140] + ("..." if len(self.plain_content) > 140 else "")
        if snippet:
            snip_lbl = QLabel(f'"{snippet}"', summary_card)
            snip_lbl.setStyleSheet(f"font-size: 12px; color: {self.pal['text_secondary']}; font-style: italic; background: transparent;")
            snip_lbl.setWordWrap(True)
            sum_layout.addWidget(snip_lbl)

        meta_lbl = QLabel(" • ".join(meta_parts), summary_card)
        meta_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {self.pal['text_muted']}; background: transparent;")
        sum_layout.addWidget(meta_lbl)

        main_layout.addWidget(summary_card)

        # 2. Interactive Drag & Drop Zone
        self.drag_chip = DraggableNoteChip(self._get_drag_mime_data, self.pal, self)
        main_layout.addWidget(self.drag_chip)

        # 3. Action Groups (Scrollable)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(14)

        # Section A: Windows OS Native Integration
        sec_os_title = QLabel("Windows OS Native Sharing", content_widget)
        sec_os_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px;")
        content_layout.addWidget(sec_os_title)

        grid_os = QGridLayout()
        grid_os.setSpacing(10)

        # Windows System Share Sheet
        self.btn_win_share = self._create_action_btn("🪟 Windows Share Flyout", "share", "Open official Windows 10/11 Share UI (Nearby Share, Store Apps, Bluetooth)")
        self.btn_win_share.clicked.connect(self._share_via_windows_system)
        grid_os.addWidget(self.btn_win_share, 0, 0)

        # Open With Dialog
        self.btn_open_with = self._create_action_btn("⚙️ Open With...", "external_link", "Choose any installed Windows app to open or process this note")
        self.btn_open_with.clicked.connect(self._share_via_open_with)
        grid_os.addWidget(self.btn_open_with, 0, 1)

        # Phone Link / SMS
        self.btn_sms = self._create_action_btn("📱 Phone Link (SMS)", "smartphone", "Send note as text message via Windows Phone Link")
        self.btn_sms.clicked.connect(self._share_via_sms)
        grid_os.addWidget(self.btn_sms, 1, 0)

        # Reveal in Explorer
        self.btn_open_folder = self._create_action_btn("📁 Reveal in Explorer", "folder", "Locate note file and attachments in Windows File Explorer")
        self.btn_open_folder.clicked.connect(self._open_attachments_folder)
        grid_os.addWidget(self.btn_open_folder, 1, 1)

        content_layout.addLayout(grid_os)

        # Section B: Direct Desktop Apps (Native Protocols - No Web Redirects)
        sec_apps_title = QLabel("Direct Desktop Applications", content_widget)
        sec_apps_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 6px;")
        content_layout.addWidget(sec_apps_title)

        grid_apps = QGridLayout()
        grid_apps.setSpacing(10)

        # WhatsApp Desktop
        self.btn_whatsapp = self._create_action_btn(" WhatsApp Desktop", "message_circle", "Send directly via native WhatsApp Desktop app (Auto-copies images/files for Ctrl+V)")
        self.btn_whatsapp.clicked.connect(self._share_via_whatsapp)
        grid_apps.addWidget(self.btn_whatsapp, 0, 0)

        # Telegram Desktop
        self.btn_telegram = self._create_action_btn(" Telegram Desktop", "send", "Send directly via native Telegram Desktop app (Auto-copies images/files for Ctrl+V)")
        self.btn_telegram.clicked.connect(self._share_via_telegram)
        grid_apps.addWidget(self.btn_telegram, 0, 1)

        # Email
        self.btn_mail = self._create_action_btn(" Default Email Client", "mail", "Open Outlook, Windows Mail, or Thunderbird")
        self.btn_mail.clicked.connect(self._share_via_email)
        grid_apps.addWidget(self.btn_mail, 1, 0)

        # Microsoft Teams
        self.btn_teams = self._create_action_btn(" Microsoft Teams", "users", "Start a chat in Microsoft Teams")
        self.btn_teams.clicked.connect(self._share_via_teams)
        grid_apps.addWidget(self.btn_teams, 1, 1)

        # Facebook & X (Retained for web sharing)
        self.btn_facebook = self._create_action_btn(" Facebook", "globe", "Share to Facebook feed or messages")
        self.btn_facebook.clicked.connect(self._share_via_facebook)
        grid_apps.addWidget(self.btn_facebook, 2, 0)

        self.btn_x = self._create_action_btn(" X (Twitter)", "external_link", "Post note snippet to X")
        self.btn_x.clicked.connect(self._share_via_x)
        grid_apps.addWidget(self.btn_x, 2, 1)

        content_layout.addLayout(grid_apps)

        # Section C: Media & Attachments (when attachments exist)
        if self.attachments:
            sec_media_title = QLabel("Media & Attachments", content_widget)
            sec_media_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 6px;")
            content_layout.addWidget(sec_media_title)

            grid_media = QGridLayout()
            grid_media.setSpacing(10)

            # Copy Image to Clipboard
            if self.image_attachments:
                self.btn_copy_image = self._create_action_btn(" Copy Image to Clipboard", "image", "Copy image bitmap for direct Ctrl+V pasting into chat")
                self.btn_copy_image.clicked.connect(self._copy_image_to_clipboard)
                grid_media.addWidget(self.btn_copy_image, 0, 0)
            else:
                self.btn_copy_image = None

            # Copy Media Files to Clipboard
            self.btn_copy_files = self._create_action_btn(" Copy Media File(s)", "paperclip", "Copy attached media files to clipboard for chat or Explorer")
            self.btn_copy_files.clicked.connect(self._copy_files_to_clipboard)
            col = 1 if self.image_attachments else 0
            grid_media.addWidget(self.btn_copy_files, 0, col)

            # Export Note Package (.zip)
            self.btn_export_zip = self._create_action_btn(" Export Package (.zip)", "archive", "Export ZIP bundle containing note and all media attachments")
            self.btn_export_zip.clicked.connect(self._export_zip_package)
            grid_media.addWidget(self.btn_export_zip, 1, 0, 1, 2 if not self.image_attachments else 1)

            content_layout.addLayout(grid_media)

        # Section D: Clipboard & Document Export
        sec_files_title = QLabel("Clipboard & Document Export", content_widget)
        sec_files_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.pal['accent']}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 6px;")
        content_layout.addWidget(sec_files_title)

        grid_files = QGridLayout()
        grid_files.setSpacing(10)

        # Copy Rich Text (Formatted)
        self.btn_copy_rich = self._create_action_btn(" Copy Rich Text", "copy", "Copy formatted text for Word, Outlook, and WordPad")
        self.btn_copy_rich.clicked.connect(self._copy_rich_text)
        grid_files.addWidget(self.btn_copy_rich, 0, 0)

        # Copy Plain Text
        self.btn_copy_txt = self._create_action_btn(" Copy Plain Text", "copy", "Copy text without markdown symbols")
        self.btn_copy_txt.clicked.connect(self._copy_plain_text)
        grid_files.addWidget(self.btn_copy_txt, 0, 1)

        # Copy Markdown
        self.btn_copy_md = self._create_action_btn(" Copy Markdown", "copy", "Copy raw markdown syntax")
        self.btn_copy_md.clicked.connect(self._copy_markdown)
        grid_files.addWidget(self.btn_copy_md, 1, 0)

        # Save as Markdown
        self.btn_save_md = self._create_action_btn(" Export as .md", "file_text", "Save as local Markdown file")
        self.btn_save_md.clicked.connect(self._export_markdown_file)
        grid_files.addWidget(self.btn_save_md, 1, 1)

        # Save as HTML
        self.btn_save_html = self._create_action_btn(" Export as .html", "globe", "Save as styled standalone webpage")
        self.btn_save_html.clicked.connect(self._export_html_file)
        grid_files.addWidget(self.btn_save_html, 2, 0, 1, 2)

        content_layout.addLayout(grid_files)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # 4. Status Toast / Feedback Label
        self.status_feedback = QLabel("", self)
        self.status_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_feedback.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.pal['accent']};")
        self.status_feedback.setVisible(False)
        main_layout.addWidget(self.status_feedback)

        # 5. Bottom Controls
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

    # --- Helpers ---

    def _get_full_text(self) -> str:
        return f"{self.note_title}\n\n{self.plain_content}" if self.plain_content else self.note_title

    def _get_full_markdown(self) -> str:
        return f"# {self.note_title}\n\n{self.note_content}" if self.note_content else f"# {self.note_title}"

    def _get_full_html(self) -> str:
        try:
            import markdown2
            html_body = markdown2.markdown(self.note_content, extras=["fenced-code-blocks", "tables", "task_list", "strike"])
        except Exception:
            html_body = f"<p>{self.plain_content}</p>"
        return f"<h3>{self.note_title}</h3>\n{html_body}"

    def _stage_note_file(self) -> Path:
        """Writes note to temporary staging directory for shell operations."""
        return stage_share_files(self.note_title, self.plain_content, self.attachments)

    def _get_drag_mime_data(self) -> QMimeData:
        """Produces rich multi-format MIME data for native Windows drag & drop."""
        mime = QMimeData()
        mime.setText(self._get_full_text())
        mime.setHtml(self._get_full_html())
        staged = self._stage_note_file()
        urls = [QUrl.fromLocalFile(str(staged))]
        for p in self.attachments:
            urls.append(QUrl.fromLocalFile(str(p)))
        mime.setUrls(urls)
        return mime

    # --- OS-Level & Protocol Sharing Handlers ---

    def _share_via_windows_system(self):
        """Invokes official Windows 10/11 Share UI flyout."""
        staged = self._stage_note_file()
        success = invoke_windows_share_ui(staged, hwnd=int(self.winId()))
        if success:
            self._show_toast("Opened Windows System Share flyout!")
        else:
            # Fallback to Open With dialog if Shell Share verb not available
            invoke_windows_open_with(staged)
            self._show_toast("Opened Windows 'Open With' dialog.")

    def _share_via_open_with(self):
        """Opens Windows 'Open With' system dialog."""
        staged = self._stage_note_file()
        invoke_windows_open_with(staged)
        self._show_toast("Opened Windows 'Open With' dialog.")

    def _share_via_sms(self):
        """Launches Windows Phone Link / SMS messaging."""
        text = urllib.parse.quote(self._get_full_text())
        sms_uri = f"sms:?body={text}"
        QDesktopServices.openUrl(QUrl(sms_uri))
        self._show_toast("Opening Windows Phone Link / SMS...")

    def _share_via_whatsapp(self):
        """Directly invokes WhatsApp Desktop native protocol, auto-copying media to clipboard."""
        toast_extra = ""
        if self.image_attachments:
            img = QImage(str(self.image_attachments[0]))
            if not img.isNull():
                QApplication.clipboard().setImage(img)
                toast_extra = " • Image ready to paste (Ctrl+V)"
        elif self.attachments:
            self._copy_files_to_clipboard()
            toast_extra = " • Files ready to paste (Ctrl+V)"

        text = urllib.parse.quote(self._get_full_text())
        native_uri = f"whatsapp://send?text={text}"

        launched = False
        try:
            launched = QDesktopServices.openUrl(QUrl(native_uri))
        except Exception:
            launched = False

        if not launched:
            # Fallback to web redirect only if native app failed to launch
            web_uri = f"https://web.whatsapp.com/send?text={text}"
            QDesktopServices.openUrl(QUrl(web_uri))
            self._show_toast(f"Opening WhatsApp Web...{toast_extra}")
        else:
            self._show_toast(f"Launched WhatsApp Desktop!{toast_extra}")

    def _share_via_telegram(self):
        """Directly invokes Telegram Desktop native protocol, auto-copying media to clipboard."""
        toast_extra = ""
        if self.image_attachments:
            img = QImage(str(self.image_attachments[0]))
            if not img.isNull():
                QApplication.clipboard().setImage(img)
                toast_extra = " • Image ready to paste (Ctrl+V)"
        elif self.attachments:
            self._copy_files_to_clipboard()
            toast_extra = " • Files ready to paste (Ctrl+V)"

        text = urllib.parse.quote(self._get_full_text())
        native_uri = f"tg://msg?text={text}"

        launched = False
        try:
            launched = QDesktopServices.openUrl(QUrl(native_uri))
        except Exception:
            launched = False

        if not launched:
            # Fallback to web redirect only if native app failed to launch
            web_uri = f"https://t.me/share/url?url=&text={text}"
            QDesktopServices.openUrl(QUrl(web_uri))
            self._show_toast(f"Opening Telegram Web...{toast_extra}")
        else:
            self._show_toast(f"Launched Telegram Desktop!{toast_extra}")

    def _share_via_email(self):
        """Directly invokes native default email client via mailto:."""
        subject = urllib.parse.quote(self.note_title)
        body = urllib.parse.quote(self.plain_content)
        mailto_url = f"mailto:?subject={subject}&body={body}"
        QDesktopServices.openUrl(QUrl(mailto_url))
        self._show_toast("Launched Email client!")

    def _share_via_teams(self):
        """Directly invokes Microsoft Teams chat."""
        text = urllib.parse.quote(self._get_full_text())
        native_uri = f"msteams:/l/chat/0/0?users=&message={text}"
        launched = False
        try:
            launched = QDesktopServices.openUrl(QUrl(native_uri))
        except Exception:
            launched = False

        if not launched:
            web_uri = f"https://teams.microsoft.com/l/chat/0/0?message={text}"
            QDesktopServices.openUrl(QUrl(web_uri))
            self._show_toast("Opening Microsoft Teams Web...")
        else:
            self._show_toast("Launched Microsoft Teams Desktop!")

    def _share_via_facebook(self):
        text = urllib.parse.quote(self._get_full_text())
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

    def _copy_image_to_clipboard(self):
        """Copies primary image attachment to Windows clipboard as a raw bitmap."""
        if not self.image_attachments:
            return
        img_path = str(self.image_attachments[0])
        img = QImage(img_path)
        if not img.isNull():
            QApplication.clipboard().setImage(img)
            self._show_toast("Image copied! Paste (Ctrl+V) directly into WhatsApp, Telegram, or any chat.")
        else:
            self._show_toast("Could not read image attachment.")

    def _copy_files_to_clipboard(self):
        """Copies file URLs and text to clipboard so pasting attaches the real files."""
        if not self.attachments:
            return
        mime = QMimeData()
        urls = [QUrl.fromLocalFile(str(p)) for p in self.attachments]
        mime.setUrls(urls)
        mime.setText(self._get_full_text())
        QApplication.clipboard().setMimeData(mime)
        count = len(self.attachments)
        self._show_toast(f"{count} file{'s' if count > 1 else ''} copied! Paste (Ctrl+V) into chat or folder.")

    def _open_attachments_folder(self):
        """Opens Windows Explorer with the note's staged file or attachments selected."""
        target = self.attachments[0] if self.attachments else self._stage_note_file()
        if sys.platform == "win32":
            subprocess.Popen(f'explorer /select,"{target}"')
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent)))
        self._show_toast("Opened location in File Explorer!")

    def _export_zip_package(self):
        """Exports a standalone ZIP containing note markdown and all embedded media attachments."""
        safe_title = "".join(c for c in self.note_title if c.isalnum() or c in (' ', '-', '_')).strip() or "note"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Note Package (.zip)", f"{safe_title}_package.zip", "Zip Archives (*.zip)")
        if not file_path:
            return

        try:
            portable_content = self.note_content
            for p in self.attachments:
                file_url = QUrl.fromLocalFile(str(p)).toString()
                portable_content = portable_content.replace(file_url, f"attachments/{p.name}")
                portable_content = portable_content.replace(str(p), f"attachments/{p.name}")

            full_md = f"# {self.note_title}\n\n{portable_content}" if portable_content else f"# {self.note_title}"

            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{safe_title}.md", full_md.encode("utf-8"))
                for p in self.attachments:
                    zf.write(p, arcname=f"attachments/{p.name}")

            self._show_toast(f"Exported package to {Path(file_path).name}!")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export note package: {e}")

    def _copy_rich_text(self):
        """Copies multi-format MIME data (text + HTML + image) for Word, Outlook, and rich editors."""
        mime = QMimeData()
        mime.setText(self._get_full_text())
        mime.setHtml(self._get_full_html())
        if self.image_attachments:
            img = QImage(str(self.image_attachments[0]))
            if not img.isNull():
                mime.setImageData(img)
        QApplication.clipboard().setMimeData(mime)
        self._show_toast("Rich formatted text copied to clipboard!")

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
