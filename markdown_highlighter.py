"""
markdown_highlighter.py - Live In-Editor Markdown Syntax Highlighter.
Subclasses QSyntaxHighlighter to provide real-time formatting in the raw text editor:
Headings, Bold, Italic, Strikethrough, Code Blocks, Tasks, and Dimmed Media URLs.
"""

import re
from typing import List, Tuple
from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextDocument, QTextCharFormat, 
    QFont, QColor
)

try:
    from .styles import THEME_PALETTES
    from .theme_manager import get_theme_manager
except ImportError:
    from styles import THEME_PALETTES
    from theme_manager import get_theme_manager


class MarkdownHighlighter(QSyntaxHighlighter):
    """
    Real-time syntax highlighter for Markdown in QTextEdit.
    Supports multi-theme color adaptation.
    """

    def __init__(self, document: QTextDocument, theme: str = "light"):
        super().__init__(document)
        self.current_theme = theme
        self.rules: List[Tuple[QRegularExpression, QTextCharFormat, int]] = []
        self._init_formats()

    def set_theme(self, theme: str):
        """Re-initializes formats with new theme palette and triggers rehighlight."""
        self.current_theme = theme
        self._init_formats()
        self.rehighlight()

    def _init_formats(self):
        pal = THEME_PALETTES.get(self.current_theme, THEME_PALETTES["light"])
        
        accent_col = QColor(pal.get("accent", "#2563EB"))
        primary_col = QColor(pal.get("text_primary", "#0F172A"))
        secondary_col = QColor(pal.get("text_secondary", "#334155"))
        muted_col = QColor(pal.get("text_muted", "#64748B"))

        # Base font family
        code_font_family = "Cascadia Code, Consolas, Courier New, monospace"

        # 1. Headings (# H1, ## H2, ### H3)
        self.fmt_h1 = QTextCharFormat()
        self.fmt_h1.setFontWeight(QFont.Weight.Bold)
        self.fmt_h1.setForeground(accent_col)
        self.fmt_h1.setProperty(QTextCharFormat.Property.FontPointSize, 17.0)

        self.fmt_h2 = QTextCharFormat()
        self.fmt_h2.setFontWeight(QFont.Weight.Bold)
        self.fmt_h2.setForeground(accent_col)
        self.fmt_h2.setProperty(QTextCharFormat.Property.FontPointSize, 15.0)

        self.fmt_h3 = QTextCharFormat()
        self.fmt_h3.setFontWeight(QFont.Weight.Bold)
        self.fmt_h3.setForeground(accent_col)
        self.fmt_h3.setProperty(QTextCharFormat.Property.FontPointSize, 13.5)

        # 2. Bold (**bold** or __bold__)
        self.fmt_bold = QTextCharFormat()
        self.fmt_bold.setFontWeight(QFont.Weight.Bold)
        self.fmt_bold.setForeground(primary_col)

        # 3. Italic (*italic* or _italic_)
        self.fmt_italic = QTextCharFormat()
        self.fmt_italic.setFontItalic(True)
        self.fmt_italic.setForeground(primary_col)

        # 4. Strikethrough (~~strike~~)
        self.fmt_strike = QTextCharFormat()
        self.fmt_strike.setFontStrikeOut(True)
        self.fmt_strike.setForeground(muted_col)

        # 5. Inline Code (`code`)
        self.fmt_inline_code = QTextCharFormat()
        self.fmt_inline_code.setFontFamilies([code_font_family])
        self.fmt_inline_code.setFontWeight(QFont.Weight.DemiBold)
        if self.current_theme == "dark":
            self.fmt_inline_code.setBackground(QColor(255, 255, 255, 30))
            self.fmt_inline_code.setForeground(accent_col)
        elif self.current_theme == "sepia":
            self.fmt_inline_code.setBackground(QColor(0, 0, 0, 20))
            self.fmt_inline_code.setForeground(QColor("#8C5A2B"))
        else:
            self.fmt_inline_code.setBackground(QColor(0, 0, 0, 16))
            self.fmt_inline_code.setForeground(QColor("#1D4ED8"))

        # 6. Fenced Code Block line
        self.fmt_code_block = QTextCharFormat()
        self.fmt_code_block.setFontFamilies([code_font_family])
        if self.current_theme == "dark":
            self.fmt_code_block.setBackground(QColor(255, 255, 255, 18))
            self.fmt_code_block.setForeground(secondary_col)
        else:
            self.fmt_code_block.setBackground(QColor(0, 0, 0, 12))
            self.fmt_code_block.setForeground(QColor("#1E293B"))

        # 7. Checkboxes: Unchecked (- [ ]) and Checked (- [x])
        self.fmt_task_unchecked = QTextCharFormat()
        self.fmt_task_unchecked.setFontWeight(QFont.Weight.Bold)
        self.fmt_task_unchecked.setForeground(muted_col)

        self.fmt_task_checked = QTextCharFormat()
        self.fmt_task_checked.setFontWeight(QFont.Weight.Bold)
        self.fmt_task_checked.setForeground(accent_col)

        # 8. Markdown Links [Text](URL) & Media ![Alt](URL)
        # We highlight the title and significantly DIM the noisy filesystem URL!
        self.fmt_link_title = QTextCharFormat()
        self.fmt_link_title.setFontWeight(QFont.Weight.DemiBold)
        self.fmt_link_title.setForeground(accent_col)
        self.fmt_link_title.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

        self.fmt_link_url = QTextCharFormat()
        self.fmt_link_url.setFontPointSize(10.5)
        self.fmt_link_url.setForeground(muted_col)

        # 9. Blockquotes (> quote)
        self.fmt_quote = QTextCharFormat()
        self.fmt_quote.setFontItalic(True)
        self.fmt_quote.setForeground(secondary_col)

        # 10. Horizontal Rules (--- or ***)
        self.fmt_hr = QTextCharFormat()
        self.fmt_hr.setFontWeight(QFont.Weight.Bold)
        self.fmt_hr.setForeground(muted_col)

        # Build regular expressions list
        self.rules = [
            # Headings
            (QRegularExpression(r"^#\s[^\n]*"), self.fmt_h1, 0),
            (QRegularExpression(r"^##\s[^\n]*"), self.fmt_h2, 0),
            (QRegularExpression(r"^###\s[^\n]*"), self.fmt_h3, 0),

            # Tasks
            (QRegularExpression(r"^\s*[-*+]\s+\[ \]\s"), self.fmt_task_unchecked, 0),
            (QRegularExpression(r"^\s*[-*+]\s+\[[xX]\]\s"), self.fmt_task_checked, 0),

            # Bold
            (QRegularExpression(r"\*\*[^*]+?\*\*"), self.fmt_bold, 0),
            (QRegularExpression(r"__[^_]+?__"), self.fmt_bold, 0),

            # Italic (single asterisks/underscores not preceded/followed by same)
            (QRegularExpression(r"(?<!\*)\*[^*\n]+?\*(?!\*)"), self.fmt_italic, 0),
            (QRegularExpression(r"(?<!_)_[^_\n]+?_(?!_)"), self.fmt_italic, 0),

            # Strikethrough
            (QRegularExpression(r"~~[^~]+?~~"), self.fmt_strike, 0),

            # Inline code
            (QRegularExpression(r"`[^`\n]+?`"), self.fmt_inline_code, 0),

            # Blockquotes
            (QRegularExpression(r"^>[^\n]*"), self.fmt_quote, 0),

            # Horizontal Rules
            (QRegularExpression(r"^(?:---|\*\*\*|___)\s*$"), self.fmt_hr, 0),
        ]

    def highlightBlock(self, text: str):
        """Highlights a single line / block of text."""
        # 1. Multi-line code block handling (```)
        in_code_block = False
        if self.previousBlockState() == 1:
            in_code_block = True

        code_fence = QRegularExpression(r"^\s*```")
        fence_match = code_fence.match(text)

        if fence_match.hasMatch():
            self.setFormat(0, len(text), self.fmt_code_block)
            self.setCurrentBlockState(0 if in_code_block else 1)
            return
        elif in_code_block:
            self.setFormat(0, len(text), self.fmt_code_block)
            self.setCurrentBlockState(1)
            return
        else:
            self.setCurrentBlockState(0)

        # 2. Standard single-line rules
        for regex, fmt, group in self.rules:
            match_iter = regex.globalMatch(text)
            while match_iter.hasNext():
                match = match_iter.next()
                start = match.capturedStart(group)
                length = match.capturedLength(group)
                if start >= 0 and length > 0:
                    self.setFormat(start, length, fmt)

        # 3. Smart Link & Media formatting:
        # [Label](URL) -> Label is colored & underlined, URL is dimmed
        link_regex = QRegularExpression(r"(!?\[)([^\]]+)(\]\()([^\)]+)(\))")
        match_iter = link_regex.globalMatch(text)
        while match_iter.hasNext():
            match = match_iter.next()
            label_start = match.capturedStart(2)
            label_len = match.capturedLength(2)
            url_start = match.capturedStart(4)
            url_len = match.capturedLength(4)

            # Highlight label
            if label_start >= 0 and label_len > 0:
                self.setFormat(label_start, label_len, self.fmt_link_title)
            # Dim the noisy URL
            if url_start >= 0 and url_len > 0:
                self.setFormat(url_start, url_len, self.fmt_link_url)
