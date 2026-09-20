# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Hashtag note categorization and auto-complete in editor.
- Multi-language UI localization and full Right-to-Left (RTL) layout switching.
- End-to-end encrypted cloud sync and revision history.
- Cross-platform mobile clients for Android and iOS.

---

## [1.5.0] - 2026-09-20

### Added
- **Pure PySide6 SVG Vector Icon Engine (`icons.py`):**
  - Replaced all platform-dependent unicode emojis with crisp, high-DPI vector SVG icons (Lucide / Fluent design).
  - Dynamically adapts icon colors across Light, Dark, and Sepia themes.
  - Applied across Header, Format Toolbar, Note Cards, Search Bar, and In-App Audio Player.
- **Drag & Drop Media Attachments:**
  - Users can now drag and drop images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`), audio files (`.wav`, `.m4a`, `.mp3`, `.ogg`, `.flac`), and video clips (`.mp4`, `.webm`, `.mov`, `.mkv`) directly into the note editor.
  - Automatically copies dropped media to the secure local attachments store and inserts proper markdown links at the drop position.
- **Live In-Editor Markdown Syntax Highlighter (`markdown_highlighter.py`):**
  - Instant visual styling in the raw editor pane for `# Headings`, `**Bold**`, `*Italic*`, `~~Strikethrough~~`, `` `Code` ``, and ````Code Blocks````.
  - Checkboxes (`- [ ]` / `- [x]`) highlighted in real time.
  - Mutes and dims noisy raw filesystem URLs (`file:///...`), highlighting only clean labels to ensure a clutter-free writing space.
- **Note Card Hover Micro-Interactions & Quick Action Menu (⋯):**
  - Smooth card elevation effect on mouse hover.
  - Top-right 1-click Quick Action menu button (⋯) with vector icons for *Open Note*, *Duplicate*, *Change Color*, *Share / Export*, and *Delete*.

---

## [1.4.3] - 2026-09-20

### Fixed
- **QTextBrowser Media Link Garbled Binary Text Bug:**
  - Resolved the critical bug where clicking an attached media link (`voice_note_xxxx.m4a`) in the Markdown preview panel caused raw MP4 binary container bytes (`ftypisom isomiso2mp41 free mdat moov...`) to render into the preview document.
  - Set `setOpenLinks(False)` on the `QTextBrowser` preview component, completely disabling built-in internal document navigation on link activation and ensuring all link clicks are cleanly intercepted and delegated exclusively to the safe security validator and in-app media player.
  - Added in-document anchor jump support (`#section-name`) using `scrollToAnchor`.
- **Markdown Task List Bullet Formatting:**
  - Replaced manual markdown string task preprocessing with native `task_list` parsing and elegant post-processing.
  - Eliminated duplicate list bullet disc markers (`• ☐`) when rendering task items, displaying clean, standalone Unicode ballot boxes (`☐` / `☑`) with customized accent coloring.
- **High-Contrast Theme Legibility & Audio Player Labels:**
  - Added explicit theme color rules (`text_primary` and `text_secondary`) for `QFrame#AudioPlayerFrame QLabel` components to prevent unreadable gray text on dark themes.

---

## [1.4.2] - 2026-09-19

### Fixed
- **Voice Recording & Playback Reliability:**
  - Resolved unplayable/corrupt recordings caused by premature asynchronous destruction of `VoiceRecorder` during dialog acceptance.
  - Implemented async recorder state tracking (`recorderStateChanged`) and safe flush timeouts.
  - Added empty container detection preventing 0-byte/corrupt audio files from being attached when a microphone is muted or blocked by Windows privacy settings.
  - Built-in In-App Audio Player (`QMediaPlayer` + `QAudioOutput`) enabling immediate audio playback and seeking directly within the application.
- **Markdown Rendering & Card Excerpt Overhaul:**
  - Fixed disappearance of markdown task checkboxes by translating `- [ ]` / `- [x]` into native Unicode ballot boxes (`☐` / `☑`) supported by `QTextBrowser`.
  - Prevented filename underscores in media links from mangling into italics (`voice_note_...` turning into `voicenote...`).
  - Polished NoteCard excerpt generation (`_clean_excerpt`) to strip raw list markers and media markdown, eliminating garbled text on launch.
  - Enhanced syntax highlighting (`.codehilite`) and markdown table styles in preview CSS.
  - Fixed format toolbar button widths and icon padding so labels like "Audio" are never clipped.

---

## [1.4.1] - 2026-09-19

### Fixed
- **UI Contrast & Readability Overhaul (WCAG AAA High Contrast):**
  - Eliminated faint, unreadable gray text on bottom multi-selection action bar (`SelectionActionBar`).
  - Added explicit contrast foreground colors (`#0F172A` in light mode, `#F8FAFC` in dark mode) for `select_mode_btn`, `select_all_btn`, `ThemeToggleBtn`, and `EditorHeaderBtn`.
  - Replaced hardcoded inline styles in `FormatToolbarFrame` and `FormatButton` with theme-aware dynamic classes.
  - Upgraded card titles, snippets, and timestamp typography across all card pastel colors to achieve maximum visual contrast and legibility.
  - Polished empty state typography and mode selector tabs with high-contrast active and inactive states.

---

## [1.4.0] - 2026-09-19

### Added
- **Centralized Theme Management System (`theme_manager.py`):**
  - Instant runtime switching between **Light**, **Dark**, and **Sepia** themes.
  - Persistent preference saving to `%LOCALAPPDATA%/StickyNotes/preferences.json`.
  - Dynamic `theme_changed` Qt signal dispatching across open views.
  - Theme-aware Markdown preview CSS with dark background (`#1E1E22`), light text (`#E4E4E7`), and adapted code blocks.
- **One-Click Theme Switcher (☀️ / 🌙):**
  - Integrated into both `StickyNotesGridView` and `NoteEditorView` headers for instant toggling.
- **Real-Time Note Search Bar:**
  - Fast, dynamic `QLineEdit#SearchInput` in Grid View filtering notes by title, markdown content, or snippet as the user types.
- **Color Category Filter Chips:**
  - Interactive filter pills (`All Notes`, `● Yellow`, `● Green`, `● Coral`, `● Lavender`, `● Sky Blue`, `● Peach`) for instant color categorization.
- **Card Visual Enhancements (`components/note_card.py`):**
  - Media indicator badges (📷 Photo, 🎵 Audio, 🎥 Video) displayed directly on note cards.
  - Refined Fluent 12px rounded geometry, soft depth drop shadows, and hover elevation.
- **Modern Empty State Cards (`QFrame#EmptyStateCard`):**
  - Custom visual cards with helpful actions when search yields no matches or notes board is empty.
- **Automated Theme Test Suite (`tests/test_theme_manager.py`):**
  - Unit tests verifying theme switching, persistence roundtrip, stylesheet generation, and signal emission.

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
