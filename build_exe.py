import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

def build():
    project_dir = Path(__file__).resolve().parent
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"
    app_name = "StickyNotes"

    print("=" * 60)
    print("Building standalone Windows executable with PyInstaller...")
    print("=" * 60)

    # Clean old build artifacts if any
    for d in [dist_dir, build_dir]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    # Ensure app icon is generated
    icon_path = project_dir / "assets" / "icon.ico"
    if not icon_path.exists():
        try:
            from scripts.generate_app_icon import create_sticky_icon
            create_sticky_icon()
        except Exception:
            pass

    # PyInstaller command arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", app_name,
        "--noconsole",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--add-data", f"{project_dir / 'styles.py'};.",
    ]
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])

    cmd.append(str(project_dir / "main.py"))

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(project_dir))

    if result.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        sys.exit(result.returncode)

    from version import __version__, APP_NAME

    app_folder = dist_dir / app_name
    print(f"[SUCCESS] Standalone app built at: {app_folder}")

    # Create a ready-to-distribute portable ZIP file (privacy invariant: generic package naming)
    zip_path = dist_dir / f"StickyNotes_v{__version__}_Windows.zip"
    print(f"Creating portable ZIP: {zip_path.name} ...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(app_folder):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(dist_dir)
                zipf.write(full_path, rel_path)

    print("=" * 60)
    print("[SUCCESS] Gift Package Ready!")
    print(f"Location: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / (1024 * 1024):.1f} MB")
    print("The recipient can unzip and run StickyNotes.exe without Python!")
    print("=" * 60)

if __name__ == "__main__":
    build()
