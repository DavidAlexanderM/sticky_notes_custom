"""
i18n.py - Lightweight Centralized Internationalization (i18n) Engine for Sticky Notes.
Provides instant runtime switching between English ('en') and Spanish ('es')
with full preference persistence and reactive UI notification signals.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

try:
    from .theme_manager import get_preferences_path
except ImportError:
    try:
        from theme_manager import get_preferences_path
    except ImportError:
        def get_preferences_path() -> Path:
            import os, sys
            if getattr(sys, 'frozen', False):
                app_data = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "StickyNotes"
            else:
                app_data = Path(__file__).parent
            return app_data / "preferences.json"


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App & Header
        "app_title": "Danielle's Sticky Notes",
        "new_note": "New Note",
        "search_placeholder": "Search notes by title, tag, or content... (Ctrl+F)",
        "all_notes": "All Notes",
        "free_notes": "Free Notes",
        "back_to_board": "← Back to Board",
        "help_tooltip": "Help & Keyboard Shortcuts (F1)",
        "theme_toggle_tooltip": "Toggle Theme (Light / Dark / Sepia)",
        "language_toggle_tooltip": "Switch Language (English / Español)",
        "toggle_tags_tooltip": "Toggle Tags Sidebar",
        
        # Tags Panel
        "tags_header": "Tags",
        "custom_tags_section": "Custom Tags",
        "predetermined_tags_section": "System Tags",
        "all_tags_filter": "All Notes",
        "untagged_filter": "Untagged",
        "add_custom_tag": "+ New Tag",
        "create_tag_title": "Create Custom Tag",
        "create_tag_prompt": "Enter tag name:",
        "delete_tag": "Delete Tag",
        "confirm_delete_tag": "Delete tag '{name}'? Notes will remain intact.",
        "tag_already_exists": "A tag with this name already exists.",
        "manage_tags": "Manage Tags...",
        "select_tags": "Select Tags",
        
        # Predetermined Tag Names
        "tag_urgent": "Urgent",
        "tag_todo": "To-Do",
        "tag_work": "Work",
        "tag_personal": "Personal",
        "tag_ideas": "Ideas",
        "urgent": "Urgent",
        "todo": "To-Do",
        "work": "Work",
        "personal": "Personal",
        "ideas": "Ideas",

        # Sort Dropdown
        "sort_label": "Sort:",
        "sort_created_desc": "📅 Created (Newest)",
        "sort_created_asc": "📅 Created (Oldest)",
        "sort_updated_desc": "⏱️ Recently Edited",
        "sort_updated_asc": "⏱️ Oldest Edited",
        "sort_title_asc": "🔤 Title (A-Z)",

        # Common Actions
        "save": "Save",
        "cancel": "Cancel",
        "delete": "Delete",
        "rename": "Rename",
        "close": "Close",
        "copy": "Copy",
        "copied": "✓ Copied!",
        "open": "Open",
        "untitled_note": "Untitled Note",
        "empty_note_prompt": "Click here or press Enter to begin writing markdown...",
    },
    "es": {
        # App & Header
        "app_title": "Notas de Danielle",
        "new_note": "Nueva Nota",
        "search_placeholder": "Buscar notas por título, etiqueta o contenido... (Ctrl+F)",
        "all_notes": "Todas las Notas",
        "free_notes": "Notas Sueltas",
        "back_to_board": "← Volver al Tablero",
        "help_tooltip": "Ayuda y Atajos de Teclado (F1)",
        "theme_toggle_tooltip": "Cambiar Tema (Claro / Oscuro / Sepia)",
        "language_toggle_tooltip": "Cambiar Idioma (English / Español)",
        "toggle_tags_tooltip": "Mostrar / Ocultar Barra de Etiquetas",

        # Tags Panel
        "tags_header": "Etiquetas",
        "custom_tags_section": "Mis Etiquetas",
        "predetermined_tags_section": "Predeterminadas",
        "all_tags_filter": "Todas las Notas",
        "untagged_filter": "Sin Etiqueta",
        "add_custom_tag": "+ Nueva Etiqueta",
        "create_tag_title": "Crear Etiqueta Personalizada",
        "create_tag_prompt": "Nombre de la etiqueta:",
        "delete_tag": "Eliminar Etiqueta",
        "confirm_delete_tag": "¿Eliminar la etiqueta '{name}'? Las notas se conservarán.",
        "tag_already_exists": "Ya existe una etiqueta con este nombre.",
        "manage_tags": "Gestionar Etiquetas...",
        "select_tags": "Seleccionar Etiquetas",

        # Predetermined Tag Names
        "tag_urgent": "Urgente",
        "tag_todo": "Por Hacer",
        "tag_work": "Trabajo",
        "tag_personal": "Personal",
        "tag_ideas": "Ideas",
        "urgent": "Urgente",
        "todo": "Por Hacer",
        "work": "Trabajo",
        "personal": "Personal",
        "ideas": "Ideas",

        # Sort Dropdown
        "sort_label": "Ordenar:",
        "sort_created_desc": "📅 Creación (Más reciente)",
        "sort_created_asc": "📅 Creación (Más antigua)",
        "sort_updated_desc": "⏱️ Edición Reciente",
        "sort_updated_asc": "⏱️ Edición Antigua",
        "sort_title_asc": "🔤 Título (A-Z)",

        # Common Actions
        "save": "Guardar",
        "cancel": "Cancelar",
        "delete": "Eliminar",
        "rename": "Renombrar",
        "close": "Cerrar",
        "copy": "Copiar",
        "copied": "✓ ¡Copiado!",
        "open": "Abrir",
        "untitled_note": "Nota Sin Título",
        "empty_note_prompt": "Haz clic aquí o presiona Enter para comenzar a escribir en markdown...",
    }
}


class TranslationManager(QObject):
    """Singleton managing active UI language with reactive signal dispatching."""
    language_changed = Signal(str)  # Emits new language code ('en' or 'es')

    def __init__(self):
        super().__init__()
        self._current_language = self._load_persisted_language()

    @property
    def current_language(self) -> str:
        return self._current_language

    def _load_persisted_language(self) -> str:
        try:
            pref_path = get_preferences_path()
            if pref_path.exists():
                with open(pref_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("language", "en")
        except Exception:
            pass
        return "en"

    def _save_persisted_language(self, lang: str):
        try:
            pref_path = get_preferences_path()
            data = {}
            if pref_path.exists():
                try:
                    with open(pref_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data["language"] = lang
            pref_path.parent.mkdir(parents=True, exist_ok=True)
            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to persist language: {e}")

    def set_language(self, lang: str):
        if lang not in TRANSLATIONS:
            lang = "en"
        if self._current_language != lang:
            self._current_language = lang
            self._save_persisted_language(lang)
            self.language_changed.emit(lang)

    def toggle_language(self) -> str:
        next_lang = "es" if self._current_language == "en" else "en"
        self.set_language(next_lang)
        return next_lang

    def tr(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """Looks up translated string for current language, with English fallback."""
        lang_dict = TRANSLATIONS.get(self._current_language, TRANSLATIONS["en"])
        default_val = default if default is not None else TRANSLATIONS["en"].get(key, key)
        val = lang_dict.get(key, default_val)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val


_GLOBAL_TRANSLATION_MGR: Optional[TranslationManager] = None

def get_translation_manager() -> TranslationManager:
    global _GLOBAL_TRANSLATION_MGR
    if _GLOBAL_TRANSLATION_MGR is None:
        _GLOBAL_TRANSLATION_MGR = TranslationManager()
    return _GLOBAL_TRANSLATION_MGR

def tr(key: str, default: Optional[str] = None, **kwargs) -> str:
    """Convenience global accessor for translated strings."""
    return get_translation_manager().tr(key, default, **kwargs)
