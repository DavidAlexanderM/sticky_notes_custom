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
        "all_tags": "All Tags",
        "untagged": "Untagged",
        "custom_tags": "Custom Tags",
        "predetermined_tags": "System Tags",
        "add_tag": "Add Tag",
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
        "confirm_delete_title": "Confirm Delete",
        "confirm_delete_multiple": "Are you sure you want to permanently delete {count} selected note(s)?",
        "record_screen": "Record Desktop Screen...",
        "choose_video": "Choose Existing Video File...",
        "open_attachments": "Open Attachments Folder...",
        "btn_audio": "Audio",
        "btn_screen_capture": "Capture",
        "btn_video": "Video",
        "btn_attach": "Attach",
        "tooltip_record_audio": "Record voice note directly (1-touch)",
        "tooltip_screen_capture": "Capture screen / snip region (1-touch)",
        "tooltip_record_video": "Record screen video directly (1-touch)",
        "tooltip_attach_media": "Attach media files (Images, Audio, Video)",
        "attach_picture": "Attach Picture...",
        "attach_audio": "Attach Audio File...",
        "attach_video": "Attach Video File...",
        "add_to_dictionary": "Add to Personal Dictionary",
        "ignore_word": "Ignore Word",
        "no_spelling_suggestions": "No spelling suggestions",
        "tooltip_spellcheck": "Toggle Live Spell Check (Proofing)",
        "spellcheck_label": "Spell Check",
        "tooltip_strike": "Strikethrough",
        "tooltip_list": "List",
        "tooltip_task": "Task",
        "tooltip_photo": "Photo",
        "tooltip_audio": "Audio",
        "tooltip_video": "Video",
        
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

        # Color Filter Tooltips
        "color_filter_all": "All Notes",
        "color_butter_yellow": "Butter Yellow notes",
        "color_mint_green": "Mint Green notes",
        "color_soft_coral": "Soft Coral notes",
        "color_lavender": "Lavender notes",
        "color_sky_blue": "Sky Blue notes",
        "color_warm_peach": "Warm Peach notes",
        "color_soft_pink": "Soft Pink notes",
        "color_slate_dark": "Slate Dark notes",

        # Project / Stack Switcher
        "all_notes_count": "All Notes ({count})",
        "create_new_stack": "Create New Stack...",
        "manage_stacks": "Manage Stacks...",
        "active_stack_tooltip": "Active Stack: {name}\nClick to switch project stack",
        "back_to_board_tooltip": "Return to main board showing all stacks and free notes",

        # Stacks & Note Cards
        "notes_count": "{count} notes",
        "one_note_count": "1 note",
        "double_click_open_stack": "Double-click to open stack",
        "rename_stack_hint": "Double-click or press F2 to rename",
        "stack_options": "Stack Options",
        "open_stack": "Open Stack",
        "rename_stack": "Rename Stack (F2)",
        "change_stack_color": "Change Stack Color",
        "unstack_all_notes": "Unstack All Notes (Dissolve)",
        "delete_stack_and_notes": "Delete Stack & Notes",
        "confirm_dissolve_stack": "Unstack all notes from '{name}'? Notes will return to Free Notes.",
        "confirm_delete_stack": "Delete stack '{name}' and all its notes? This action cannot be undone.",
        "note_options": "Note Options",
        "open_note": "Open Note",
        "duplicate": "Duplicate",
        "duplicate_note": "Duplicate Note",
        "change_color": "Change Color",
        "move_to_stack": "Move to Stack",
        "current_stack_item": "✓ {name} (Current)",
        "share_export": "Share / Export",
        "delete_note": "Delete Note",
        "confirm_delete_note": "Are you sure you want to delete this note?",
        "empty_note": "Empty note",
        "recently": "Recently",

        # Selection Action Bar
        "select_mode": "Select",
        "select_all": "Select All",
        "clear": "Clear",
        "delete_selected": "Delete Selected",
        "notes_selected": "{count} notes selected",
        "one_note_selected": "1 note selected",
        "clear_filters_btn": "Clear Filter",
        "no_notes_matched": "No notes or stacks matched your filters.",

        # Editor View & Toolbars
        "editor_back_tooltip": "Return to Board (Auto-saves)",
        "editor_title_placeholder": "Note Title...",
        "tooltip_bold": "Bold (Ctrl+B)",
        "tooltip_italic": "Italic (Ctrl+I)",
        "tooltip_underline": "Underline (Ctrl+U)",
        "tooltip_strikethrough": "Strikethrough",
        "tooltip_heading": "Heading (##)",
        "tooltip_bullet_list": "Bullet List",
        "tooltip_checklist": "Task Checklist",
        "tooltip_code": "Code Block",
        "tooltip_image": "Insert Image",
        "tooltip_voice": "Voice Recording",
        "tooltip_video": "Attach Video",
        "tooltip_tags": "Manage Note Tags",
        "tooltip_palette": "Note Color",
        "tooltip_share": "Share / Export",
        "tooltip_delete_note": "Delete Note",
        "mode_edit": "Edit",
        "mode_split": "Split",
        "mode_preview": "Preview",

        # Help & About Dialog
        "help_dialog_title": "Help & Keyboard Shortcuts",
        "tab_shortcuts": "Keyboard Shortcuts",
        "tab_markdown": "Markdown & Media",
        "tab_about": "About",
        "close_btn": "Close",
        "sh_new_note": "Create new note",
        "sh_search": "Focus search bar",
        "sh_select_all": "Select all notes",
        "sh_delete_note": "Delete selected note",
        "sh_bold": "Bold formatting",
        "sh_italic": "Italic formatting",
        "sh_underline": "Underline formatting",
        "sh_return_board": "Save and return to board",
        "sh_rename_stack": "Rename active stack",

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
        "all_tags": "Todas las Etiquetas",
        "untagged": "Sin Etiqueta",
        "custom_tags": "Mis Etiquetas",
        "predetermined_tags": "Etiquetas del Sistema",
        "add_tag": "Añadir Etiqueta",
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
        "confirm_delete_title": "Confirmar Eliminación",
        "confirm_delete_multiple": "¿Estás seguro de que deseas eliminar permanentemente {count} nota(s) seleccionada(s)?",
        "record_screen": "Grabar Pantalla del Escritorio...",
        "choose_video": "Elegir Archivo de Video Existente...",
        "open_attachments": "Abrir Carpeta de Adjuntos...",
        "btn_audio": "Audio",
        "btn_screen_capture": "Captura",
        "btn_video": "Video",
        "btn_attach": "Adjuntar",
        "tooltip_record_audio": "Grabar nota de voz directamente (1 toque)",
        "tooltip_screen_capture": "Capturar pantalla o recortar área (1 toque)",
        "tooltip_record_video": "Grabar video de pantalla directamente (1 toque)",
        "tooltip_attach_media": "Adjuntar archivos multimedia (Imágenes, Audio, Video)",
        "attach_picture": "Adjuntar Imagen...",
        "attach_audio": "Adjuntar Archivo de Audio...",
        "attach_video": "Adjuntar Archivo de Video...",
        "add_to_dictionary": "Añadir al Diccionario Personal",
        "ignore_word": "Omitir Palabra",
        "no_spelling_suggestions": "Sin sugerencias ortográficas",
        "tooltip_spellcheck": "Activar/Desactivar Corrector Ortográfico",
        "spellcheck_label": "Corrector Ortográfico",
        "tooltip_strike": "Tachado",
        "tooltip_list": "Lista",
        "tooltip_task": "Tarea",
        "tooltip_photo": "Foto",
        "tooltip_audio": "Audio",
        "tooltip_video": "Video",

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

        # Color Filter Tooltips
        "color_filter_all": "Todas las Notas",
        "color_butter_yellow": "Notas Amarillo Mantequilla",
        "color_mint_green": "Notas Verde Menta",
        "color_soft_coral": "Notas Coral Suave",
        "color_lavender": "Notas Lavanda",
        "color_sky_blue": "Notas Azul Cielo",
        "color_warm_peach": "Notas Melocotón Cálido",
        "color_soft_pink": "Notas Rosa Suave",
        "color_slate_dark": "Notas Pizarra Oscura",

        # Project / Stack Switcher
        "all_notes_count": "Todas las Notas ({count})",
        "create_new_stack": "Crear Nueva Pila...",
        "manage_stacks": "Administrar Pilas...",
        "active_stack_tooltip": "Pila Activa: {name}\nHaz clic para cambiar de pila",
        "back_to_board_tooltip": "Volver al tablero principal con todas las pilas y notas sueltas",

        # Stacks & Note Cards
        "notes_count": "{count} notas",
        "one_note_count": "1 nota",
        "double_click_open_stack": "Doble clic para abrir pila",
        "rename_stack_hint": "Doble clic o pulsa F2 para renombrar",
        "stack_options": "Opciones de Pila",
        "open_stack": "Abrir Pila",
        "rename_stack": "Renombrar Pila (F2)",
        "change_stack_color": "Cambiar Color de Pila",
        "unstack_all_notes": "Deshacer Pila (Separar Notas)",
        "delete_stack_and_notes": "Eliminar Pila y Notas",
        "confirm_dissolve_stack": "¿Deshacer la pila '{name}'? Las notas volverán a Notas Sueltas.",
        "confirm_delete_stack": "¿Eliminar la pila '{name}' y todas sus notas? Esta acción no se puede deshacer.",
        "note_options": "Opciones de Nota",
        "open_note": "Abrir Nota",
        "duplicate": "Duplicar",
        "duplicate_note": "Duplicar Nota",
        "change_color": "Cambiar Color",
        "move_to_stack": "Mover a Pila",
        "current_stack_item": "✓ {name} (Actual)",
        "share_export": "Compartir / Exportar",
        "delete_note": "Eliminar Nota",
        "confirm_delete_note": "¿Estás seguro de que deseas eliminar esta nota?",
        "empty_note": "Nota vacía",
        "recently": "Recientemente",

        # Selection Action Bar
        "select_mode": "Seleccionar",
        "select_all": "Seleccionar Todo",
        "clear": "Limpiar",
        "delete_selected": "Eliminar Seleccionadas",
        "notes_selected": "{count} notas seleccionadas",
        "one_note_selected": "1 nota seleccionada",
        "clear_filters_btn": "Limpiar Filtros",
        "no_notes_matched": "No se encontraron notas ni pilas con estos filtros.",

        # Editor View & Toolbars
        "editor_back_tooltip": "Volver al Tablero (Guarda automáticamente)",
        "editor_title_placeholder": "Título de la nota...",
        "tooltip_bold": "Negrita (Ctrl+B)",
        "tooltip_italic": "Cursiva (Ctrl+I)",
        "tooltip_underline": "Subrayado (Ctrl+U)",
        "tooltip_strikethrough": "Tachado",
        "tooltip_heading": "Encabezado (##)",
        "tooltip_bullet_list": "Lista con Viñetas",
        "tooltip_checklist": "Lista de Tareas",
        "tooltip_code": "Bloque de Código",
        "tooltip_image": "Insertar Imagen",
        "tooltip_voice": "Grabación de Voz",
        "tooltip_video": "Adjuntar Video",
        "tooltip_tags": "Gestionar Etiquetas de la Nota",
        "tooltip_palette": "Color de Nota",
        "tooltip_share": "Compartir / Exportar",
        "tooltip_delete_note": "Eliminar Nota",
        "mode_edit": "Editar",
        "mode_split": "Dividir",
        "mode_preview": "Vista Previa",

        # Help & About Dialog
        "help_dialog_title": "Ayuda y Atajos de Teclado",
        "tab_shortcuts": "Atajos de Teclado",
        "tab_markdown": "Markdown y Multimedia",
        "tab_about": "Acerca de",
        "close_btn": "Cerrar",
        "sh_new_note": "Crear nueva nota",
        "sh_search": "Ir a la barra de búsqueda",
        "sh_select_all": "Seleccionar todas las notas",
        "sh_delete_note": "Eliminar nota seleccionada",
        "sh_bold": "Formato negrita",
        "sh_italic": "Formato cursiva",
        "sh_underline": "Formato subrayado",
        "sh_return_board": "Guardar y volver al tablero",
        "sh_rename_stack": "Renombrar pila activa",

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


def format_localized_date(iso_str: str) -> str:
    """Formats an ISO timestamp into a localized, human-friendly date string."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso_str)
        lang = get_translation_manager().current_language
        months_es = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        time_part = dt.strftime("%I:%M %p")
        if lang == "es":
            month = months_es[dt.month - 1]
            return f"{dt.day} {month}, {time_part}"
        else:
            return dt.strftime("%b %d, %I:%M %p")
    except Exception:
        return tr("recently", "Recently")
