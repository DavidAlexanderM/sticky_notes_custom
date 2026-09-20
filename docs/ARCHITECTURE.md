# Sticky Notes - System Architecture & Technical Documentation

This document provides a detailed overview of the system architecture, component hierarchies, data flows, API functions, internationalization (i18n) handling, and the cross-platform mobile strategy (Android & iOS).

---

## 1. System Architecture

The application is built on a decoupled, modular architecture powered by **PySide6 (Qt 6 for Python)** and an embedded local **SQLite** storage engine.

```mermaid
graph TD
    subgraph UI Layer [UI Layer (PySide6 / Qt6)]
        MW[MainWindow (Single Window Host)]
        SW[QStackedWidget (View Router)]
        
        GV[StickyNotesGridView]
        NC[NoteCard Components]
        CPF[ColorPickerFlyout]
        
        EV[NoteEditorView]
        FT[FormatToolbar]
        VRD[VoiceRecorderDialog]
        MD_P[Markdown Preview (QTextBrowser)]
        MD_E[Markdown Editor (QTextEdit)]
    end

    subgraph Service & Media Layer [Service & Media Layer]
        MM[MediaManager (copy_to_attachments)]
        VR[VoiceRecorder (QMediaRecorder & QAudioInput)]
        MD_ENG[markdown2 Engine (HTML Generator)]
    end

    subgraph Storage Layer [Persistence Layer]
        DB[(SQLite: notes.db)]
        FS[(Local File System: attachments/)]
    end

    MW --> SW
    SW -->|Index 0| GV
    SW -->|Index 1| EV
    
    GV --> NC
    NC --> CPF
    
    EV --> FT
    EV --> VRD
    EV --> MD_P
    EV --> MD_E
    
    FT -->|Add Media| MM
    VRD -->|Record Audio| VR
    VR -->|Save Audio| FS
    MM -->|Store Files| FS
    
    EV -->|Render Markdown| MD_ENG
    MD_ENG --> MD_P
    
    GV -->|CRUD Queries| DB
    EV -->|Auto-save / Fetch| DB
```

---

## 2. Component Hierarchy & Navigation Flow

The application strictly implements a **single-window design pattern** (`MainWindow`) to avoid distracting popups and multiple taskbar icons:

1. **`MainWindow` (`QMainWindow`)**:
   - Contains a root `QStackedWidget` managing two primary views:
     - **Index 0:** `StickyNotesGridView` (Board overview)
     - **Index 1:** `NoteEditorView` (Document workspace)
2. **`StickyNotesGridView` (`QWidget`)**:
   - Manages note cards in a responsive `QGridLayout`.
   - Supports single-click card interaction, double-click to open, and multi-select mass erase mode.
   - Hosts `ColorPickerFlyout` triggered by right-click events.
3. **`NoteEditorView` (`QWidget`)**:
   - Split-screen or full-screen editor with three modes: `Edit`, `Split`, and `Preview`.
   - Incorporates `FormatToolbar` for text manipulation and media insertion.
   - Contains automatic debounced saving (600ms inactivity timer) and instant save upon clicking the return arrow (`←`).

---

## 3. Data Schema & Persistence Model

### SQLite Schema (`notes.db`)

```sql
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,          -- UUID v4 string
    title TEXT NOT NULL,          -- Note title (UTF-8)
    content TEXT NOT NULL,        -- Raw Markdown body (UTF-8)
    color_hex TEXT NOT NULL,      -- Hex color code (e.g. #FFF9C4)
    created_at TEXT NOT NULL,     -- ISO-8601 UTC timestamp
    updated_at TEXT NOT NULL      -- ISO-8601 UTC timestamp
);

CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at DESC);
```

### Storage Location Strategy
* **Development Mode:** Stored in the local project directory (`./notes.db` and `./attachments/`).
* **Standalone Frozen Executable:** Automatically redirects storage to the user's standard application data directory (`%LOCALAPPDATA%\StickyNotes\` on Windows, `~/Library/Application Support/StickyNotes/` on macOS, `~/.local/share/StickyNotes/` on Linux) to guarantee write permissions and prevent data loss during app updates.

---

## 4. Module & Function Reference

### `database.py`
| Function | Parameters | Returns | Description |
| :--- | :--- | :--- | :--- |
| `init_db()` | None | `None` | Initializes table schema and seeds welcome notes if fresh. |
| `get_all_notes()` | None | `List[dict]` | Fetches all notes ordered by `updated_at DESC`. |
| `get_note(note_id)` | `note_id: str` | `Optional[dict]` | Fetches single note record by ID. |
| `create_note(title, content, color_hex)` | `title, content, color_hex` | `str` (UUID) | Inserts new note record and returns its UUID. |
| `update_note(note_id, title, content, color_hex)` | Optional fields | `None` | Dynamically updates provided fields and refreshes `updated_at`. |
| `duplicate_note(note_id)` | `note_id: str` | `Optional[str]` | Copies title with `(Copy)` suffix, replicates content/color, and saves new record. |
| `delete_note(note_id)` | `note_id: str` | `None` | Deletes note by primary key. |
| `delete_multiple_notes(note_ids)` | `List[str]` | `None` | Deletes batch of notes in a single SQL transaction. |

### `media_manager.py`
| Class / Function | Description |
| :--- | :--- |
| `get_attachments_dir() -> Path` | Resolves and creates the persistent media attachment directory. |
| `copy_to_attachments(source_path) -> Path` | Sanitizes file stem, appends unique hash, copies file, and returns destination path. |
| `VoiceRecorder (QObject)` | Manages microphone input session via `QMediaCaptureSession`, records AAC/MP4 audio via `QMediaRecorder`, tracks duration, and emits `duration_changed` and `recording_finished`. |

### `components/format_toolbar.py`
* **`FormatToolbar`**:
  * `wrap_selection(prefix, suffix)`: Wraps highlighted editor text or positions cursor between enclosing tokens.
  * Formatting methods: `apply_bold()`, `apply_italic()`, `apply_underline()`, `apply_strikethrough()`, `apply_code()`, `apply_heading()`, `apply_bullet_list()`, `apply_task_list()`.
  * Signals: `add_picture_requested`, `add_audio_requested`, `add_video_requested`.

### `components/voice_recorder_dialog.py`
* **`VoiceRecorderDialog`**:
  * Modal GUI managing live voice recording state machine (Idle -> Recording -> Saved).
  * Exposes `result_audio_path` upon dialog acceptance.

---

## 5. Multi-Language & Internationalization (i18n)

### Why & How Different Languages Work
1. **Unicode Support (UTF-8 everywhere):**
   * SQLite tables are UTF-8 encoded by default in Python 3.
   * `QString` in PySide6 natively handles UTF-16/UTF-8. Accents (Spanish `á, é, í, ó, ú, ñ`), Umlauts (German `ä, ö, ü`), and CJK (Chinese, Japanese, Korean) characters require no special transliteration.
2. **Input Method Editors (IME):**
   * Asian scripts (Japanese Kanji/Kana, Chinese Pinyin/Bopomofo, Korean Hangul) rely on OS-level IME composition windows.
   * `QTextEdit` and `QLineEdit` natively support Windows IME composition events out-of-the-box (`QInputMethodEvent`).
3. **Right-to-Left (RTL) Scripts (Arabic, Hebrew, Persian):**
   * Qt implements the Unicode Bidirectional Algorithm (BiDi).
   * In `QTextEdit`, text direction is automatically detected per paragraph.
   * For whole-app RTL flipping, Qt supports `QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft)`.
4. **UI String Localization:**
   * To translate UI strings (e.g., "+ New Note" -> "+ Nueva Nota"), Qt provides `QCoreApplication.translate()` and `.qm` binary translation catalogs loaded via `QTranslator`.

---

## 6. Mobile Strategy: Android & iOS Portability

While desktop platforms (Windows, macOS, Linux) share 95% of PySide6 code directly, mobile platforms require a tailored approach.

### Architecture Options for Mobile:

```
┌────────────────────────────────────────────────────────┐
│             Desktop (Win/Mac/Linux)                    │
│            PySide6 (Qt6) + SQLite                      │
└────────────────────────────────────────────────────────┘
                           ▲
                           │ Shared Database Schema & API
                           ▼
┌────────────────────────────────────────────────────────┐
│             Mobile Target (Android / iOS)              │
│                                                        │
│  Option A (Recommended): Flutter or React Native       │
│  - Native 120Hz touch animations                       │
│  - Seamless mobile camera & microphone access          │
│  - Shares SQLite schema & Markdown parser              │
│                                                        │
│  Option B: Web PWA (Progressive Web App)               │
│  - Write once in modern web tech                       │
│  - Runs in Chrome on Android / Safari on iOS           │
└────────────────────────────────────────────────────────┘
```

### Recommended Mobile Roadmap:
1. **Phase 1 (Sync Protocol):** Implement a lightweight synchronization protocol (e.g., Supabase, CouchDB/PouchDB, or custom REST/WebDAV) so desktop and mobile sync notes seamlessly.
2. **Phase 2 (Mobile Frontend):** Build an Android/iOS client using **Flutter** or **React Native**:
   * Same visual sticky-note card board.
   * Direct camera capture and native mobile voice memo recording.
   * Cloud sync to match the desktop database.

---

## 7. Application Security & DevSecOps Architecture

To safeguard client machines against local file exploits, malicious Markdown snippets, and arbitrary code execution, the application enforces defense-in-depth security policies:

```mermaid
flowchart TD
    UserInput[Untrusted User Input / Files / Links] --> SecGate{Security Gate (security.py)}
    
    SecGate -->|Path Check| PCheck[Path Traversal Defense: is_relative_to]
    SecGate -->|Extension Check| ECheck[Block dangerous types: .exe, .bat, .cmd, .ps1, .vbs]
    SecGate -->|URL Check| UCheck[Protocol Whitelist: http, https, mailto]
    SecGate -->|HTML Sanitizer| HCheck[Strip script, iframe, embed, and inline on* handlers]
    
    PCheck -->|Safe| FS[(attachments/)]
    ECheck -->|Unsafe| Block1[Reject with User Warning Dialog]
    UCheck -->|Safe External| SysBrowser[System Browser via QDesktopServices]
    UCheck -->|Unsafe Scheme| Block2[Block with Security Alert Dialog]
    HCheck -->|Sanitized HTML| QtPreview[QTextBrowser Preview]
```

### Security Defenses Implemented:
1. **Strict Path Containment:** Every media attachment copied via `media_manager.copy_to_attachments()` is checked against `Path.resolve().is_relative_to(get_attachments_dir().resolve())`. Any traversal attempts (`../../`) immediately raise a `PermissionError`.
2. **Dangerous Filetype Blocking:** Attachments matching `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.sh`, `.scr`, `.msi`, `.dll`, or hidden double extensions (e.g. `invoice.pdf.exe`) are rejected before disk writes occur.
3. **URL Protocol Whitelisting:** External links clicked in `NoteEditorView` are evaluated with `is_safe_url()`. Only `http://`, `https://`, `mailto:`, or local attachments within the app's `attachments/` directory are permitted. Dangerous schemes (`javascript:`, `shell:`, `powershell:`, `ms-msdt:`, or arbitrary local binaries) are blocked.
4. **Markdown Preview HTML Sanitization:** Raw or generated HTML is processed through `sanitize_markdown_html()` to strip active `<script>` tags, malicious frames, embeds, and JavaScript event handlers (`onload`, `onerror`, `onclick`).
5. **100% Parameterized SQLite Engine:** All database operations strictly use parameterized queries (`?` placeholders). Dynamic query building with f-strings is prohibited and enforced via pre-commit AST static analysis (`scripts/security_check.py`).

---

## 8. Theme Architecture & Design Tokens System

Starting in **v1.4.0**, the application features a centralized, tokenized theme architecture decoupled from individual Qt widgets.

```mermaid
flowchart LR
    TM[ThemeManager (Singleton)] -->|Stores Choice| Prefs[(preferences.json)]
    TM -->|Signal: theme_changed| MW[MainWindow]
    TM -->|Signal: theme_changed| GV[StickyNotesGridView]
    TM -->|Signal: theme_changed| EV[NoteEditorView]
    
    subgraph Tokens [Design Tokens: styles.py]
        LP[Light Palette]
        DP[Dark Palette]
        SP[Sepia Palette]
    end
    
    TM --> Tokens
    Tokens -->|QSS| AppStyle[app.setStyleSheet]
    Tokens -->|CSS| MDPreview[Markdown Preview CSS]
```

### Key Components:
1. **`theme_manager.py` (ThemeManager):**
   - Singleton managing active theme state (`"light"`, `"dark"`, `"sepia"`).
   - Emits `theme_changed = Signal(str)` to update all Qt widgets without application restart.
   - Persists user preferences to `%LOCALAPPDATA%/StickyNotes/preferences.json`.
2. **`styles.py` (Design Tokens):**
   - Tokenized palettes defining background, surface, text, border, and accent colors for each theme.
   - `generate_app_stylesheet(theme)` compiles standard QSS rules.
   - `get_markdown_preview_css(theme)` generates dark/light HTML styles for `QTextBrowser`.
3. **Interactive Search & Category Filtering:**
   - Real-time `QLineEdit#SearchInput` filtering note cards dynamically by title and content.
   - Filter chips for fast note categorization by color.


