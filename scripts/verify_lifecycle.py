"""
Automated Quality Assurance & Lifecycle Verification Script
Verifies:
1. Documentation-as-Code completeness.
2. Version synchronization across version.py and CHANGELOG.md.
3. Automated test suite execution (CRUD, multi-language, audio device detection).
4. Automated Security & DevSecOps gates (Path traversal, SQLi, safe URLs, AST static audit).
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_documentation():
    print("[1/4] Checking documentation completeness...")
    required_docs = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CHANGELOG.md",
        PROJECT_ROOT / "docs" / "ARCHITECTURE.md",
        PROJECT_ROOT / "docs" / "ROADMAP.md",
        PROJECT_ROOT / "docs" / "DEVELOPMENT_LIFECYCLE.md",
    ]
    for doc in required_docs:
        if not doc.exists():
            raise FileNotFoundError(f"Missing mandatory documentation: {doc.relative_to(PROJECT_ROOT)}")
        size = doc.stat().st_size
        if size < 200:
            raise ValueError(f"Documentation file appears incomplete ({size} bytes): {doc.relative_to(PROJECT_ROOT)}")
        print(f"  [OK] {doc.relative_to(PROJECT_ROOT)} ({size} bytes)")
    print("  -> Documentation completeness verified.\n")


def check_version_sync():
    print("[2/4] Checking version synchronization...")
    sys.path.insert(0, str(PROJECT_ROOT))
    import version

    app_version = version.__version__
    print(f"  Current App Version: {app_version}")

    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    changelog_content = changelog_path.read_text(encoding="utf-8")

    expected_entry = f"## [{app_version}]"
    if expected_entry not in changelog_content:
        raise ValueError(f"CHANGELOG.md does not contain an entry for current version: '{expected_entry}'")
    
    print(f"  [OK] Found release entry in CHANGELOG.md for v{app_version}")
    print("  -> Version synchronization verified.\n")


def run_automated_tests():
    print("[3/4] Running automated test suites...")
    test_files = [
        PROJECT_ROOT / "test_app.py",
        PROJECT_ROOT / "tests" / "test_compatibility_and_media.py",
        PROJECT_ROOT / "tests" / "test_theme_manager.py",
        PROJECT_ROOT / "tests" / "test_gui_features.py",
        PROJECT_ROOT / "tests" / "test_screen_recorder.py",
        PROJECT_ROOT / "tests" / "test_projects.py",
        PROJECT_ROOT / "tests" / "test_updater.py"
    ]

    for test_file in test_files:
        print(f"  Executing {test_file.relative_to(PROJECT_ROOT)} ...")
        proc = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        if proc.returncode != 0:
            print(f"[TEST FAILURE in {test_file.name}]")
            print("STDOUT:", proc.stdout)
            print("STDERR:", proc.stderr)
            raise RuntimeError(f"Test suite failed: {test_file.name} (exit code {proc.returncode})")
        print(f"  [PASS] {test_file.name}")

    print("  -> All functional test suites passed with 0 errors.\n")


def run_security_gates():
    print("[4/4] Running automated security & DevSecOps gates...")
    
    # 1. Automated Security Unit Tests
    print("  Executing tests/test_security.py ...")
    proc_sec = subprocess.run(
        [sys.executable, "-m", "unittest", "tests/test_security.py"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    if proc_sec.returncode != 0:
        print("[SECURITY TEST FAILURE]")
        print("STDOUT:", proc_sec.stdout)
        print("STDERR:", proc_sec.stderr)
        raise RuntimeError("Security unit test suite failed.")
    print("  [PASS] tests/test_security.py (Path traversal, SQLi, Safe URLs, HTML sanitization)")

    # 2. AST Static Analysis Security Scanner
    print("  Executing scripts/security_check.py (AST SAST scanner) ...")
    proc_ast = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "security_check.py"), "--json"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    if proc_ast.returncode != 0:
        print("[AST SECURITY FAILURE]")
        print(proc_ast.stdout)
        print(proc_ast.stderr)
        raise RuntimeError("AST static security check detected high/critical violations.")
    print("  [PASS] scripts/security_check.py (0 AST vulnerabilities, clean dependency audit)")

    print("  -> All security & DevSecOps gates passed with 0 violations.\n")


def main():
    print("=" * 65)
    print("Sticky Notes - Pre-Release Lifecycle & Verification Gate")
    print("=" * 65)
    try:
        check_documentation()
        check_version_sync()
        run_automated_tests()
        run_security_gates()
        print("=" * 65)
        print("[LIFECYCLE PASSED] Codebase satisfies all Definition of Done criteria!")
        print("=" * 65)
    except Exception as e:
        print("=" * 65)
        print(f"[LIFECYCLE FAILED] {e}")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()
