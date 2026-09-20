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
    zip_files = list(dist_dir.glob("*.zip"))
    asset_name = zip_files[0].name if zip_files else f"StickyNotes_v{clean_ver}_Windows.zip"
    asset_size = zip_files[0].stat().st_size if zip_files else 0

    manifest = {
        "version": clean_ver,
        "tag_name": tag,
        "published_at": f"{os.environ.get('GITHUB_SHA', 'latest')}",
        "html_url": f"https://github.com/DavidAlexanderM/sticky_notes_releases/releases/tag/{tag}",
        "body": f"Sticky Notes {tag} release for Windows.",
        "asset_name": asset_name,
        "asset_size": asset_size,
        "browser_download_url": f"https://github.com/DavidAlexanderM/sticky_notes_releases/releases/download/{tag}/{asset_name}"
    }

    out_file = output_dir / "version.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Also update root version.json if running in project root
    root_manifest = PROJECT_ROOT / "version.json"
    with open(root_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[OK] Generated mirror manifest: {out_file} (v{clean_ver})")
    return out_file

if __name__ == "__main__":
    generate_manifest()
