# AGENTS.md - AI Agent & Subagent Operational Guide

This document is the high-density operational specification for AI agents (Antigravity, subagents, and automated tools) working in this repository. Read this file first to understand the architecture, commands, security rules, and token-saving practices.

---

## 1. Quick Architecture Index

| File / Directory | Purpose | Key Classes / Functions |
| :--- | :--- | :--- |
| `main.py` | Single-window entry point & router | `MainWindow(QMainWindow)` |
| `version.py` | Single source of truth for versioning | `__version__ = "1.3.0"`, `APP_TITLE` |
| `security.py` | Path traversal, URL, filetype & HTML sanitization | `is_safe_attachment()`, `is_safe_url()`, `sanitize_markdown_html()` |
| `database.py` | SQLite persistence layer | `init_db()`, `create_note()`, `get_all_notes()`, `duplicate_note()`, `delete_multiple_notes()` |
| `styles.py` | WinUI 3 Fluent QSS & Markdown CSS | `APP_STYLESHEET`, `MARKDOWN_PREVIEW_CSS`, `NOTE_COLORS` |
| `media_manager.py` | Attachments & audio capture layer | `get_attachments_dir()`, `copy_to_attachments()`, `VoiceRecorder`, `has_microphone()` |
| `components/` | Reusable UI components | `NoteCard`, `ColorPickerFlyout`, `FormatToolbar`, `VoiceRecorderDialog` |
| `views/` | Primary stacked views | `StickyNotesGridView` (Grid), `NoteEditorView` (Editor) |
| `tests/` | Automated test suites | `test_compatibility_and_media.py`, `test_security.py` |
| `scripts/` | Agentic, security & lifecycle tooling | `verify_lifecycle.py`, `security_check.py`, `db_cli.py` |
| `build_exe.py` | Standalone PyInstaller builder | `build()` -> `dist/StickyNotes_v1.3.0_Windows.zip` |

---

## 2. Essential Commands (Standardized)

Always use these standardized commands rather than inventing ad-hoc commands:

* **Launch Desktop App:**
  ```powershell
  python main.py
  ```
* **Full 4-Stage Lifecycle Verification Gate (Docs, Version, Tests & Security):**
  ```powershell
  python scripts/verify_lifecycle.py
  ```
* **Run Standalone AST Security Scanner:**
  ```powershell
  python scripts/security_check.py
  ```
* **Inspect Database in Compact JSON (Token-Efficient):**
  ```powershell
  python scripts/db_cli.py list --limit 5
  python scripts/db_cli.py stats
  python scripts/db_cli.py get <note-id>
  ```
* **Compile Standalone Executable & Gift ZIP:**
  ```powershell
  python build_exe.py
  ```

---

## 3. Token-Efficiency & Agent Performance Rules

To conserve the model context window and minimize token consumption:
1. **NEVER read binary or database files directly:**
   - Do NOT run `view_file` on `notes.db` or files in `attachments/`.
   - Use `python scripts/db_cli.py` to inspect database state in compact JSON format.
2. **Use the Lifecycle Gate Instead of Multiple Shell Calls:**
   - Run `python scripts/verify_lifecycle.py` to simultaneously test functional integrity, security, i18n, and documentation in a single command.
3. **Targeted File Reading:**
   - Specify `StartLine` and `EndLine` when viewing code files over 50 lines.
4. **Adhere to Progressive Disclosure:**
   - Detailed workflow runbooks are stored in `.agents/skills/sticky-notes-ops/SKILL.md` and should only be consulted when executing operational tasks.

---

## 4. Hard Engineering & Security Constraints

* **Strict SQL Parameterization:** Never construct dynamic SQL with f-strings, `%`, or `.format()` inside `sqlite3` execution calls. Always use static SQL and `?` placeholders.
* **Attachment Path Containment:** All attachment file operations must verify `Path.resolve().is_relative_to(get_attachments_dir().resolve())` and validate against `is_safe_attachment()`.
* **Prohibited File Types:** Never allow `.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.sh`, `.scr`, `.msi`, `.dll` or disguised double extensions into `attachments/`.
* **Safe URL Protocols:** External links must validate with `is_safe_url()` to allow only `http://`, `https://`, `mailto:` or local attachment references. Block `javascript:`, `file://` outside attachments, and shell launchers.
* **HTML Sanitization:** Rendered Markdown HTML must pass through `sanitize_markdown_html()` to neutralize active scripts, iframes, and inline event handlers before rendering.
* **Documentation-as-Code (DaC):** Every PR/commit modifying features or APIs **must** update `docs/ARCHITECTURE.md` and log an entry in `CHANGELOG.md`.
* **Universal UTF-8:** Never hardcode ASCII-only assumptions. Support accents, CJK, and RTL scripts natively.
* **Single Version Source:** Update version numbers strictly in `version.py`.
