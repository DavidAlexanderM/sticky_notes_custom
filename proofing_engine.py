"""
proofing_engine.py - High-Performance Live Proofing & Spell Checking Engine.
Provides spell checking, suggestion candidates, session ignoring, and personal
dictionary persistence using pyspellchecker and SQLite.
"""

import re
import threading
from typing import List, Set, Tuple, Optional
from PySide6.QtCore import QObject, Signal

try:
    from spellchecker import SpellChecker
    HAS_SPELLCHECKER = True
except ImportError:
    HAS_SPELLCHECKER = False

try:
    from . import database
except ImportError:
    import database


class ProofingEngine(QObject):
    """
    Manages spell checking, dictionary language switching, custom user words,
    and text tokenization for the note editor.
    """
    dictionary_updated = Signal()  # Emitted when a word is added or removed
    language_changed = Signal(str)  # Emitted when the proofing language changes

    # Regex patterns for filtering non-prose tokens in markdown
    _RE_URL = re.compile(r'https?://\S+|file://\S+|www\.\S+|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    _RE_CODE_INLINE = re.compile(r'`[^`]+`')
    _RE_MD_LINK = re.compile(r'!?\[[^\]]*\]\([^)]+\)')
    # Word pattern: Unicode letters, allows internal apostrophes/hyphens (e.g. don't, mother-in-law)
    _RE_WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")

    _instance: Optional['ProofingEngine'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'ProofingEngine':
        with cls._lock:
            if cls._instance is None:
                cls._instance = ProofingEngine()
            return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = True
        self._current_lang = "en"
        self._spellcheckers: dict = {}
        self._user_words: Set[str] = set()
        self._session_ignored: Set[str] = set()
        self._load_user_dictionary()

    @property
    def is_available(self) -> bool:
        """Returns True if the underlying spellchecker library is installed."""
        return HAS_SPELLCHECKER

    @property
    def is_enabled(self) -> bool:
        return self._enabled and HAS_SPELLCHECKER

    def set_enabled(self, enabled: bool):
        if self._enabled != enabled:
            self._enabled = enabled
            self.dictionary_updated.emit()

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang_code: str):
        """Switches active proofing language (e.g. 'en', 'es')."""
        clean_code = "es" if lang_code.lower().startswith("es") else "en"
        if clean_code != self._current_lang:
            self._current_lang = clean_code
            self._ensure_spellchecker_loaded(clean_code)
            self.language_changed.emit(clean_code)
            self.dictionary_updated.emit()

    def _ensure_spellchecker_loaded(self, lang: str) -> Optional[object]:
        """Lazy loads SpellChecker instance for the requested language."""
        if not HAS_SPELLCHECKER:
            return None
        if lang not in self._spellcheckers:
            try:
                sc = SpellChecker(language=lang)
                if self._user_words:
                    sc.word_frequency.load_words(list(self._user_words))
                self._spellcheckers[lang] = sc
            except Exception:
                return None
        return self._spellcheckers.get(lang)

    def _load_user_dictionary(self):
        """Loads personal dictionary words from the SQLite database."""
        try:
            words = database.get_dictionary_words()
            self._user_words = {w.lower() for w in words}
        except Exception:
            self._user_words = set()

    def add_to_personal_dictionary(self, word: str):
        """Adds a word to the user dictionary in SQLite and in-memory engine."""
        clean = word.strip().lower()
        if not clean:
            return
        self._user_words.add(clean)
        try:
            database.add_dictionary_word(clean, self._current_lang)
        except Exception:
            pass

        # Update loaded spellcheckers
        for sc in self._spellcheckers.values():
            try:
                sc.word_frequency.load_words([clean])
            except Exception:
                pass

        self.dictionary_updated.emit()

    def ignore_word(self, word: str):
        """Temporarily ignores a word for the current application session."""
        clean = word.strip().lower()
        if clean:
            self._session_ignored.add(clean)
            self.dictionary_updated.emit()

    def is_word_ignored(self, word: str) -> bool:
        clean = word.strip().lower()
        return clean in self._session_ignored or clean in self._user_words

    def is_misspelled(self, word: str) -> bool:
        """
        Checks if a single word is misspelled in the current language.
        Returns False if proofing is disabled, word is too short, numeric,
        or present in dictionary / user words / ignored list.
        """
        if not self.is_enabled:
            return False

        clean = word.strip().strip("'\"`.,!?:;()[]{}*~_#")
        if len(clean) <= 1:
            return False
        # If contains numbers or special symbols, skip
        if any(char.isdigit() for char in clean):
            return False

        lower = clean.lower()
        if lower in self._user_words or lower in self._session_ignored:
            return False

        sc = self._ensure_spellchecker_loaded(self._current_lang)
        if not sc:
            return False

        # If word itself or lower-case word is known, not misspelled
        if clean in sc or lower in sc:
            return False

        return True

    def get_suggestions(self, word: str, max_candidates: int = 5) -> List[str]:
        """
        Retrieves top spelling correction suggestions for a misspelled word.
        Preserves original capitalization (e.g. Titlecase).
        """
        if not self.is_enabled:
            return []

        clean = word.strip().strip("'\"`.,!?:;()[]{}*~_#")
        if not clean:
            return []

        sc = self._ensure_spellchecker_loaded(self._current_lang)
        if not sc:
            return []

        is_title = clean.istitle()
        is_upper = clean.isupper()

        try:
            candidates = sc.candidates(clean) or []
        except Exception:
            candidates = []

        # Sort candidates by frequency / distance if possible
        results: List[str] = []
        for cand in candidates:
            if cand.lower() == clean.lower():
                continue
            if is_upper:
                formatted = cand.upper()
            elif is_title:
                formatted = cand.capitalize()
            else:
                formatted = cand

            if formatted not in results:
                results.append(formatted)
            if len(results) >= max_candidates:
                break

        return results

    def tokenize_line(self, line: str) -> List[Tuple[str, int, int]]:
        """
        Extracts spell-checkable word tokens from a single line of text.
        Returns list of (word, start_index, length).
        Automatically skips:
        - Inline code `...`
        - Markdown links/images [text](url)
        - Raw URLs (http://..., file://...)
        - HTML tags (<...>)
        - Markdown task checkboxes (- [ ])
        """
        if not self.is_enabled or not line:
            return []

        # Mask regions to ignore with spaces of identical length
        mask = list(line)

        def _blank_out(match):
            for i in range(match.start(), match.end()):
                mask[i] = ' '

        # Mask URLs and emails
        for m in self._RE_URL.finditer(line):
            _blank_out(m)

        # Mask inline code
        for m in self._RE_CODE_INLINE.finditer(line):
            _blank_out(m)

        # Mask markdown links/images
        for m in self._RE_MD_LINK.finditer(line):
            _blank_out(m)

        # Mask HTML tags
        for m in re.finditer(r'<[^>]+>', line):
            _blank_out(m)

        # Mask markdown task checkboxes: - [ ] or - [x]
        for m in re.finditer(r'^\s*-\s*\[[ xX]\]', line):
            _blank_out(m)

        masked_text = "".join(mask)

        # Find word tokens in remaining unmasked text
        tokens: List[Tuple[str, int, int]] = []
        for m in self._RE_WORD.finditer(masked_text):
            word = m.group(0)
            # Skip pure numbers or single-letter tokens
            if len(word) > 1 and not any(ch.isdigit() for ch in word):
                tokens.append((word, m.start(), len(word)))

        return tokens


def get_proofing_engine() -> ProofingEngine:
    """Returns the shared ProofingEngine instance."""
    return ProofingEngine.get_instance()
