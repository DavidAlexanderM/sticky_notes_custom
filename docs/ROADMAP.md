# Sticky Notes - Product & Feature Roadmap

This roadmap outlines the planned development milestones for the Sticky Notes app, from desktop UI refinement to mobile Android/iOS clients and cloud synchronization.

---

## 🗺️ Milestone Overview

```
Phase 1: Desktop Polish & UI Modernization (Q4 2026)
   │
   ▼
Phase 2: Search, Tags & Internationalization (Q1 2027)
   │
   ▼
Phase 3: Encrypted Cloud Sync & Backup (Q2 2027)
   │
   ▼
Phase 4: Mobile Android & iOS Clients (Q3 2027)
   │
   ▼
Phase 5: Smart AI & Voice-to-Text Transcription (Q4 2027)
```

---

## Phase 1: Desktop Polish & UI Modernization (Current)
* [x] Sticky note grid board with responsive card layout.
* [x] Markdown editing with live preview and split-screen mode.
* [x] Custom color palette flyout on right-click.
* [x] Multi-select and mass erase (bulk deletion).
* [x] Note duplication and export (Clipboard, `.md`, `.html`).
* [x] Rich text formatting toolbar (Bold, Italics, Underline, Strikethrough, Code, Lists).
* [x] Multimedia attachments (Pictures, live microphone recording, videos).
* [x] Standalone portable Windows executable packaging (`.exe`).
* [ ] **Modern Aesthetic Revamp:**
  * Redesign toolbar with sleek minimalist SVG line icons.
  * Modern card elevation with subtle borders and media pill badges (`🎙 1 Voice`, `🖼 2 Pics`).
  * Seamless document canvas with generous whitespace.

---

## Phase 2: Search, Tags & Internationalization (i18n)
* [ ] **Instant Search & Filter:**
  * Real-time search bar filtering notes by title and content.
  * Filter by color chips (e.g. show only Mint or Coral notes).
* [ ] **Tags & Folders:**
  * Hash-tag support in Markdown (e.g. `#work`, `#ideas`) that creates clickable filter pills.
* [ ] **Multi-Language UI (i18n):**
  * Language selector in settings (English, Spanish, French, German, Japanese, Chinese, Arabic).
  * Native Right-to-Left (RTL) layout switching for Arabic and Hebrew users.
* [ ] **Pin to Top:**
  * Pin important sticky notes so they always stay at the top of the grid.

---

## Phase 3: Cloud Sync & Revision History
* [ ] **End-to-End Encrypted Cloud Sync:**
  * Sync notes across devices via WebDAV, Google Drive, or optional self-hosted server.
* [ ] **Trash Bin & Recovery:**
  * Deleted notes move to a 30-day Trash bin before permanent removal.
* [ ] **Version History:**
  * Restore previous edits of any note.

---

## Phase 4: Mobile Apps (Android & iOS)
* [ ] **Cross-Platform Mobile App (Flutter or React Native):**
  * Same visual sticky-note card layout optimized for mobile touchscreens.
  * Direct camera attachment (snap a document or whiteboard directly into a note).
  * Native voice memos with background audio recording.
* [ ] **Home Screen Widgets:**
  * Pin sticky notes directly on the Android / iOS home screen.
* [ ] **Offline-First Sync:**
  * Mobile client works 100% offline, syncing whenever internet is restored.

---

## Phase 5: Smart AI & Voice-to-Text
* [ ] **Voice-to-Text Transcription:**
  * Automatically transcribe recorded voice notes into Markdown text using local Whisper or Gemini API.
* [ ] **Smart Summary:**
  * One-click AI summarization of long meeting notes into bullet points.
* [ ] **Auto-Formatting:**
  * Turn raw transcribed audio into organized task lists and action items.
