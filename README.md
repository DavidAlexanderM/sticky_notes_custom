# Danielle's Sticky Notes - Personal Desktop Edition

A refined, single-window Windows desktop application built with **Python 3.11** and **PySide6 (Qt6)** featuring a **Windows 11 Fluent / WinUI 3** aesthetic, 3D note stacks, interactive tag chips, live proofing, screen & call recording, Windows OS native sharing, and in-app auto-updating.

<p align="left">
  <a href="https://github.com/DavidAlexanderM/sticky_notes_releases/releases/latest">
    <img src="https://img.shields.io/badge/Release-v1.7.1-2563EB?style=for-the-badge&logo=github&label=Release" alt="Latest Release v1.7.1" />
  </a>
  <a href="https://github.com/DavidAlexanderM/sticky_notes_releases/releases/latest">
    <img src="https://img.shields.io/github/downloads/DavidAlexanderM/sticky_notes_releases/total?style=for-the-badge&color=10B981&logo=windows&label=Downloads" alt="Total Downloads" />
  </a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows" alt="Platform Windows" />
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python" alt="Python 3.11" />
</p>

---

## ⚡ Direct Download (v1.7.1 Latest)

No need to search through release tabs or build from source — download and run immediately on any Windows 10/11 PC from the official zero-token public releases mirror:

| Package | Recommended For | 1-Click Direct Download |
| :--- | :--- | :--- |
| 🚀 **Windows Setup Installer** | Standard installation with desktop icon, Start Menu entry, clean uninstaller, and automatic silent updates. | [**⬇️ Download Installer (`StickyNotes_Setup_v1.7.1.exe`)**](https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/v1.7.1/StickyNotes_Setup_v1.7.1.exe) |
| 📦 **Portable Standalone Package** | Zero installation needed. Extract anywhere (e.g., USB stick or Documents) and launch `StickyNotes.exe`. | [**📦 Download Portable (`StickyNotes_v1.7.1_Windows.zip`)**](https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/v1.7.1/StickyNotes_v1.7.1_Windows.zip) |

> 💡 **Public Releases Mirror:** Release notes, SHA-256 asset hashes, and previous releases are always available on the [**Public Releases Mirror**](https://github.com/DavidAlexanderM/sticky_notes_releases/releases).

---

## 🌟 Key Features

### 🔄 Bulletproof In-App Auto-Updater (v1.6.9 & v1.7.1)
* **Zero-Token Feed Resolution:** Seamless multi-tier update feed queries public mirror releases API without requiring GitHub accounts or Personal Access Tokens.
* **Integrity Validation:** Validates `b"MZ"` headers for Windows installers and `b"PK"` for zip archives, preventing corrupted installs.
* **Glitch-Free UI:** Dedicated 7-page `QStackedWidget` update dialog with clean state transitions, download progress tracking, and release notes preview.
* **Automated Self-Restart:** Hardened detached Windows process handles process closure, runs silent installer with `/NORESTART /CLOSEAPPLICATIONS`, relaunches updated executable, and logs diagnostics to `%TEMP%\StickyNotes_Update\update.log`.

### 📤 Windows Native Sharing & Rich Clipboard (v1.7.0)
* **OS-Level Share Integration:** Invokes native Windows 10/11 system Share flyout (`&Share` COM verb) for Nearby Share, Bluetooth, Contacts, Phone Link, and installed Store apps.
* **Native Protocol Handlers:** One-click sharing via desktop app URIs (`whatsapp://`, `tg://`, `msteams:`, `sms:`, `mailto:`).
* **Interactive Drag-and-Drop Chip:** `DraggableNoteChip` lets you drag notes directly into external apps (Word, Slack, browsers) with multi-format MIME support (`text/plain`, `text/html`, `.zip` note packages).
* **Multi-Format Clipboard Export:** Copies rich text with formatted HTML, plain text, and rendered note bitmaps in a single click.

### 🎥 Screen Recording & 2-Way Audio Call Capture (v1.6.1, v1.6.7, v1.6.8)
* **Desktop Screen Capture:** High-performance desktop recording to H.264 MP4 with FFmpeg integration.
* **Multi-Monitor Snipping HUD:** Interactive region selection across multiple monitors with live dimension readout and `Esc`/`Enter` keyboard navigation.
* **WASAPI Audio Loopback (2-Way Capture):** Captures system speaker audio (meeting participants, Zoom/Teams/Discord calls) and microphone audio simultaneously.
* **Pure Python Audio Mixing Fallback:** Mixed-audio generation using `numpy` and WAV channel interleaving when FFmpeg is not installed.

### 🗂️ 3D Note Stacks & Projects System (v1.6.3)
* **Physical Layered Stacks:** Visual 3D paper stack cards representing project groupings.
* **Drag-to-Merge:** Drag any note over another or onto an existing stack to group them together.
* **Project Switcher & Inline Renaming:** Switch workspaces instantly, press `F2` to rename projects inline, and assign custom project accent colors.

### 🏷️ Interactive Tagging System & Collapsible Sidebar (v1.6.4)
* **Tag Chips & Flyout:** Assign tags inline with colored `#tag` chips.
* **Collapsible Side Panel:** Slide-out left panel displays all system and custom tags with dynamic count badges.
* **Custom Tags Priority:** User-created tags are ordered first for rapid selection.

### ✍️ In-Editor Live Proofing Engine (v1.6.5)
* **Real-Time Spell Checking:** Live red wavy squiggles for misspelled words powered by `pyspellchecker`.
* **Right-Click Suggestion Menu:** Instant correction suggestions and "Add to Personal Dictionary".
* **Persistent SQLite Dictionary:** User-saved words stored in `user_dictionary` table across app restarts.
* **Bilingual Proofing:** Real-time spell check supports both English and Spanish language profiles.

### 🌐 Instant Runtime Bilingual Support (v1.6.4)
* **1-Click Language Switch:** Toggle between English (`🌐 EN`) and Spanish (`🌐 ES`) from the top bar with zero app restart.
* **Canonical Tag Translation:** System tags (`#work`, `#personal`, `#urgent`, `#ideas`, `#todo`) auto-translate while preserving database integrity.

### 🎨 WinUI 3 Fluent Themes & System Dark Mode Detection (v1.4.0, v1.6.2)
* **Three Color Schemes:** Light, Dark, and warm Sepia reading themes with tuned contrast ratios.
* **OS-Level Sync:** Listens to Windows `WM_THEMECHANGED` and `colorSchemeChanged` events to automatically match Windows and PowerToys dark mode states.
* **8 Note Colors:** Soft sticky palette (*Butter Yellow, Mint Green, Soft Coral, Lavender, Sky Blue, Warm Peach, Soft Pink, Slate Dark*).

---

## 🛠️ Installation & Setup (Developer Edition)

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/DavidAlexanderM/sticky_notes_custom.git
   cd sticky_notes_custom
   ```

2. **Set up a virtual environment and install dependencies:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```powershell
   python main.py
   ```
   *Or launch using `run.bat`.*

4. **Run the verification test suite & lifecycle gate:**
   ```powershell
   python scripts/verify_lifecycle.py
   ```

---

## 📁 Project Architecture & Structure

```
sticky_notes_app/
├── main.py                          # Application entry point & single-window host
├── version.py                       # Centralized version metadata (Single Source of Truth)
├── database.py                      # SQLite storage engine (Notes, Projects, Tags, Dictionary)
├── updater.py                       # Auto-update feed resolution, downloads & detached self-restart
├── proofing_engine.py               # Real-time spell checker & SQLite user dictionary
├── i18n.py                          # Bilingual runtime dictionary & canonical tag translation
├── media_manager.py                 # Audio/video/screen recording & WASAPI loopback mixer
├── theme_manager.py                 # Theme state, persistence & Windows dark mode listener
├── security.py                      # Input validation, path traversal & HTML sanitization
├── icons.py                         # Themed SVG icon rendering engine
├── styles.py                        # WinUI 3 Fluent CSS/QSS design tokens & palettes
├── build_exe.py                     # PyInstaller standalone executable packager
├── installer.iss                    # Inno Setup Windows installer compiler script
│
├── components/                      # Modular UI Widgets & Dialogs
│   ├── color_picker_flyout.py       # Floating sticky palette selector
│   ├── format_toolbar.py            # Rich Markdown editing & attachment toolbar
│   ├── help_dialog.py               # Keyboard shortcuts & features help guide
│   ├── note_card.py                 # Sticky note grid item card with elevation
│   ├── project_dialog.py            # Project creation & color management dialog
│   ├── screen_recorder_dialog.py    # Desktop snipping overlay & recording controls
│   ├── share_dialog.py              # Windows OS share flyout, drag chip & protocols
│   ├── stack_card.py                # 3D layered paper stack widget for project notes
│   ├── tag_selector_flyout.py       # Inline tag assignment flyout
│   ├── tag_side_panel.py            # Collapsible tag filter sidebar
│   ├── update_dialog.py             # 7-page QStackedWidget update manager dialog
│   └── voice_recorder_dialog.py     # Live audio recording modal with active timer
│
├── views/                           # Primary Window Views
│   ├── grid_view.py                 # Responsive note board, project switcher & search
│   └── editor_view.py               # Three-mode Markdown editor (Edit / Split / Preview)
│
├── scripts/                         # Lifecycle, Build & DevSecOps Utilities
│   ├── verify_lifecycle.py          # Pre-release 4-stage gate (Docs, Sync, 11 Tests, SAST)
│   ├── generate_release_manifest.py # Automated version.json generator for mirror feeds
│   ├── security_check.py            # AST SAST static vulnerability audit
│   └── release.py                   # Automated tagging, release notes & sync orchestrator
│
├── tests/                           # Complete Automated Test Suite (11 test suites)
│   ├── test_app.py                  # Core SQLite CRUD & app integration tests
│   ├── test_compatibility_and_media.py
│   ├── test_theme_manager.py
│   ├── test_gui_features.py
│   ├── test_screen_recorder.py
│   ├── test_projects.py
│   ├── test_tags_and_i18n.py
│   ├── test_updater.py
│   ├── test_share_dialog.py
│   ├── test_call_recording.py
│   ├── test_proofing.py
│   └── test_security.py
│
└── docs/                            # Documentation-as-Code Specifications
    ├── ARCHITECTURE.md              # System design, schema & component relationships
    ├── ROADMAP.md                   # Feature development roadmap & completed milestones
    ├── DEVELOPMENT_LIFECYCLE.md     # DevSecOps, quality standards & CI/CD pipeline
    └── PUBLIC_MIRROR_SETUP.md       # Zero-token public mirror setup guide
```

---

## 🔒 Security & Privacy

* **100% Local-First:** All notes, project hierarchies, audio recordings, screenshots, and custom dictionaries are stored locally on your machine (`%LOCALAPPDATA%\StickyNotes\`).
* **Zero Telemetry:** No tracking, analytics, or background data collection.
* **Safe HTML & Markdown Sanitization:** Powered by rigorous regex and AST AST SAST audits (`scripts/security_check.py`) guarding against path traversal and XSS.
