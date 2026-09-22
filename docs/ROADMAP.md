# Sticky Notes - Product & Feature Roadmap

This roadmap documents the delivered milestones and future architecture plans for Danielle's Sticky Notes.

---

## 🗺️ Milestone Overview

```
Phase 1: Desktop Polish & WinUI 3 Modernization   ───► [COMPLETED - v1.4.0]
   │
Phase 2: Search, Tags, Stacks, Proofing & i18n   ───► [COMPLETED - v1.6.5]
   │
Phase 2.5: Recording, Native Sharing & Updater    ───► [COMPLETED - v1.7.1]
   │
Phase 3: Encrypted Cloud Sync & Revision History ───► [ACTIVE FOCUS - 2026/2027]
   │
Phase 4: Mobile Android & iOS Clients (Flutter)   ───► [PLANNED - 2027]
   │
Phase 5: Smart AI Transcription & Summarization   ───► [PLANNED - 2027]
```

---

## ✅ Delivered Milestones

### Phase 1: Desktop Polish & UI Modernization (v1.0.0 – v1.4.0)
* [x] **Sticky Note Grid Board:** Responsive card layout with auto-arranging geometry.
* [x] **Markdown Engine:** Three-mode editor (`Edit`, `Split`, `Preview`) with formatted Markdown rendering.
* [x] **Custom Color Palette:** 8-color soft sticky note palette with right-click flyout selector.
* [x] **Multi-Select & Mass Erase:** Bulk note selection and deletion with confirmation.
* [x] **Rich Text Toolbar:** Bold, Italics, Underline, Strikethrough, Code blocks, Lists, and Checklists.
* [x] **Multimedia Attachments:** Local picture embedding, microphone recording, and video attachments.
* [x] **Modern Aesthetic Revamp:** Minimalist SVG toolbar line icons (`icons.py`), card elevation with media pill badges (`🎙 1 Voice`, `🖼 2 Pics`), and generous whitespace.
* [x] **Design Tokens & Theme Manager:** Light, Dark, and warm Sepia themes with instant runtime switching.

### Phase 2: Search, Tags, Stacks & Proofing (v1.5.0 – v1.6.5)
* [x] **Instant Search & Filtering:** Real-time search bar filtering note cards by title and Markdown body content.
* [x] **Color Filter Chips:** Single-click category filtering by note color.
* [x] **Interactive Tagging System:** `#tag` tokens in notes with colored clickable chips.
* [x] **Collapsible Tag Drawer:** Slide-out left panel with dynamic note count badges and custom-tags-first priority ordering.
* [x] **Physical 3D Note Stacks & Projects:** Layered paper stack widget (`StackCard`), drag-to-merge notes into projects, and inline renaming (`F2`).
* [x] **Bilingual Runtime i18n:** 1-click language switching between English (`🌐 EN`) and Spanish (`🌐 ES`) with canonical tag localization.
* [x] **Live In-Editor Proofing Engine:** Real-time spell checking with red squiggly underlines (`pyspellchecker`), right-click suggestions, and custom SQLite user dictionary.
* [x] **OS Theme Detection:** Auto-sync with Windows 10/11 and PowerToys dark mode changes (`WM_THEMECHANGED`, `colorSchemeChanged`).

### Phase 2.5: Recording, Native OS Sharing & Bulletproof Updater (v1.6.7 – v1.7.1)
* [x] **Screen Capture & Snipping Overlay:** Multi-monitor transparent HUD with rubberband selection and coordinate readout.
* [x] **2-Way Audio Call Recording:** WASAPI loopback audio capture recording system speaker audio (calls) and microphone simultaneously with pure Python WAV mixing fallback.
* [x] **Windows OS-Level Native Sharing:** Shell COM integration invoking Windows 10/11 `&Share` flyout for Nearby Share, Bluetooth, and Store apps.
* [x] **Native Protocol Sharing:** Desktop URL schemes for WhatsApp, Telegram, Microsoft Teams, SMS, and Email.
* [x] **Interactive Drag-and-Drop Chip:** `DraggableNoteChip` providing multi-MIME data (`text/plain`, `text/html`, `.zip` package) for dragging notes directly into external applications.
* [x] **Rich Clipboard Export:** Simultaneous copying of formatted HTML, plain text, and rendered note bitmap.
* [x] **Bulletproof Auto-Updater:** Multi-tier feed resolution (public mirror API, cache-busted manifest, private PAT, custom mirror), S3 `NoAuthRedirectHandler`, binary integrity checks (`b"MZ"`/`b"PK"`), 7-page `QStackedWidget` update dialog, and hardened detached self-restart with diagnostic logging.
* [x] **Inno Setup Windows Installer:** Non-admin per-user installer with desktop/Start Menu icons and automatic silent update execution.

---

## 🎯 Active Focus: Phase 3 — Cloud Sync & Revision History
* [ ] **End-to-End Encrypted Cloud Sync:**
  * Zero-knowledge encrypted note synchronization via WebDAV, Nextcloud, or Supabase.
* [ ] **Trash Bin & Safe Recovery:**
  * Soft-deletion moving discarded notes to a 30-day Trash bin before permanent purging.
* [ ] **Version History & Diff Viewer:**
  * Inspect previous edits of any note with visual side-by-side diffs and 1-click rollback.
* [ ] **Pin to Top:**
  * Pin priority sticky notes to remain at the top of the grid regardless of sorting mode.

---

## 📱 Future Focus: Phase 4 — Mobile Android & iOS Clients
* [ ] **Cross-Platform Mobile App (Flutter):**
  * Visual sticky-note card layout optimized for mobile touchscreens.
  * Direct camera attachment (snap a document, whiteboard, or receipt directly into a note).
  * Background voice memo capture.
* [ ] **Home Screen Widgets:**
  * Pin live sticky notes directly onto the Android and iOS home screen.
* [ ] **Offline-First Synchronization:**
  * Seamless offline-first operation with conflict-free automatic synchronization when connectivity is restored.

---

## 🧠 Future Focus: Phase 5 — Smart AI & Transcription
* [ ] **Voice-to-Text Transcription:**
  * Transcribe meeting audio recordings and voice notes into formatted Markdown using on-device Whisper or Gemini API.
* [ ] **AI Summarization & Action Items:**
  * Automatically distill long call recordings or notes into executive summaries and checklist action items.
