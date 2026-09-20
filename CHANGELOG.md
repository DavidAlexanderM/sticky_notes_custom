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
