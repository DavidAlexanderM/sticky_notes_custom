"""
generate_release_manifest.py - Generates version.json for Public Mirror Feed.
Extracts version info, locates compiled distribution zip, and formats JSON feed.
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from version import __version__

def generate_manifest(output_dir: Path = None, tag_name: str = None) -> Path:
    if output_dir is None:
        output_dir = PROJECT_ROOT / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    tag = tag_name or os.environ.get("GITHUB_REF_NAME") or f"v{__version__}"
    clean_ver = tag.lstrip("vV")

    dist_dir = PROJECT_ROOT / "dist"
    matching_zips = [f for f in dist_dir.glob("*.zip") if clean_ver in f.name]
    target_zip = matching_zips[0] if matching_zips else None
    asset_name = target_zip.name if target_zip else f"StickyNotes_v{clean_ver}_Windows.zip"
    asset_size = target_zip.stat().st_size if target_zip else 0

    # Look for installer exe
    matching_exes = [f for f in dist_dir.glob("*.exe") if "setup" in f.name.lower()]
    target_exe = matching_exes[0] if matching_exes else None
    installer_name = target_exe.name if target_exe else f"StickyNotes_Setup_v{clean_ver}.exe"
    installer_size = target_exe.stat().st_size if target_exe else 0

    manifest = {
        "version": clean_ver,
        "tag_name": tag,
        "published_at": f"{os.environ.get('GITHUB_SHA', 'latest')}",
        "html_url": f"https://github.com/DavidAlexanderM/sticky_notes_releases/releases/tag/{tag}",
        "body": f"Sticky Notes {tag} release for Windows.",
        "asset_name": asset_name,
        "asset_size": asset_size,
        "browser_download_url": f"https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/{tag}/{asset_name}",
        "installer_name": installer_name,
        "installer_size": installer_size,
        "installer_url": f"https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/{tag}/{installer_name}"
    }

    out_file = output_dir / "version.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Also update root version.json if running for default dist directory
    if output_dir == PROJECT_ROOT / "dist":
        root_manifest = PROJECT_ROOT / "version.json"
        with open(root_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    print(f"[OK] Generated mirror manifest: {out_file} (v{clean_ver})")
    return out_file

if __name__ == "__main__":
    generate_manifest()
