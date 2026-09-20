# Danielle's Sticky Notes - Personal Desktop Edition

A minimal, single-window Windows desktop application built with **Python** and **PySide6 (Qt6)** featuring a **Windows 11 Fluent / WinUI 3** aesthetic, 3D note stacks, interactive tag chips, and bilingual English/Spanish support.

<p align="left">
  <a href="https://github.com/DavidAlexanderM/sticky_notes_custom/releases/latest">
    <img src="https://img.shields.io/github/v/release/DavidAlexanderM/sticky_notes_custom?style=for-the-badge&color=2563EB&logo=github&label=Release" alt="Latest Release" />
  </a>
  <a href="https://github.com/DavidAlexanderM/sticky_notes_custom/releases/latest">
    <img src="https://img.shields.io/github/downloads/DavidAlexanderM/sticky_notes_custom/total?style=for-the-badge&color=10B981&logo=windows&label=Total%20Downloads" alt="Total Downloads" />
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows" alt="Platform Windows" />
</p>

---

## ⚡ Direct Download (Latest Version)

No need to search through release tabs or build from source — download and run immediately on any Windows PC:

| Package | Recommended For | 1-Click Direct Download |
| :--- | :--- | :--- |
| 🚀 **Windows Installer** | Standard installation with desktop shortcut, start menu entry, and uninstaller. | [**⬇️ Download Installer (.exe)**](https://github.com/DavidAlexanderM/sticky_notes_custom/releases/latest) |
| 📦 **Portable Package** | Zero installation needed. Extract anywhere (e.g. USB or Documents) and double-click `StickyNotes.exe`. | [**📦 Download Portable (.zip)**](https://github.com/DavidAlexanderM/sticky_notes_custom/releases/latest) |

> 💡 **Tip:** Full release notes, asset hashes, and previous versions are always available on the [**Official Releases Page**](https://github.com/DavidAlexanderM/sticky_notes_custom/releases/latest).

---

## Features

* **Single-Window Fluent Minimal Design:**
  * Clean, borderless feel with Segoe UI typography and soft drop shadows.
  * Instant, seamless view transitions without popup clutter.
* **Sticky Notes Board & Management:**
  * Displays notes in a responsive adaptive grid.
  * Preview titles, Markdown excerpts, and last-modified timestamps.
  * **Multi-Select & Mass Erase:** Click "Select" to check multiple notes, "Select All", and delete them in bulk with confirmation.
  * **Duplicate Note:** Duplicate any note from the right-click menu or editor header.
  * **Share & Export:** Quick-copy formatted markdown to clipboard, or export to `.md` / `.html` files.
* **Right-Click Color Picker Flyout:**
  * Right-click any note to open a palette with 8 sticky colors (*Butter Yellow, Mint Green, Soft Coral, Lavender, Sky Blue, Warm Peach, Soft Pink, Slate Dark*).
  * Automatically adjusts text contrast for light/dark themes.
* **Double-Click Note Editor & Formatting Toolbar:**
  * Double-click any note to open the editor.
  * **[← Back Arrow]** or `Esc` key returns to the board with auto-save.
  * **Formatting Controls & Shortcuts:**
    * **Bold** (`Ctrl+B`)
    * **Italics** (`Ctrl+I`)
    * **Underline** (`Ctrl+U`)
    * **Strikethrough**, **Heading** (`##`), **Bullet Lists**, **Task Checklists**, and **Code Blocks**.
  * **Multimedia Attachments:**
    * 🖼 **Pictures:** Insert photos/images (`.png`, `.jpg`, `.gif`, `.webp`) with automatic responsive rendering and rounded corners.
    * 🎙 **Voice Recordings & Audio:** Built-in live microphone recording with active timer, or attach existing `.mp3`/`.wav`/`.m4a` audio files.
    * 🎥 **Videos:** Attach `.mp4`, `.mkv`, `.webm`, or `.mov` video files.
    * **One-Click Playback:** Clicking attached audio/video links in preview immediately opens them in your default Windows media player.
  * **Three View Modes:**
    * `Edit`: Distraction-free Markdown editor.
    * `Split`: Live side-by-side editing and formatted Markdown preview.
    * `Preview`: Full rendered rich text view with styled headings, images, code blocks, checklists, and media badges.
* **Zero Configuration Storage & Attachments:**
  * Automatic local SQLite persistence and local `attachments/` folder. Uses `%LOCALAPPDATA%/StickyNotes/` when packaged as an executable. Works completely offline.
* **Gift App Ready (Standalone .exe):**
  * Package into a standalone portable `.zip` or `.exe` via `python build_exe.py` that runs on any Windows PC with zero dependencies.

---

## Installation & Setup

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/DavidAlexanderM/sticky_notes_app.git
   cd sticky_notes_app
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```powershell
   python main.py
   ```
   *Or simply double-click `run.bat`.*

---

## Project Structure

```
sticky_notes_app/
├── main.py                    # Application entry point & single-window host
├── database.py                # SQLite storage engine (CRUD & seeding)
├── styles.py                  # Windows 11 Fluent QSS & markdown themes
├── requirements.txt           # Python dependencies
├── run.bat                    # Windows launcher batch script
├── test_app.py                # Test & verification script
├── components/
│   ├── color_picker_flyout.py # Floating right-click color palette
│   └── note_card.py           # Sticky note card widget
└── views/
    ├── grid_view.py           # Responsive sticky notes grid
    └── editor_view.py         # Markdown editor with live preview & back arrow
```
