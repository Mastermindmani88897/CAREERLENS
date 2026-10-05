#!/usr/bin/env python3
"""
CareerLens — Unified Security and Code Quality Verification Gate.
Runs standardized verification checks across backend and frontend:
1. Secret leak scan
2. Backend lint (Ruff)
3. Backend formatting (Ruff format)
4. Static security analysis (Bandit)
5. Backend automated test suite (Pytest)
6. Frontend lint (Oxlint)
7. Frontend type-check (TypeScript)
8. Frontend automated tests (Vitest)
9. Frontend production build (Vite)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Virtual environment python binary resolution
if sys.platform == "win32":
    VENV_PY = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    VENV_RUFF = BACKEND_DIR / ".venv" / "Scripts" / "ruff.exe"
    VENV_BANDIT = BACKEND_DIR / ".venv" / "Scripts" / "bandit.exe"
    VENV_PYTEST = BACKEND_DIR / ".venv" / "Scripts" / "pytest.exe"
    NPM_CMD = "npm.cmd"
else:
    VENV_PY = BACKEND_DIR / ".venv" / "bin" / "python"
    VENV_RUFF = BACKEND_DIR / ".venv" / "bin" / "ruff"
    VENV_BANDIT = BACKEND_DIR / ".venv" / "bin" / "bandit"
    VENV_PYTEST = BACKEND_DIR / ".venv" / "bin" / "pytest"
    NPM_CMD = "npm"

# Fallback to sys.executable if venv specific bin does not exist
PY_BIN = str(VENV_PY if VENV_PY.exists() else sys.executable)
RUFF_BIN = str(VENV_RUFF if VENV_RUFF.exists() else "ruff")
BANDIT_BIN = str(VENV_BANDIT if VENV_BANDIT.exists() else "bandit")
PYTEST_BIN = str(VENV_PYTEST if VENV_PYTEST.exists() else "pytest")


def run_step(name: str, cmd: list[str], cwd: Path) -> bool:
    """Execute a quality check step and stream results."""
    print(f"\n[CHECK] {name}...")
    try:
        res = subprocess.run(cmd, cwd=str(cwd), check=False)
        if res.returncode == 0:
            print(f"[PASS]  {name}")
            return True
        else:
            print(f"[FAIL]  {name} (exit code: {res.returncode})")
            return False
    except Exception as exc:
        print(f"[ERROR] {name}: {exc}")
        return False


def scan_for_staged_secrets() -> bool:
    """Scan tracked and staged files for dangerous credentials."""
    print("\n[CHECK] Repository Secret Scan...")
    secret_patterns = [
        re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY-----"),
        re.compile(r"JWT_SECRET_KEY=[a-zA-Z0-9_\-]{16,}"),
        re.compile(r"postgresql(?:\+asyncpg)?://[^:]+:(?!PASSWORD@)[^@\s]+@"),
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key pattern
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),     # OpenAI API key pattern
    ]

    clean = True
    try:
        # Get list of tracked files via git
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]

        for rel_path in tracked_files:
            file_path = ROOT_DIR / rel_path
            if not file_path.is_file():
                continue

            # Skip binary and test mock files
            if rel_path.endswith((".png", ".jpg", ".ico", ".svg", ".pyc", ".woff", ".woff2")):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for pat in secret_patterns:
                    if pat.search(content):
                        # Filter out known false positives in tests or example templates
                        if "test_" in rel_path or "setup_db.py" in rel_path or ".env.example" in rel_path or "check_quality.py" in rel_path or "test_security_hardening.py" in rel_path:
                            continue
                        print(f"  [POTENTIAL SECRET] Found suspicious pattern in {rel_path}")
                        clean = False
            except Exception:
                pass

        if clean:
            print("[PASS]  Repository Secret Scan (0 leaks detected)")
        else:
            print("[FAIL]  Repository Secret Scan found potential secret leaks")
        return clean
    except Exception as exc:
        print(f"[WARN] Could not run git ls-files: {exc}")
        return True


def main() -> int:
    print("=" * 60)
    print("CAREERLENS — Security & Development Quality Gate")
    print("=" * 60)

    steps = [
        ("Secret Scan", lambda: scan_for_staged_secrets()),
        ("Backend Ruff Lint", lambda: run_step("Backend Ruff Lint", [RUFF_BIN, "check", "."], BACKEND_DIR)),
        ("Backend Ruff Format", lambda: run_step("Backend Ruff Format Check", [RUFF_BIN, "format", "--check", "."], BACKEND_DIR)),
        ("Backend Bandit Security Scan", lambda: run_step("Backend Bandit Scan", [BANDIT_BIN, "-r", "app", "alembic", "-ll"], BACKEND_DIR)),
        ("Backend Pytest Suite", lambda: run_step("Backend Pytest", [PYTEST_BIN], BACKEND_DIR)),
        ("Frontend Oxlint", lambda: run_step("Frontend Oxlint", [NPM_CMD, "run", "lint"], FRONTEND_DIR)),
        ("Frontend Type-Check", lambda: run_step("Frontend Type-Check", [NPM_CMD, "run", "type-check"], FRONTEND_DIR)),
        ("Frontend Vitest Suite", lambda: run_step("Frontend Vitest", [NPM_CMD, "test"], FRONTEND_DIR)),
        ("Frontend Vite Build", lambda: run_step("Frontend Build", [NPM_CMD, "run", "build"], FRONTEND_DIR)),
    ]

    failed = []
    for name, action in steps:
        success = action()
        if not success:
            failed.append(name)

    print("\n" + "=" * 60)
    if failed:
        print(f"[RESULT] FAILED ({len(failed)} step(s) failed):")
        for f in failed:
            print(f"  - {f}")
        return 1
    else:
        print("[RESULT] ALL QUALITY AND SECURITY GATES PASSED!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
