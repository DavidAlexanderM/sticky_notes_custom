# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Modern UI redesign with floating glassmorphism pill toolbar and media badges.
- Real-time instant search bar and hashtag note categorization.
- Multi-language UI localization and full Right-to-Left (RTL) layout switching.
- End-to-end encrypted cloud sync and revision history.
- Cross-platform mobile clients for Android and iOS.

---

## [1.3.0] - 2026-09-19

### Added
- **Application Security Module (`security.py`):**
  - Path traversal defense verifying all attachment operations stay strictly within the `attachments/` directory.
  - Executable and script attachment blocking (`.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.sh`, `.scr`, `.msi`, `.dll`, double-extensions).
  - External link protocol whitelisting (`http://`, `https://`, `mailto:`) and blocking dangerous system launcher schemes (`javascript:`, `shell:`, `powershell:`, `ms-msdt:`).
  - HTML sanitization stripping active `<script>`, `<iframe>`, `<embed>`, and inline event handlers from Markdown preview.
- **Automated Security Test Suite (`tests/test_security.py`):**
  - 11 comprehensive automated tests verifying path traversal prevention, dangerous extension rejection, safe URL protocols, script stripping, and SQLite parameterization against SQL injection payloads.
- **AST Static Analysis & DevSecOps Gate (`scripts/security_check.py`):**
  - Token-efficient AST code scanner verifying zero dynamic SQL string formatting and zero unsafe code execution calls (`eval`, `exec`, `os.system`).
  - Integrated dependency vulnerability auditing via `pip-audit`.
- **4-Stage Verification Gate (`scripts/verify_lifecycle.py`):**
  - Added Stage 4 running the security test suite and AST security scanner on every pre-release check.
- **Agentic Infrastructure:**
  - `AGENTS.md` root operations manual.
  - Token-saving SQLite CLI helper (`scripts/db_cli.py`).
  - Antigravity workspace operational skill (`.agents/skills/sticky-notes-ops/SKILL.md`).
  - Local Model Context Protocol configuration (`.agents/mcp_config.json`).

### Changed
- Refactored `database.delete_multiple_notes()` to use 100% static parameterized `executemany()` query.
- Fixed variable scope for HTML note export in `NoteEditorView`.

---

## [1.2.0] - 2026-09-19

### Added
- **Rich Text Formatting Toolbar:** Dedicated formatting strip above editor with buttons and keyboard shortcuts:
  - Bold (`Ctrl+B`), Italics (`Ctrl+I`), Underline (`Ctrl+U`), Strikethrough, Headings, Bullet Lists, Task Checklists, and Code blocks.
- **Multimedia Attachments:**
  - Pictures (`.png`, `.jpg`, `.gif`, `.webp`) copied to local `attachments/` with responsive preview styling.
  - Live Microphone Voice Recording with active elapsed duration timer.
  - Existing audio file attachments (`.mp3`, `.wav`, `.m4a`).
  - Video attachments (`.mp4`, `.mkv`, `.webm`, `.mov`).
  - One-click media playback launching attached audio and videos in the default system media player.
- **Hardware Device Detection:**
  - Automatic audio capture device (microphone) detection using `QMediaDevices`.
  - Graceful UI fallback disabling live recording with clear warning badge when no microphone is connected.
- **Testing & Documentation:**
  - Comprehensive compatibility test suite covering media pipelines and 10 international language scripts (Spanish, French, German, Arabic RTL, Hebrew RTL, Chinese, Japanese, Korean, Unicode emojis, and math symbols).
  - System Architecture documentation (`docs/ARCHITECTURE.md`) with Mermaid diagrams and full API reference.
  - Phased Product Roadmap (`docs/ROADMAP.md`).
  - Professional Development Lifecycle and Documentation Governance guide (`docs/DEVELOPMENT_LIFECYCLE.md`).

---

## [1.1.0] - 2026-09-19

### Added
- **Note Management Features:**
  - Multi-select and mass erase mode with visual card checkboxes, "Select All", and confirmation dialog.
  - Note duplication action (`(Copy)`) accessible from both the card right-click flyout and the editor header.
  - Share and Export menu: Copy Markdown to Clipboard, Export as `.md`, and Export as `.html`.
- **Standalone Gift App Packaging:**
  - Automated PyInstaller compilation script (`build_exe.py`) bundling `StickyNotes.exe` into a portable, zero-dependency `.zip` file for gifting.
  - Dynamic database path redirection to `%LOCALAPPDATA%\StickyNotes\` when running as a compiled executable.

---

## [1.0.0] - 2026-09-19

### Added
- Initial release of Sticky Notes desktop application built with Python 3 and PySide6 (Qt 6).
- Single-window minimal Fluent design with seamless view routing via `QStackedWidget`.
- Responsive sticky note grid board with title, markdown snippet, and timestamp cards.
- Right-click floating circular color palette with 8 pastel and dark sticky colors.
- Double-click note editor with standard text input, live split-screen Markdown preview, and return back arrow (`←` / `Esc`) with auto-save.
- Embedded SQLite database (`notes.db`) with automatic table creation and starter note seeding.
