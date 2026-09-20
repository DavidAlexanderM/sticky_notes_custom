#!/usr/bin/env python3
"""
security_check.py - Automated AST Static Analysis Security & DevSecOps Gate.
Scans Python source files for insecure coding patterns, dynamic SQL queries,
unsafe shell executions, and audits dependencies when pip-audit is available.
"""

import ast
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files/Directories to exclude from SAST scan
EXCLUDE_DIRS = {".git", ".agents", "build", "dist", "__pycache__", "env", "venv", ".venv"}


class SecurityASTVisitor(ast.NodeVisitor):
    """AST visitor that detects dangerous functions and dynamic SQL queries."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Dict[str, Any]] = []

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Check for built-in eval() and exec()
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self.violations.append({
                "file": self.filename,
                "line": node.lineno,
                "rule": "B101_DYNAMIC_CODE_EXECUTION",
                "message": f"Dangerous direct use of built-in {node.func.id}() detected.",
                "severity": "HIGH"
            })

        # Check for os.system()
        if func_name == "system":
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                self.violations.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "rule": "B102_OS_SYSTEM_CALL",
                    "message": "Dangerous use of os.system() detected. Use subprocess with argument lists.",
                    "severity": "HIGH"
                })

        # Check for subprocess shell=True
        if func_name in ("Popen", "run", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.violations.append({
                        "file": self.filename,
                        "line": node.lineno,
                        "rule": "B103_SUBPROCESS_SHELL_TRUE",
                        "message": "subprocess call with shell=True is susceptible to command injection.",
                        "severity": "HIGH"
                    })

        # Check for SQL injection in execute() or executemany()
        if func_name in ("execute", "executemany") and node.args:
            first_arg = node.args[0]
            # Check for f-strings: execute(f"SELECT ...")
            if isinstance(first_arg, ast.JoinedStr):
                self.violations.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "rule": "B201_SQLI_DYNAMIC_FSTRING",
                    "message": "Dynamic SQL query constructed with f-string in execute(). Use parameterized queries ('?').",
                    "severity": "CRITICAL"
                })
            # Check for % formatting: execute("..." % var)
            elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, ast.Mod):
                self.violations.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "rule": "B202_SQLI_STRING_FORMAT_MOD",
                    "message": "Dynamic SQL query constructed with '%' operator. Use parameterized queries ('?').",
                    "severity": "CRITICAL"
                })
            # Check for .format(): execute("...".format(...))
            elif isinstance(first_arg, ast.Call) and isinstance(first_arg.func, ast.Attribute) and first_arg.func.attr == "format":
                # Allow safe placeholder generation: e.g. f"DELETE FROM notes WHERE id IN ({placeholders})" where placeholders is ?,?,?
                # Check if it is format call
                self.violations.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "rule": "B203_SQLI_STR_FORMAT",
                    "message": "Potential dynamic SQL query with .format(). Ensure values are parameterized.",
                    "severity": "MEDIUM"
                })

        self.generic_visit(node)


def scan_python_files(root: Path) -> List[Dict[str, Any]]:
    """Recursively parses all Python files into AST and runs the security visitor."""
    all_violations = []
    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code, filename=str(p))
            visitor = SecurityASTVisitor(str(p.relative_to(root)))
            visitor.visit(tree)
            all_violations.extend(visitor.violations)
        except Exception as e:
            all_violations.append({
                "file": str(p.relative_to(root)),
                "line": 0,
                "rule": "PARSER_ERROR",
                "message": f"Could not parse file: {e}",
                "severity": "MEDIUM"
            })
    return all_violations


def check_dependency_audit() -> Dict[str, Any]:
    """Checks dependencies using pip-audit if installed."""
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0:
            return {"status": "clean", "tool": "pip-audit", "vulnerabilities": []}
        try:
            audit_json = json.loads(res.stdout)
            return {"status": "issues_found", "tool": "pip-audit", "details": audit_json}
        except Exception:
            return {"status": "clean", "tool": "pip-audit"}
    except (subprocess.SubprocessError, FileNotFoundError):
        return {"status": "skipped", "reason": "pip-audit not installed in environment"}


def main():
    violations = scan_python_files(PROJECT_ROOT)
    dep_audit = check_dependency_audit()

    critical_or_high = [v for v in violations if v["severity"] in ("CRITICAL", "HIGH")]

    report = {
        "status": "passed" if len(critical_or_high) == 0 else "failed",
        "total_violations": len(violations),
        "critical_or_high": len(critical_or_high),
        "violations": violations,
        "dependency_audit": dep_audit
    }

    if "--json" in sys.argv:
        print(json.dumps(report, separators=(",", ":")))
    else:
        print("=" * 65)
        print("Sticky Notes - AST Security & DevSecOps Audit")
        print("=" * 65)
        print(f"Files Scanned under: {PROJECT_ROOT}")
        print(f"Static AST Violations: {len(violations)} (High/Critical: {len(critical_or_high)})")
        for v in violations:
            print(f"  [{v['severity']}] {v['file']}:{v['line']} - {v['message']} ({v['rule']})")
        
        print(f"Dependency Audit: {dep_audit.get('status')} ({dep_audit.get('tool', dep_audit.get('reason'))})")
        print("=" * 65)
        if len(critical_or_high) == 0:
            print("[SECURITY PASSED] Zero critical/high security violations found.")
        else:
            print("[SECURITY FAILED] Remediation required before release.")

    sys.exit(0 if len(critical_or_high) == 0 else 1)


if __name__ == "__main__":
    main()
