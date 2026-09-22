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
GITHUB_REPO_NAME = "sticky_notes_custom"
GITHUB_API_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

PUBLIC_MIRROR_REPO_OWNER = "DavidAlexanderM"
PUBLIC_MIRROR_REPO_NAME = "sticky_notes_releases"
DEFAULT_PUBLIC_MANIFEST_URL = f"https://raw.githubusercontent.com/{PUBLIC_MIRROR_REPO_OWNER}/{PUBLIC_MIRROR_REPO_NAME}/main/version.json"
PUBLIC_MIRROR_API_URL = f"https://api.github.com/repos/{PUBLIC_MIRROR_REPO_OWNER}/{PUBLIC_MIRROR_REPO_NAME}/releases/latest"


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


def get_stored_mirror_url() -> str:
    """Retrieves saved custom mirror URL from preferences or returns default."""
    pref_file = get_preferences_path()
    if pref_file.exists():
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                url = data.get("mirror_url", "").strip()
                if url:
                    return url
        except Exception:
            pass
    return DEFAULT_PUBLIC_MANIFEST_URL


def save_stored_mirror_url(url: str):
    """Persists custom mirror URL in preferences."""
    pref_file = get_preferences_path()
    data = {}
    if pref_file.exists():
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["mirror_url"] = url.strip()
    try:
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def parse_release_payload(payload: dict, source_name: str = "mirror") -> dict:
    """Extracts standardized release metadata from either GitHub API or version.json manifest."""
    # Check if this is a version.json manifest format
    if "version" in payload and ("browser_download_url" in payload or "asset_name" in payload):
        tag_name = payload.get("tag_name") or f"v{payload.get('version')}"
        remote_version = payload.get("version", "").lstrip("vV")
        body = payload.get("body", "")
        html_url = payload.get("html_url", "")
        published_at = payload.get("published_at", "")
        has_update = is_newer_version(remote_version, __version__)
        return {
            "version": remote_version,
            "tag_name": tag_name,
            "body": body,
            "html_url": html_url,
            "published_at": published_at,
            "has_update": has_update,
            "asset_name": payload.get("asset_name"),
            "asset_size": payload.get("asset_size", 0),
            "browser_download_url": payload.get("browser_download_url"),
            "asset_api_url": payload.get("asset_api_url"),
            "installer_name": payload.get("installer_name"),
            "installer_size": payload.get("installer_size", 0),
            "installer_url": payload.get("installer_url"),
            "source": source_name,
        }

    # Otherwise treat as GitHub Release API payload
    tag_name = payload.get("tag_name", "")
    remote_version = tag_name.lstrip("vV")
    body = payload.get("body", "")
    html_url = payload.get("html_url", "")
    published_at = payload.get("published_at", "")

    assets = payload.get("assets", [])
    zip_asset = None
    exe_asset = None
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and ("windows" in name or "stickynotes" in name):
            zip_asset = asset
        elif name.endswith(".exe") and ("setup" in name or "installer" in name):
            exe_asset = asset

    if not zip_asset and assets:
        zip_asset = assets[0]

    has_update = is_newer_version(remote_version, __version__)
    return {
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
        "installer_name": exe_asset.get("name") if exe_asset else payload.get("installer_name"),
        "installer_size": exe_asset.get("size", 0) if exe_asset else payload.get("installer_size", 0),
        "installer_url": exe_asset.get("browser_download_url") if exe_asset else payload.get("installer_url"),
        "source": source_name,
    }


class NoAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Prevents Authorization headers from leaking to external CDN/S3 storage
    during GitHub release asset redirects, which causes S3 HTTP 400 Bad Request errors.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            try:
                from urllib.parse import urlparse
                new_host = urlparse(newurl).netloc.lower()
                if "api.github.com" not in new_host:
                    for h in list(new_req.headers.keys()):
                        if h.lower() == "authorization":
                            del new_req.headers[h]
                    for h in list(getattr(new_req, "unredirected_hdrs", {}).keys()):
                        if h.lower() == "authorization":
                            del new_req.unredirected_hdrs[h]
            except Exception:
                pass
        return new_req


class UpdateCheckWorker(QThread):
    """
    Background worker that queries software update feeds.
    Multi-tier resolution:
      1. Public Mirror API (Instant, uncached GitHub Releases API, zero token required)
      2. Public Mirror Raw Manifest with CDN cache-buster (?nocache=timestamp)
      3. Direct GitHub API (with optional PAT for private repository)
      4. Custom Mirror URL (if configured)
    """
    check_finished = Signal(bool, dict)  # (has_update, release_info)
    check_failed = Signal(str, bool)     # (error_message, is_auth_error)

    def __init__(self, token: Optional[str] = None, mirror_url: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.token = token or get_stored_github_token()
        self.mirror_url = mirror_url or get_stored_mirror_url()

    def run(self):
        try:
            # Tier 1: Public Mirror Releases API (Instant & Zero-token)
            try:
                req = urllib.request.Request(PUBLIC_MIRROR_API_URL)
                req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
                req.add_header("Accept", "application/vnd.github+json")
                with urllib.request.urlopen(req, timeout=8) as response:
                    if response.status == 200:
                        payload = json.loads(response.read().decode("utf-8"))
                        release_info = parse_release_payload(payload, source_name="public_mirror")
                        self.check_finished.emit(release_info["has_update"], release_info)
                        return
            except Exception:
                pass

            # Tier 2: Public Mirror Raw Manifest (Cache-Busted)
            raw_url = self.mirror_url or DEFAULT_PUBLIC_MANIFEST_URL
            try:
                import time
                sep = "&" if "?" in raw_url else "?"
                busted_url = f"{raw_url}{sep}nocache={int(time.time())}"
                req = urllib.request.Request(busted_url)
                req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
                req.add_header("Accept", "application/json, text/plain, */*")
                req.add_header("Cache-Control", "no-cache, no-store, must-revalidate")
                req.add_header("Pragma", "no-cache")
                with urllib.request.urlopen(req, timeout=8) as response:
                    if response.status == 200:
                        payload = json.loads(response.read().decode("utf-8"))
                        release_info = parse_release_payload(payload, source_name="public_mirror")
                        self.check_finished.emit(release_info["has_update"], release_info)
                        return
            except Exception:
                pass

            # Tier 3: Direct Private Repo via GitHub API (if token available)
            if self.token:
                try:
                    req = urllib.request.Request(GITHUB_API_RELEASES_URL)
                    req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
                    req.add_header("Accept", "application/vnd.github+json")
                    req.add_header("Authorization", f"Bearer {self.token}")
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 200:
                            payload = json.loads(response.read().decode("utf-8"))
                            release_info = parse_release_payload(payload, source_name="private_repo")
                            self.check_finished.emit(release_info["has_update"], release_info)
                            return
                except Exception:
                    pass

            # Tier 4: Custom Mirror URL fallback (if different from default)
            if self.mirror_url and self.mirror_url != DEFAULT_PUBLIC_MANIFEST_URL:
                try:
                    req = urllib.request.Request(self.mirror_url)
                    req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")
                    req.add_header("Accept", "application/json, text/plain, */*")
                    with urllib.request.urlopen(req, timeout=8) as response:
                        if response.status == 200:
                            payload = json.loads(response.read().decode("utf-8"))
                            release_info = parse_release_payload(payload, source_name="custom_mirror")
                            self.check_finished.emit(release_info["has_update"], release_info)
                            return
                except Exception:
                    pass

            self.check_failed.emit(
                "Unable to retrieve release metadata from GitHub or update feeds.",
                not bool(self.token)
            )

        except urllib.error.HTTPError as e:
            is_auth = e.code in (401, 403, 404)
            if is_auth and not self.token:
                msg = (
                    "Public mirror is currently not reachable and the repository is private. "
                    "Please configure a GitHub Personal Access Token or verify your Mirror URL."
                )
            else:
                msg = f"GitHub API Error: HTTP {e.code} ({e.reason})"
            self.check_failed.emit(msg, is_auth)
        except urllib.error.URLError as e:
            self.check_failed.emit(f"Network error: Unable to reach update servers ({e.reason})", False)
        except Exception as e:
            self.check_failed.emit(f"Update check failed: {str(e)}", False)


class UpdateDownloadWorker(QThread):
    """
    Downloads release ZIP or Setup EXE in background with granular progress tracking.
    Uses NoAuthRedirectHandler to safely follow AWS S3 redirects, and verifies
    binary integrity upon completion.
    """
    progress = Signal(int, int, float)  # (bytes_downloaded, total_bytes, percent)
    download_finished = Signal(str)     # (local_file_path)
    download_failed = Signal(str)       # (error_message)

    def __init__(self, release_info: dict, token: Optional[str] = None, use_installer: bool = False, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.release_info = release_info
        self.token = token or get_stored_github_token()
        self.use_installer = use_installer
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            # Determine download URL:
            if self.use_installer and self.release_info.get("installer_url"):
                download_url = self.release_info["installer_url"]
                filename = self.release_info.get("installer_name") or f"StickyNotes_Setup_v{self.release_info.get('version')}.exe"
                expected_size = self.release_info.get("installer_size", 0)
                req = urllib.request.Request(download_url)
            elif self.token and self.release_info.get("asset_api_url") and self.release_info.get("source") != "public_mirror":
                download_url = self.release_info["asset_api_url"]
                filename = self.release_info.get("asset_name") or f"StickyNotes_v{self.release_info.get('version')}.zip"
                expected_size = self.release_info.get("asset_size", 0)
                req = urllib.request.Request(download_url)
                req.add_header("Authorization", f"Bearer {self.token}")
                req.add_header("Accept", "application/octet-stream")
            else:
                download_url = self.release_info.get("browser_download_url") or self.release_info.get("installer_url")
                if not download_url:
                    self.download_failed.emit("No downloadable Windows asset found in release.")
                    return
                filename = self.release_info.get("asset_name") or f"StickyNotes_v{self.release_info.get('version')}.zip"
                expected_size = self.release_info.get("asset_size", 0)
                req = urllib.request.Request(download_url)

            req.add_header("User-Agent", "StickyNotesApp-AutoUpdater")

            # Destination temporary file
            temp_dir = Path(tempfile.gettempdir()) / "StickyNotes_Update"
            temp_dir.mkdir(parents=True, exist_ok=True)
            dest_file = temp_dir / filename

            # Build opener with NoAuthRedirectHandler to safely redirect to S3 storage
            opener = urllib.request.build_opener(NoAuthRedirectHandler())

            with opener.open(req, timeout=30) as response, open(dest_file, "wb") as out_file:
                total_bytes = int(response.headers.get("Content-Length") or expected_size)
                downloaded_bytes = 0
                chunk_size = 64 * 1024  # 64 KB chunks

                while True:
                    if self._is_cancelled:
                        self.download_failed.emit("Download cancelled by user.")
                        try:
                            dest_file.unlink(missing_ok=True)
                        except Exception:
                            pass
                        return

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    out_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    percent = (downloaded_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0
                    self.progress.emit(downloaded_bytes, total_bytes, percent)

            # Binary Integrity Verification
            if not dest_file.exists():
                self.download_failed.emit("Download failed: destination file not found.")
                return

            actual_size = dest_file.stat().st_size
            if actual_size < 102400:  # Minimum 100 KB for valid installer or zip package
                try:
                    dest_file.unlink(missing_ok=True)
                except Exception:
                    pass
                self.download_failed.emit("Downloaded file failed integrity check: file is incomplete or truncated.")
                return

            # Check binary signature
            try:
                with open(dest_file, "rb") as f:
                    magic = f.read(4)
                is_exe_file = dest_file.suffix.lower() == ".exe"
                is_zip_file = dest_file.suffix.lower() == ".zip"
                if is_exe_file and not magic.startswith(b"MZ"):
                    dest_file.unlink(missing_ok=True)
                    self.download_failed.emit("Downloaded update failed integrity check: invalid executable header.")
                    return
                if is_zip_file and not magic.startswith(b"PK"):
                    dest_file.unlink(missing_ok=True)
                    self.download_failed.emit("Downloaded update failed integrity check: invalid zip archive header.")
                    return
            except Exception as e:
                self.download_failed.emit(f"Integrity check failed: {str(e)}")
                return

            self.download_finished.emit(str(dest_file))

        except Exception as e:
            self.download_failed.emit(f"Failed to download update: {str(e)}")


def apply_update_and_restart(file_path_str: str) -> bool:
    """
    Applies the downloaded update package (.exe installer or .zip archive) and
    restarts Sticky Notes. In frozen production, replaces files or runs silent installer.
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        return False

    is_frozen = getattr(sys, 'frozen', False)
    current_pid = os.getpid()
    bat_path = file_path.parent / "apply_update.bat"

    # Case 1: Installer executable (.exe)
    if file_path.suffix.lower() == ".exe":
        installed_dir = Path(os.environ.get('LOCALAPPDATA', '')) / "Programs" / "StickyNotes"
        installed_exe = installed_dir / "StickyNotes.exe"
        app_dir = Path(sys.executable).resolve().parent if is_frozen else installed_dir
        target_exe = app_dir / "StickyNotes.exe"

        batch_script = f"""@echo off
setlocal enabledelayedexpansion
echo [Sticky Notes Updater] Closing application (PID {current_pid})...

:: 1. Force close the existing application process to ensure zero file locks
taskkill /f /pid {current_pid} >nul 2>&1
:WAIT_LOOP
tasklist /fi "pid eq {current_pid}" | find "{current_pid}" >nul
if not errorlevel 1 (
    ping 127.0.0.1 -n 2 >nul
    taskkill /f /pid {current_pid} >nul 2>&1
    goto WAIT_LOOP
)

:: 2. Run installer and WAIT for it to completely finish
echo [Sticky Notes Updater] Running installer...
start /wait "" "{file_path}" /SILENT /NORESTART /CLOSEAPPLICATIONS /DIR="{app_dir}"

:: 3. Launch the updated application (check app_dir first, then installed_exe)
echo [Sticky Notes Updater] Launching updated application...
ping 127.0.0.1 -n 2 >nul
if exist "{target_exe}" (
    start "" "{target_exe}"
) else if exist "{installed_exe}" (
    start "" "{installed_exe}"
)

:: 4. Clean up staging files
echo [Sticky Notes Updater] Cleaning up staging files...
ping 127.0.0.1 -n 2 >nul
del "{file_path}" >nul 2>&1
(goto) 2>nul & del "%~f0"
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(batch_script)

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

    # Case 2: Zip package (.zip)
    if not is_frozen:
        # Development mode cannot overwrite running Python files with ZIP
        return False

    temp_extract_dir = file_path.parent / "extracted"
    if temp_extract_dir.exists():
        import shutil
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
    temp_extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(temp_extract_dir)
    except Exception as e:
        print(f"[ERROR] Failed to extract update ZIP: {e}")
        return False

    payload_dir = temp_extract_dir
    candidates = list(temp_extract_dir.glob("**/StickyNotes.exe"))
    if candidates:
        payload_dir = candidates[0].parent

    app_target_dir = Path(sys.executable).resolve().parent
    exe_path = Path(sys.executable).resolve()

    batch_script = f"""@echo off
setlocal enabledelayedexpansion
echo [Sticky Notes Updater] Closing application (PID {current_pid})...

:: 1. Force close the existing application process
taskkill /f /pid {current_pid} >nul 2>&1
:WAIT_LOOP
tasklist /fi "pid eq {current_pid}" | find "{current_pid}" >nul
if not errorlevel 1 (
    ping 127.0.0.1 -n 2 >nul
    taskkill /f /pid {current_pid} >nul 2>&1
    goto WAIT_LOOP
)

:: 2. Apply update files via robocopy
echo [Sticky Notes Updater] Applying update files...
robocopy "{payload_dir}" "{app_target_dir}" /E /NP /R:3 /W:1 >nul

:: 3. Relaunch updated application
echo [Sticky Notes Updater] Relaunching application...
ping 127.0.0.1 -n 2 >nul
start "" "{exe_path}"

:: 4. Clean up staging files
echo [Sticky Notes Updater] Cleaning up staging files...
ping 127.0.0.1 -n 3 >nul
rd /s /q "{temp_extract_dir}" >nul 2>&1
del "{file_path}" >nul 2>&1
(goto) 2>nul & del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(batch_script)

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
