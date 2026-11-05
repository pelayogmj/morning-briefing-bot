#!/usr/bin/env python3
"""PostToolUse hook: run pytest automatically after editing a .py file.

Can't block the edit (it already happened by the time PostToolUse fires)
but surfaces a test failure back to Claude immediately, instead of
leaving it to be discovered later.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        sys.exit(0)

    if not VENV_PYTHON.exists():
        sys.exit(0)

    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        print(
            f"Tests failed after editing {file_path}:\n"
            f"{result.stdout}\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
