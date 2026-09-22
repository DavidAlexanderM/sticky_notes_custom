# Public Releases Mirror Setup Guide

Sticky Notes includes a **Zero-Token Public Releases Mirror** architecture. This enables end-users to receive seamless 1-click update checks and automated downloads without requiring them to generate or paste a GitHub Personal Access Token (PAT), while keeping your primary source code repository (`sticky_notes_app`) 100% private.

---

## 1. How It Works

```
┌────────────────────────────────────────────────────────┐
│   Primary Private Repo: DavidAlexanderM/sticky_notes_app  │
│   (Code, Issues, CI/CD, Secrets)                       │
└────────────────────────┬───────────────────────────────┘
                         │
        [git push origin v1.5.6]
                         │
                         ▼
             GitHub Actions Workflow
          - Compiles StickyNotes.exe (PyInstaller)
          - Packages StickyNotes_vX.Y.Z_Windows.zip
          - Generates version.json manifest
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
   Private Release               Public Mirror Repo:
   (For Developer)          DavidAlexanderM/sticky_notes_releases
                            - Hosts public version.json
                            - Hosts public downloadable .zip assets
                                        │
                                        ▼
                         Sticky Notes Desktop App
                         - Queries public version.json (Zero Token)
                         - Downloads .zip chunked & verified
                         - Applies update & restarts Windows app!
```

---

## 2. One-Time Setup (2 Minutes)

### Step 1: Create the Public Companion Repository
1. Go to GitHub: [Create a new repository](https://github.com/new).
2. Repository name: `sticky_notes_releases`
3. Description: `Public distribution mirror and release feed for Sticky Notes Windows App`.
4. Visibility: **Public**.
5. Initialize with: **Add a README file** (checked).
6. Click **Create repository**.

### Step 2: Create a Mirror Deployment Secret
To allow GitHub Actions in your private repository to automatically push compiled `.zip` releases and the `version.json` feed into your public releases repo:
1. Go to your GitHub user settings: [Personal Access Tokens (classic or fine-grained)](https://github.com/settings/tokens).
2. Generate a token with:
   - Scope: `repo` (Full control of private repositories and public repositories).
3. Copy the generated token.
4. Go to your private repository: `sticky_notes_app` -> **Settings** -> **Secrets and variables** -> **Actions**.
5. Click **New repository secret**:
   - Name: `RELEASE_MIRROR_TOKEN`
   - Value: Paste the copied token.
6. Click **Add secret**.

---

## 3. Releasing New Updates

Whenever you are ready to publish a new version:
1. Bump the version in `version.py` and update `CHANGELOG.md`.
2. Commit and push:
   ```bash
   git commit -am "chore(release): bump version to v1.7.1"
   git tag v1.7.1
   git push custom custom-edition:main --tags
   ```
3. GitHub Actions will:
   - Run all 11 test suites and lifecycle verification.
   - Compile the PyInstaller executable and Inno Setup installer.
   - Publish the private release on `sticky_notes_custom`.
   - Automatically push `version.json`, `StickyNotes_Setup_v1.7.1.exe`, and `StickyNotes_v1.7.1_Windows.zip` to `DavidAlexanderM/sticky_notes_releases`!

---

## 4. Multi-Tier Feed Resolution Hierarchy (v1.6.9+)

When an end-user checks for updates:
- **Tier 1 (Public Mirror Releases API)**: Queries `https://api.github.com/repos/DavidAlexanderM/sticky_notes_releases/releases/latest`. Instant, uncached, zero token required.
- **Tier 2 (Cache-Busted Mirror Manifest)**: If Tier 1 is rate-limited, queries `version.json?nocache={timestamp}` from raw GitHub usercontent.
- **Tier 3 (Authenticated Private Repo API)**: If configured with a GitHub PAT, queries `api.github.com/repos/DavidAlexanderM/sticky_notes_custom/releases/latest`.
- **Tier 4 (Custom Mirror Feed)**: Optional user-configured mirror URL configured in **Update Center -> Update Settings**.

