---
name: sticky-notes-ops
description: >-
  Operational runbook for the Sticky Notes desktop application. Use when inspecting the SQLite database,
  running automated test suites and lifecycle verification gates, building standalone Windows executables,
  or enforcing Documentation-as-Code (DaC) and internationalization standards.
---

# Sticky Notes Operational Skill (`sticky-notes-ops`)

This skill provides step-by-step operational workflows for maintaining, testing, and packaging the **Sticky Notes** desktop application while conserving context window tokens.

---

## 1. Database Operations (Token-Efficient)

**Rule:** Never inspect `notes.db` or files in `attachments/` with `view_file` or direct file dumps. Always use `scripts/db_cli.py` to receive compact JSON.

### Quick Stats
Check total notes, color distribution, and attachment storage size:
```powershell
python scripts/db_cli.py stats
```

### List Notes (Compact)
List the top notes with character count and preview snippets:
```powershell
python scripts/db_cli.py list --limit 5
```

### Retrieve Single Note
Fetch complete details for a specific note UUID:
```powershell
python scripts/db_cli.py get <note-id>
```

### Create / Delete Note via CLI
```powershell
python scripts/db_cli.py create --title "My Title" --content "Markdown body" --color "#FFF9C4"
python scripts/db_cli.py delete <note-id>
```

---

## 2. Pre-Release Lifecycle Verification Gate

Before committing any feature, bugfix, or release, run the automated verification gate:
```powershell
python scripts/verify_lifecycle.py
```

### What this gate verifies in a single command:
1. **Version Integrity:** Confirms `version.py` matches `docs/DEVELOPMENT_LIFECYCLE.md` and `CHANGELOG.md`.
2. **Automated Test Suite:** Runs `tests/test_compatibility_and_media.py`:
   - SQLite CRUD transactions & cascading deletes.
   - Attachment hashing & collision prevention.
   - Microphone presence detection & fallback graceful state.
   - UTF-8 international text encoding across 10 scripts (Arabic, Hebrew, Japanese, Chinese, Hindi, Russian, German, Korean, Greek, Emojis).
3. **Documentation-as-Code:** Verifies existence of required governance docs (`DEVELOPMENT_LIFECYCLE.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CHANGELOG.md`).

---

## 3. Building Standalone Windows Executable & Gift ZIP

To produce a single, portable Windows `.exe` and distribution ZIP for the user or gift recipients:
```powershell
python build_exe.py
```

### Output Artifacts:
- `dist/StickyNotes.exe` (Single-file executable with Qt dependencies bundled)
- `dist/StickyNotes_v1.2.0_Windows.zip` (Portable release archive with README and run instructions)

---

## 4. Feature Development Checklist (Definition of Done)

When implementing changes:
1. Update single source of truth in `version.py` if version is bumped.
2. Update `docs/ARCHITECTURE.md` with any changed APIs, schemas, or components.
3. Add a log entry in `CHANGELOG.md` under `[Unreleased]` or the version header following Keep a Changelog format.
4. Verify tests pass with `python scripts/verify_lifecycle.py`.
5. Format commit message using Conventional Commits (`feat(...)`, `fix(...)`, `docs(...)`).
