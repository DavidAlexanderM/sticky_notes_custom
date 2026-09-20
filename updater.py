"""
updater.py - Core Auto-Update Subsystem for Sticky Notes.
Handles background checking, GitHub API interactions (with private repository token support),
resilient chunked downloading with progress tracking, and Windows self-replacement.
"""

import os
import sys
import json
import tempfile
import zipfile
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from PySide6.QtCore import QThread, Signal, QObject

try:
    from .version import __version__, __version_info__, HOMEPAGE
    from .theme_manager import get_preferences_path
except ImportError:
    from version import __version__, __version_info__, HOMEPAGE
    from theme_manager import get_preferences_path

GITHUB_REPO_OWNER = "DavidAlexanderM"
GITHUB_REPO_NAME = "sticky_notes_app"
GITHUB_API_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """Parses version strings like '1.5.4', 'v1.5.4', 'v1.5.4-alpha' into comparable tuples."""
    clean = version_str.strip().lstrip("vV")
    # Discard pre-release tags for numeric tuple comparison
    numeric_part = clean.split("-")[0].split("+")[0]
    parts = []
    for part in numeric_part.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(remote_version_str: str, local_version_str: str = __version__) -> bool:
    """Returns True if the remote version string is strictly newer than local version."""
    return parse_version_tuple(remote_version_str) > parse_version_tuple(local_version_str)


def get_stored_github_token() -> Optional[str]:
    """Retrieves saved GitHub token from preferences or environment variable."""
    env_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_token:
        return env_token

    pref_file = get_preferences_path()
    if pref_file.exists():
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("github_token", "").strip()
                return token if token else None
        except Exception:
            pass
    return None


def save_stored_github_token(token: str):
    """Persists GitHub token in preferences for private repository updates."""
    pref_file = get_preferences_path()
    data = {}
    if pref_file.exists():
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["github_token"] = token.strip()
    try:
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class UpdateCheckWorker(QThread):
    """
    Background worker that queries GitHub releases API without blocking the UI.
    Supports optional GitHub PAT token for private repositories.
    """
    check_finished = Signal(bool, dict)  # (has_update, release_info)
    check_failed = Signal(str, bool)     # (error_message, is_auth_error)

    def __init__(self, token: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.token = token or get_stored_github_token()

    def run(self):
        try:
            req = urllib.request.Request(GITHUB_API_RELEASES_URL)
            req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
            req.add_header("Accept", "application/vnd.github+json")

            if self.token:
                req.add_header("Authorization", f"Bearer {self.token}")

            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status != 200:
                    self.check_failed.emit(f"GitHub returned HTTP {response.status}", False)
                    return

                payload = json.loads(response.read().decode("utf-8"))
                tag_name = payload.get("tag_name", "")
                remote_version = tag_name.lstrip("vV")
                body = payload.get("body", "")
                html_url = payload.get("html_url", "")
                published_at = payload.get("published_at", "")

                # Find Windows ZIP asset
                assets = payload.get("assets", [])
                zip_asset = None
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if name.endswith(".zip") and ("windows" in name or "stickynotes" in name):
                        zip_asset = asset
                        break
                if not zip_asset and assets:
                    zip_asset = assets[0]

                has_update = is_newer_version(remote_version, __version__)

                release_info = {
                    "version": remote_version,
                    "tag_name": tag_name,
                    "body": body,
                    "html_url": html_url,
                    "published_at": published_at,
                    "has_update": has_update,
                    "asset_name": zip_asset.get("name") if zip_asset else None,
                    "asset_size": zip_asset.get("size", 0) if zip_asset else 0,
                    "browser_download_url": zip_asset.get("browser_download_url") if zip_asset else None,
                    "asset_api_url": zip_asset.get("url") if zip_asset else None,
                }

                self.check_finished.emit(has_update, release_info)

        except urllib.error.HTTPError as e:
            is_auth = e.code in (401, 403, 404)
            if is_auth and not self.token:
                msg = "Repository is private or requires authorization. Please configure a GitHub Token."
            else:
                msg = f"GitHub API Error: HTTP {e.code} ({e.reason})"
            self.check_failed.emit(msg, is_auth)
        except urllib.error.URLError as e:
            self.check_failed.emit(f"Network error: Unable to reach GitHub ({e.reason})", False)
        except Exception as e:
            self.check_failed.emit(f"Update check failed: {str(e)}", False)


class UpdateDownloadWorker(QThread):
    """
    Downloads release ZIP in background with granular progress tracking.
    Uses binary octet-stream accept header for authenticated private repo asset downloads.
    """
    progress = Signal(int, int, float)  # (bytes_downloaded, total_bytes, percent)
    download_finished = Signal(str)     # (local_zip_path)
    download_failed = Signal(str)       # (error_message)

    def __init__(self, release_info: dict, token: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.release_info = release_info
        self.token = token or get_stored_github_token()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # Determine download URL:
            # For private repos, query asset_api_url with Accept: application/octet-stream
            if self.token and self.release_info.get("asset_api_url"):
                download_url = self.release_info["asset_api_url"]
                req = urllib.request.Request(download_url)
                req.add_header("Authorization", f"Bearer {self.token}")
                req.add_header("Accept", "application/octet-stream")
            else:
                download_url = self.release_info.get("browser_download_url")
                if not download_url:
                    self.download_failed.emit("No downloadable Windows ZIP asset found in release.")
                    return
                req = urllib.request.Request(download_url)

            req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")

            # Destination temporary file
            temp_dir = Path(tempfile.gettempdir()) / "StickyNotes_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)
            zip_filename = self.release_info.get("asset_name") or f"StickyNotes_v{self.release_info.get('version')}.zip"
            dest_file = temp_dir / zip_filename

            with urllib.request.urlopen(req, timeout=30) as response, open(dest_file, "wb") as out_file:
                total_bytes = int(response.headers.get("Content-Length") or self.release_info.get("asset_size", 0))
                downloaded_bytes = 0
                chunk_size = 64 * 1024  # 64 KB chunks

                while True:
                    if self._is_cancelled:
                        self.download_failed.emit("Download cancelled by user.")
                        return

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    out_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    percent = (downloaded_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0
                    self.progress.emit(downloaded_bytes, total_bytes, percent)

            self.download_finished.emit(str(dest_file))

        except Exception as e:
            self.download_failed.emit(f"Failed to download update: {str(e)}")


def apply_update_and_restart(zip_path_str: str) -> bool:
    """
    Extracts the updated package and executes an asynchronous Windows batch script
    that swaps the application files once the current process exits, then relaunches.
    """
    zip_path = Path(zip_path_str)
    if not zip_path.exists():
        return False

    temp_extract_dir = zip_path.parent / "extracted"
    if temp_extract_dir.exists():
        import shutil
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
    temp_extract_dir.mkdir(parents=True, exist_ok=True)

    # Extract downloaded zip
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract_dir)
    except Exception as e:
        print(f"[ERROR] Failed to extract update ZIP: {e}")
        return False

    # Find the folder containing StickyNotes.exe
    payload_dir = temp_extract_dir
    candidates = list(temp_extract_dir.glob("**/StickyNotes.exe"))
    if candidates:
        payload_dir = candidates[0].parent

    # Target directory to overwrite
    if getattr(sys, 'frozen', False):
        app_target_dir = Path(sys.executable).resolve().parent
        exe_path = Path(sys.executable).resolve()
    else:
        # Development mode: Cannot overwrite running python files in place
        return False

    current_pid = os.getpid()
    bat_path = zip_path.parent / "apply_update.bat"

    # Batch script waits for the existing process to terminate, copies files, and restarts
    batch_script = f"""@echo off
setlocal enabledelayedexpansion
echo [Sticky Notes Updater] Waiting for application (PID {current_pid}) to close...

:WAIT_LOOP
tasklist /fi "pid eq {current_pid}" | find "{current_pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto WAIT_LOOP
)

echo [Sticky Notes Updater] Applying update files...
robocopy "{payload_dir}" "{app_target_dir}" /E /NP /R:3 /W:1 >nul

echo [Sticky Notes Updater] Relaunching application...
start "" "{exe_path}"

echo [Sticky Notes Updater] Cleaning up staging files...
timeout /t 2 /nobreak >nul
rd /s /q "{temp_extract_dir}" >nul 2>&1
del "{zip_path}" >nul 2>&1
(goto) 2>nul & del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(batch_script)

    # Launch batch script in a detached process and terminate application
    subprocess.Popen(
        ["cmd.exe", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True
    )

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        app.quit()
    sys.exit(0)
