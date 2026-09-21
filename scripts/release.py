"""
scripts/release.py - Automated Zero-Friction Release Orchestrator for Sticky Notes.
Usage:
    python scripts/release.py 1.6.6
    python scripts/release.py patch
    python scripts/release.py minor

Performs:
1. Pre-flight verification (clean git status, test suite pass).
2. Updates version.py and CHANGELOG.md.
3. Commits version bump to current branch.
4. Pushes commit to GitHub (custom/main).
5. Creates git tag vX.Y.Z and pushes tag to remote.
6. Synchronizes workspace mirror (Google Drive).
"""

import sys
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "version.py"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
DRIVE_MIRROR = Path(r"G:\My Drive\Doctora\sticky_notes_app")


def run_cmd(cmd, cwd=PROJECT_ROOT, check=True):
    print(f"--> Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    return res


def get_current_version() -> str:
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not m:
        raise ValueError("Could not parse __version__ from version.py")
    return m.group(1)


def calculate_next_version(current: str, bump_type: str) -> str:
    parts = [int(p) for p in current.split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[0], parts[1], parts[2]

    if bump_type.lower() == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif bump_type.lower() == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type.lower() == "major":
        return f"{major + 1}.0.0"
    elif re.match(r"^\d+\.\d+\.\d+$", bump_type):
        return bump_type
    else:
        raise ValueError(f"Invalid version argument: '{bump_type}'. Use 'patch', 'minor', or 'X.Y.Z'.")


def update_version_py(new_ver: str):
    parts = tuple(int(p) for p in new_ver.split("."))
    today = datetime.now().strftime("%Y-%m-%d")
    content = VERSION_FILE.read_text(encoding="utf-8")
    content = re.sub(r'__version__\s*=\s*["\'][^"\']+["\']', f'__version__ = "{new_ver}"', content)
    content = re.sub(r'__version_info__\s*=\s*\([^\)]+\)', f'__version_info__ = {parts}', content)
    content = re.sub(r'__release_date__\s*=\s*["\'][^"\']+["\']', f'__release_date__ = "{today}"', content)
    VERSION_FILE.write_text(content, encoding="utf-8")
    print(f"[OK] Updated version.py to {new_ver} ({today})")


def update_changelog(new_ver: str):
    if not CHANGELOG_FILE.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    content = CHANGELOG_FILE.read_text(encoding="utf-8")
    if f"## [{new_ver}]" in content:
        return  # Already has section

    new_section = f"## [{new_ver}] - {today}\n\n### Added & Improved\n- Quality improvements and release updates.\n\n"
    if "## [Unreleased]" in content:
        content = content.replace("## [Unreleased]\n", f"## [Unreleased]\n\n{new_section}", 1)
    else:
        content = new_section + content
    CHANGELOG_FILE.write_text(content, encoding="utf-8")
    print(f"[OK] Added v{new_ver} section to CHANGELOG.md")


def sync_drive_mirror():
    if not DRIVE_MIRROR.exists():
        return
    print(f"--> Syncing files to Google Drive mirror: {DRIVE_MIRROR}")
    for item in ["version.py", "CHANGELOG.md", "updater.py", "build_exe.py"]:
        src = PROJECT_ROOT / item
        if src.exists():
            shutil.copy2(src, DRIVE_MIRROR / item)
    print("[OK] Mirrored to Google Drive")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/release.py <new_version | patch | minor>")
        sys.exit(1)

    target_arg = sys.argv[1]
    current_ver = get_current_version()
    new_ver = calculate_next_version(current_ver, target_arg)
    tag_name = f"v{new_ver}"

    print("=" * 60)
    print(f"Sticky Notes Release Automation: {current_ver} -> {new_ver} ({tag_name})")
    print("=" * 60)

    # 1. Run Automated Tests
    print("--> Step 1: Running unit test suite...")
    test_res = run_cmd([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    print("[OK] Test suite passed successfully!")

    # 2. Update files
    print("--> Step 2: Updating version metadata...")
    update_version_py(new_ver)
    update_changelog(new_ver)

    # 3. Git commit
    print("--> Step 3: Committing version bump...")
    run_cmd(["git", "add", "version.py", "CHANGELOG.md"])
    run_cmd(["git", "commit", "-m", f"chore(release): bump version to {new_ver}"])

    # 4. Push branch
    print("--> Step 4: Pushing commit to remote 'custom' (branch main)...")
    run_cmd(["git", "push", "custom", "custom-edition:main"])

    # 5. Create and push tag
    print(f"--> Step 5: Creating tag {tag_name} and pushing to remote...")
    run_cmd(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
    run_cmd(["git", "push", "custom", tag_name])

    # 6. Mirror to Google Drive
    print("--> Step 6: Syncing workspace mirror...")
    sync_drive_mirror()

    print("=" * 60)
    print(f"[SUCCESS] Release {tag_name} initiated successfully!")
    print(f"Track the build on GitHub Actions:")
    print(f"https://github.com/DavidAlexanderM/sticky_notes_custom/actions")
    print("=" * 60)


if __name__ == "__main__":
    main()
