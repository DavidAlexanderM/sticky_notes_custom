# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- End-to-end encrypted cloud sync and revision history.
- Cross-platform mobile clients for Android and iOS.

## [1.6.9] - 2026-09-21

### Fixed & Overhauled
- **Bulletproof In-App Auto-Updater (`updater.py`):**
  - Multi-tier feed resolution: Prioritizes public mirror GitHub Releases API (`PUBLIC_MIRROR_API_URL`) as Tier 1, delivering instant, real-time release metadata with zero GitHub token required.
  - Implemented CDN cache-busting on raw manifest queries (`?nocache=timestamp` with `Cache-Control: no-cache`), eliminating edge caching lag.
  - Added `NoAuthRedirectHandler` to safely strip `Authorization` headers when redirecting to external AWS S3 / `objects.githubusercontent.com` storage, preventing AWS S3 `400 Bad Request` errors.
  - Added binary integrity validation: verifies file size (> 100 KB) and executable signatures (`b"MZ"` for setup `.exe`, `b"PK"` for `.zip`) before passing binaries to the installer.
  - Refined silent self-updating script (`apply_update.bat`) with `/NORESTART /CLOSEAPPLICATIONS` and clean PID termination wait loop.
- **Permanent Button Overlap Elimination (`UpdateDialog`):**
  - Architecturally refactored from dynamic widget destruction (`_clear_card()`) to a native `QStackedWidget` system with 7 dedicated, isolated pages.
  - Completely prevents buttons and layouts from overlapping during state transitions (Checking, Up to Date, Update Available, Downloading, Install Ready, Settings, Error).
  - Added `get_active_buttons()` helper for seamless page-scoped testing and inspection.

## [1.6.8] - 2026-09-21

### Fixed & Improved
- **Screen Capture Keyboard Activation & Focus Grab (`SnippingOverlay`):**
  - Added `Qt.FocusPolicy.StrongFocus`, `self.activateWindow()`, `self.setFocus()`, and `self.grabKeyboard()` in `showEvent` so `Esc` (cancel) and `Enter` (full screenshot) work immediately without needing to click first.
  - Safe `releaseKeyboard()` lifecycle management during overlay acceptance, rejection, and closing.
- **Dependency-Free Audio Call & Meeting Recording (`media_manager.py`):**
  - Added `mix_wav_files_pure_python` using `numpy` and `wave` to mix dual-channel call audio (system loopback + microphone) with automatic sample rate resampling and channel alignment.
  - Call recording now works 100% reliably out of the box on any Windows PC, even when `ffmpeg.exe` is not installed.
  - Implemented `get_ffmpeg_path()` to auto-discover bundled, portable, and system FFmpeg binaries.
  - Bundled FFmpeg into release packages in `build_exe.py` and GitHub Actions workflow for crystal-clear H.264 screen video recording.
- **Native Media Sharing Center (`ShareNoteDialog`):**
  - Upgraded plain-text stripping to clean local `file:///` URLs into readable labels (`[Image: name.png]`, `[Play Voice Note: name.wav]`) while keeping web links intact.
  - Added **Copy Image to Clipboard**: copies image bitmaps directly to Windows clipboard for instant `Ctrl+V` pasting into WhatsApp, Telegram, Discord, Word, etc.
  - Added **Copy Media File(s) to Clipboard**: copies file paths into native clipboard MIME data.
  - Added **Export Note Package (.zip)**: bundles the note markdown (with portable relative links) and embedded `attachments/` folder into a standalone `.zip`.
  - Added **Reveal in Explorer**: locates and selects note attachments in Windows File Explorer.
  - Automated WhatsApp and Telegram buttons to copy image/media to clipboard prior to opening chat.

## [1.6.7] - 2026-09-21

### Added & Improved
- **Two-Way Audio & Call Recording via Windows WASAPI Loopback:**
  - Implemented `WasapiAudioRecorder` utilizing `PyAudioWPatch` to capture system audio output (headphones/speakers) and microphone input simultaneously.
  - Added multi-mode audio capture options:
    - 🎧 **Call / Meeting Mode (Both Voices - Recommended)**: Blends incoming caller audio and Danielle's microphone into a clean, normalized dual-track recording via FFmpeg.
    - 🔊 **Computer Audio Only**: Captures remote callers, webinar presentations, or computer media without room microphone background noise.
    - 🎙️ **Microphone Only**: Classic voice memo recording.
  - Silent keepalive stream keeps Windows WASAPI audio clocks active during conversation pauses, preventing dropped packets or audio sync drifts.
- **Screen & Video Call Recording Audio Overhaul:**
  - Integrated call audio recording into `ScreenRecorder`, allowing full video recording of online meetings, webinars, and video calls with both picture and balanced two-way audio.
- **User Interface Enhancements:**
  - `VoiceRecorderDialog`: Added audio source selector and live device status indicator displaying detected speaker and microphone endpoints.
  - `ScreenRecorderDialog`: Added call audio recording checkbox and mode selector, with scoped frame styling eliminating accidental label borders.

## [1.6.6] - 2026-09-21

### Fixed & Improved
- **Multi-Monitor Screen Capture & Snipping HUD (`SnippingOverlay`):**
  - Expanded screen capture to composite all connected displays across the virtual desktop coordinate system (`QGuiApplication.screens()`), allowing seamless snipping across dual and multi-screen setups.
  - Added a prominent, high-contrast HUD instruction banner (`📸 Drag to capture a region • Enter: Full Screen • Esc / Right-Click: Cancel`) positioned top-center in deep slate `#0F172A` with pure white text.
  - Replaced fixed-width dimension badge with dynamically measured `QFontMetrics` pill and vibrant `#0096FF` accent border, ensuring crystal-clear readability against any desktop background.
- **Update Center Button Overlap & Frame Styling Fix (`UpdateDialog`):**
  - Resolved button overlay bug during updater state transitions by completely purging nested layouts and unparenting child widgets in `_clear_card()`.
  - Fixed stylesheet inheritance on `QFrame` which was causing `QLabel` and `QTextBrowser` elements to inherit unintended borders and padding, restoring clean margins, layout hierarchy, and spacing.
- **Screen Recording Display Discovery & Dropdown Contrast:**
  - Enhanced display monitor dropdown labeling with resolution, index, and primary monitor indicator (`Monitor 1: 1920×1080 (Primary)`).
  - Added global high-contrast `QComboBox` and `QAbstractItemView` styling across light, dark, and sepia themes to prevent illegible dark-on-dark text in Windows drop-downs.
  - Increased typography size and contrast in `RecordingCompleteDialog`.

## [1.6.5] - 2026-09-21

### Added & Improved
- **1-Touch Media Action Buttons (`FormatToolbar`):**
  - **Audio Recording (`🎙️ Audio`):** Instant 1-touch button opening voice recorder dialog without intermediary menus.
  - **Screen Capture (`📸 Capture`):** Instant 1-touch desktop snipping tool with interactive drag selection, dimension overlay, and markdown embedding.
  - **Video Recording (`🎥 Video`):** Instant 1-touch screen video recording trigger.
  - **Consolidated Media Clip Menu (`📎 Attach ▾`):** Unified attachment picker for images, audio files, video files, and quick access to the attachments folder.
- **Live In-Editor Spell Checking & Proofing Engine (`proofing_engine.py`):**
  - Real-time typographical checking underlining misspelled words with Qt's native wavy red squiggles (`SpellCheckUnderline`).
  - Markdown-aware tokenization: Automatically skips URLs, emails, code blocks, task checkboxes, and markdown symbols.
  - Right-click spelling correction suggestions (`💡 {suggestion}`) for instant word replacement.
  - **Personal Dictionary Persistence:** "Add to Personal Dictionary" action saving custom terms into SQLite (`user_dictionary` table).
  - **Session Word Ignoring:** "Ignore Word" action for temporary omission.
  - **Bilingual Proofing:** Automatically mirrors the active application language (`English` or `Español`) with full support for Spanish accents.
  - **Toolbar Proofing Toggle:** Dedicated `ABC✓` button on the format toolbar to enable or disable proofing on the fly.

## [1.6.4] - 2026-09-20

### Added & Fixed
- **Collapsible Tag Side Panel (`TagSidePanel`):**
  - Dedicated left sidebar for 1-click note tag filtering, eliminating the need for keyboard-only hashtag typing.
  - **Custom Tags Ordered FIRST:** User-created custom tags strictly appear at the top of the panel and selection flyouts for instant access, followed by predetermined system tags below.
  - Live count badges dynamically tracking active notes per tag, with top filters for "All Notes" and "Untagged".
  - Full tag management: Create custom tags with automatic color palette assignment, inline renaming, and deletion with cascading tag updates.
- **1-Click Tag Assignment Flyout (`TagSelectorFlyout`):**
  - Accessible via note card action menu (`Manage Tags...`) and editor view header (`🏷️`).
  - Instant checkbox assignment with Custom Tags first, Predetermined Tags second, and inline new tag creation.
- **Bilingual Internationalization Engine (`i18n.py`):**
  - Instant runtime language switching between English and Spanish via header toggle button (`🌐 EN` / `🌐 ES`).
  - Persistent language preference stored in `preferences.json`.
  - Canonical cross-language predetermined tag matching, synchronizing counts and filters across English and Spanish.
- **Visual Note Card Tag Badges (`NoteCard`):**
  - Modern, subtle `#Tag` badge chips rendered directly on board note cards.
- **Architectural Guardrails & UI Verification:**
  - Automated headless snapshot generator (`capture_tags_verification.py`).
  - Layout detachment safety (`setParent(None)`) preventing Qt deferred deletion ghosting.

## [1.6.3] - 2026-09-20

### Added & Fixed
- **Textless Minimalist Color Filter Swatch Pills:**
  - Eliminated textual color labels from filter pills in Grid View, retaining purely visual, circular color dots (24x24 px).
  - Implemented high-contrast active selection rings, hover borders, and rich tooltips indicating the color name and filter function.
  - Dynamically updates pill borders and accent rings on light, dark, and sepia theme transitions.
- **Physical 3D Note Stacks with Drag-and-Drop Organization (`StackCard`):**
  - **Drag-to-Merge Note Stacks:** Users can drag free notes directly over each other to merge them into a project stack with automatic sequential naming (`Stack 1`, `Stack 2`, etc.).
  - **Physical Paper 3D Visuals:** Implemented multi-layered paper cards with subtle rotational offsets (-3.8° and +3.2°), paper drop shadows, and true note color previews mirroring the actual colors of notes inside the stack.
  - **In-Place Inline Renaming:** Users can rename stacks inline directly from the card by pressing `F2` or double-clicking the stack title.
  - **Drag-to-Add Notes:** Dragging any note onto an existing `StackCard` highlights the target stack with a glowing border and adds the note to the stack.
  - **Stack Navigation & Breadcrumb:** Double-clicking a `StackCard` opens that stack's collection view with a dedicated `← Back to Board` button in the header.
  - **Stack Dissolving:** Added "Unstack All Notes (Dissolve)" in the stack menu to unpack all grouped notes back into individual free notes on the board.

## [1.6.2] - 2026-09-20

### Added & Fixed
- **Color Filter Swatches & Sort by Creation Date:**
  - Replaced text-only chips with circular, anti-aliased real color swatches for all 8 sticky note colors with tooltips and active focus indicators.
  - Added Sort Dropdown selector (`📅 Created (Newest)`, `📅 Created (Oldest)`, `⏱️ Recently Edited`, `⏱️ Oldest Edited`, `🔤 Title (A-Z)`) with persistent user preference in `preferences.json`.
- **Physical Note Stack Visuals for Projects:**
  - Implemented 3D vector layered note stack icons (`render_note_stack_icon`) featuring multi-layer offset post-its with drop shadow depth and dynamic project accent coloring.
  - Applied note stack icons across the main project switcher button, dropdown menu, and NoteCard "Move to Stack" menus.
- **Help & Storage Diagnostics Readability:**
  - Wrapped the About & Storage tab in a dedicated `QScrollArea` with increased default dialog dimensions (`680x560`) to eliminate text clipping.
  - Enhanced Database and Attachments path display with read-only `QLineEdit` fields, 1-click `📋 Copy` buttons with status feedback, and `📂 Open Folder` shortcuts.
- **PowerToys & Windows Auto Theme Switching:**
  - Resolved `QByteArray` type mismatch in `_WindowsThemeEventFilter` native event listener and added `WM_THEMECHANGED (0x031A)` alongside `WM_SETTINGCHANGE (0x001A)`.
  - Connected Qt 6.5+ native `QGuiApplication.styleHints().colorSchemeChanged` signal for zero-latency cross-platform theme change notifications.
  - Inspected both `AppsUseLightTheme` and `SystemUsesLightTheme` Windows registry keys, ensuring full compatibility with PowerToys dark mode toggles.
- **Auto-Updater Windows Execution & Relaunch:**
  - Replaced input-redirected `timeout` calls in detached batch scripts with failsafe `ping 127.0.0.1 -n 2 >nul`.
  - Added native standalone installer executable (`.exe`) detection and background silent installation (`/SILENT /CLOSEAPPLICATIONS`).
  - Improved Development Mode messaging and added direct installer launching via safe `os.startfile`.

---

## [1.6.1] - 2026-09-20

### Added & Fixed
- **Universal Desktop Screen Recording Engine (`media_manager.py`):**
  - Implemented `FrameCaptureThread` background capture pipeline using `QScreen.grabWindow` piped directly to FFmpeg (`libx264`, `yuv420p`, `ultrafast`).
  - Completely resolves Windows DXGI Output Duplication COM error `0x80070005 (Access is denied)` on multi-GPU setups (Intel/AMD integrated + NVIDIA discrete) and session isolation.
  - Synchronized audio-video capture: records microphone commentary simultaneously to temporary WAV and muxes H.264 video + AAC audio into MP4 seamlessly in <0.2s.
  - Preserves graceful fallback to Qt6 `QScreenCapture` / `QMediaRecorder` when FFmpeg is not installed.
- **Recording Complete Confirmation Modal (`components/screen_recorder_dialog.py`):**
  - Added `RecordingCompleteDialog` modal presenting video filename, elapsed duration, file size, and exact local path on disk.
  - Quick actions: `▶️ Play Video` (in default media player), `📂 Show in Folder` (revealing and highlighting the file in Windows Explorer), `📋 Copy Path`, and `✓ Done`.
  - Note editor automatically activates `split` view mode on recording completion so the playable video link and preview are immediately visible.
- **Attachments Folder Explorer Quick-Access (`components/format_toolbar.py` & `views/editor_view.py`):**
  - Added `📂 Open Attachments Folder...` action to the toolbar's Video dropdown menu, allowing instant access to `%LOCALAPPDATA%\StickyNotes\attachments` or the local workspace attachments directory.

---

## [1.6.0] - 2026-09-20

### Added & Improved
- **Project Stacks & Note Collections:**
  - Multi-project database architecture with schema migration: organizes notes into separate project stacks (e.g. "Doctora", "Research", "Work", "Personal") with zero data loss for existing notes.
  - Active project stack persistence: application remembers the last active stack and reopens directly to that collection on startup.
  - Header Project Switcher dropdown: 1-click switching with live note counts, colored stack accents, and "All Notes" global overview mode.
  - Project Management Dialog (`components/project_dialog.py`): create new project stacks with custom accent colors, rename existing stacks, and safely delete projects with automatic reassignment of all notes to "General Notes".
  - Move Notes across Stacks: 1-click stack reassignment via NoteCard context menu (`Move to Stack`) and batch reassignment across multi-selected notes via the bottom action bar.
  - Note Editor Stack Badge: in-editor stack indicator and quick-switcher allowing seamless project reassignment while editing notes.
  - Comprehensive automated test suite (`tests/test_projects.py`) covering all CRUD operations, filtering, safe deletion, and UI interactions.

---

## [1.5.8] - 2026-09-20

### Added & Improved
- **Desktop Screen Recording (`ScreenRecorder` & `ScreenRecorderDialog`):**
  - Native hardware-accelerated desktop screen recording engine using Qt6's `QScreenCapture` and `QMediaRecorder` with Windows Media Foundation H.264 (`h264_mf`) MP4 encoding.
  - Multi-monitor / display selector allowing users to record any connected monitor at native resolution.
  - Optional synchronized microphone commentary / narration toggle with device selection.
  - Compact, draggable floating HUD overlay widget (`ScreenRecordingOverlay`) that stays on top during capture with live recording indicator (`🔴 REC`), elapsed timer, and 1-click Stop/Cancel controls.
  - Upgraded formatting toolbar **Video** button to offer an instant choice between `🔴 Record Desktop Screen...` and `📁 Choose Existing Video File...`.
  - Automatic note integration: saves recordings directly into `attachments/` and embeds a playable markdown link.

---

## [1.5.7] - 2026-09-20

### Added & Improved
- **Official Windows Installer (`StickyNotes_Setup_v1.5.7.exe`):**
  - Integrated **Inno Setup** compiler script (`installer.iss`) into the CI/CD pipeline.
  - Non-administrative per-user installation target (`%LOCALAPPDATA%\Programs\StickyNotes`) that completely avoids Windows UAC administrator elevation prompts.
  - Creates Start Menu entry, optional Desktop shortcut, and registers in Windows Settings (Installed Apps) with version info, publisher, and 1-click uninstaller.
  - Multi-language installer support (English and Spanish).
- **Embedded Multi-Resolution Windows Icon:**
  - Designed and generated multi-size application icon (`assets/icon.ico`: 16, 24, 32, 48, 64, 128, 256 px).
  - Embedded into `StickyNotes.exe` via PyInstaller and registered in the installer and Start Menu.

---

## [1.5.6] - 2026-09-20

### Added & Improved
- **Zero-Token Public Releases Mirror Architecture:**
  - Integrated public feed support enabling end-users to check and install software updates with 1-click **without requiring any GitHub Personal Access Token (PAT)**.
  - Multi-tier update resolution:
    1. Queries the Public Mirror Feed (`https://raw.githubusercontent.com/DavidAlexanderM/sticky_notes_releases/main/version.json`) or mirror release endpoint anonymously.
    2. Gracefully falls back to private repository querying (`DavidAlexanderM/sticky_notes_app`) if a Personal Access Token is configured.
  - Added Update Settings UI in `UpdateDialog` to view the active feed source (`🌐 Public Releases Mirror` vs `🔒 GitHub Private API`), configure custom mirror URLs, test connectivity on demand, and restore default feeds.
- **Automated CI/CD Mirroring Pipeline:**
  - Enhanced GitHub Actions workflow (`.github/workflows/build.yml`) to automatically generate `version.json` release manifests via `scripts/generate_release_manifest.py`.
  - Added automated release synchronization: when a version tag (`v*`) is pushed, CI compiles the Windows package and publishes it directly to both the private repository and the public companion mirror (`sticky_notes_releases`).
  - Added complete setup documentation in `docs/PUBLIC_MIRROR_SETUP.md`.

---

## [1.5.5] - 2026-09-20

### Added & Improved
- **Integrated In-App Auto-Updater (`updater.py` & `UpdateDialog`):**
  - Seamless background update checker querying GitHub Releases API with support for both public and **private repositories** (using Personal Access Tokens / fine-grained tokens).
  - Modal Software Update Center (`components/update_dialog.py`) displaying current version, latest release version, release date, and full markdown changelog preview.
  - One-click chunked downloading with live progress bar and downloaded MB counter.
  - Seamless Windows self-update replacement (`apply_update.bat`) that swaps application files and relaunches automatically.
  - **Check for Updates** button added directly to Tab 3 (*About & Storage*) of the Help & About dialog.
  - Non-intrusive delayed background update check (3.5s after launch) that adds a subtle `✨ vX.Y.Z Available` notification pill to the app header when updates are detected.

---

## [1.5.4] - 2026-09-20

### Added & Improved
- **Real-Time Automatic OS Theme Detection:**
  - Implemented live Windows OS theme monitoring in `ThemeManager` using a dual-layer strategy: native Windows `WM_SETTINGCHANGE` event filter combined with an infallible background polling timer.
  - Sticky Notes now switches between Dark and Light mode in real-time as soon as the user changes Windows Settings.
  - Added tri-state theme cycling: `System (Auto) -> Dark -> Light -> System (Auto)`.
  - Added right-click theme switcher menu to `theme_btn` on both Grid and Editor views, giving 1-click access to *Follow Windows Theme (Auto)*, *Dark Theme*, *Light Theme*, and *Sepia Theme*.
  - Reset default preference to `"system"`.
- **Empowered Multi-App & OS Sharing Center (`ShareNoteDialog`):**
  - Upgraded Note Sharing into a rich, dedicated modal dialog accessible from card menus, palette flyout, and the editor header.
  - One-click transmission to **Email** (Outlook / Windows Mail / Thunderbird), **WhatsApp** (Desktop / Web), **Telegram**, **Facebook**, and **X (Twitter)**.
  - Integrated fast clipboard actions: Copy Markdown and Copy Plain Text (with automatic regex markdown stripping).
  - Export to Markdown (`.md`) and styled standalone HTML (`.html`) files.
  - Note metadata preview featuring word count, character count, and formatted text snippet.

---

## [1.5.3] - 2026-09-20

### Added & Improved
- **Antigravity 2.0 Dark Palette Integration:**
  - Upgraded the Dark theme canvas from saturated navy blue (`#0F172A`/`#1E293B`) to neutral carbon obsidian (`#131314` canvas, `#1E1F20` elevated container surface, `#444746` neutral outline border).
  - Adopted Gemini electric light blue (`#8AB4F8`) for accents, links, and selected tab indicators, with contrasting dark navy label fill (`#041E49`).
  - Added neutral high-contrast buttons (`#28292A` background, `#333537` hover, `#E3E3E3` bright white text).
- **Comprehensive Help Dialog Contrast & Theming Fix:**
  - Resolved dark-on-dark unreadable text in the Help & About dialog (`HelpAboutDialog`).
  - Shortcut badges dynamically styled: light translucent Gemini blue background with `#8AB4F8` text and border in Dark theme.
  - Markdown syntax blocks and about info container now utilize `#131314` background with `#444746` borders and `#E3E3E3` text.
  - Dynamic re-theming support upon theme switch while the dialog is open.
- **Voice Recorder & Dialog Contrast:**
  - Upgraded `VoiceRecorderDialog` to inherit tokenized colors from active theme palette.
  - Global `QDialog` and `QDialog QLabel` text color guarantee (`#E3E3E3` in Dark mode).

---

## [1.5.2] - 2026-09-20

### Added
- **Fluid Shift/Ctrl Multi-Selection:**
  - Standard desktop multi-selection: `Shift + Click` extends continuous range selection, `Ctrl + Click` toggles individual cards in a group.
  - Automatically displays bottom `SelectionActionBar` with note count, Select All, Delete Selected, and Clear when \(\ge 1\) notes are selected.
  - Retired the old modal "Select" header button for a streamlined, non-blocking workflow.
- **Unified Themed Popups & Context Menus:**
  - `ColorPickerFlyout` and `QMenu` now dynamically match the application's active theme (Dark, Light, Sepia). Eliminates hardcoded white popups when running in Dark theme.
  - Action buttons in color flyout and card menus upgraded with vector SVG icons (`copy`, `share`, `trash`).
- **Comprehensive Help & About Center (`HelpAboutDialog`):**
  - Dedicated Help button (❓) in headers and accessible via `F1` / `Ctrl+H`.
  - Tab 1: Visual Keyboard Shortcuts cheatsheet (Arrow navigation, Enter, Delete, Shift/Ctrl clicks, formatting shortcuts).
  - Tab 2: Markdown & Media attachments reference guide.
  - Tab 3: About metadata, database location, and 1-click button to open local attachments folder in Windows Explorer.
- **Full Keyboard Navigation in Notes Grid:**
  - Arrow keys (↑, ↓, ←, →) navigate and focus cards.
  - `Shift + Arrows` expands/shrinks selection range.
  - `Enter` / `Return` opens focused note in full editor.
  - `Delete` / `Backspace` deletes selected notes with confirmation.
  - `Ctrl + A` selects all notes; `Escape` clears selection or search filter.
  - `Ctrl + N` creates a note; `Ctrl + F` focuses search bar.
- **OS-Dependent Theme Detection (Icon-Only Buttons):**
  - Auto-detects Windows dark/light mode preference (`AppsUseLightTheme`).
  - Theme toggle buttons in Grid and Editor views are now icon-only (`sun` / `moon` / `monitor`) without text labels.
- **Cleaned Header:**
  - Removed verbose instructions subtitle from main header.

---

## [1.5.1] - 2026-09-20

### Fixed
- **Startup Crash in `NoteEditorView` Initialization:**
  - Resolved `AttributeError: 'NoteEditorView' object has no attribute 'play_pause_btn'` caused by premature invocation of `_update_header_icons()` before the in-app audio player frame was instantiated.
  - Added defensive `hasattr()` checks across all header and audio player button icon updates.
  - Added comprehensive end-to-end instantiation and theme toggle regression tests in `tests/test_gui_features.py` for both `NoteEditorView` and `MainWindow`.

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
