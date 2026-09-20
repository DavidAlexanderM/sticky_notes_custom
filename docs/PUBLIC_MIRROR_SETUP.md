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
   git commit -am "chore(release): bump version to v1.5.6"
   git tag v1.5.6
   git push origin main --tags
   ```
3. GitHub Actions will:
   - Run tests and lifecycle verification.
   - Compile the Windows binary and create the `.zip` archive.
   - Publish the private release on `sticky_notes_app`.
   - Automatically push `version.json` and `StickyNotes_v1.5.6_Windows.zip` to `DavidAlexanderM/sticky_notes_releases`!

---

## 4. Multi-Tier Resolution in the App

If an end-user runs Sticky Notes:
- **Tier 1 (Public Mirror Feed)**: Queries `https://raw.githubusercontent.com/DavidAlexanderM/sticky_notes_releases/main/version.json`. Zero credentials required.
- **Tier 2 (Public Release Assets)**: Downloads the binary directly from GitHub releases on `sticky_notes_releases`.
- **Tier 3 (Fallback Direct)**: If the public mirror is unreachable or if a developer has set `GITHUB_TOKEN`, the app falls back to querying `DavidAlexanderM/sticky_notes_app` directly using the token.
- **Custom Mirrors**: Users can also configure a custom HTTP/HTTPS feed URL in **Settings -> Update Settings**.
