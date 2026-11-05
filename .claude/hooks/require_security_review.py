#!/usr/bin/env python3
"""PreToolUse hook: gate `git commit` on a prior security review.

Hooks have no built-in session memory, so "a review already happened" is
tracked via a project-specific convention (not an official Claude Code
feature): a marker file (.claude/.security-review-passed) storing a hash
of the staged diff at the time tools/mark_security_reviewed.py was last
run. If the current staged diff doesn't match that hash, the commit is
blocked until a fresh review is recorded.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MARKER_PATH = PROJECT_ROOT / ".claude" / ".security-review-passed"
COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b")


def staged_diff_hash():
    result = subprocess.run(
        ["git", "diff", "--cached"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return hashlib.sha256(result.stdout.encode("utf-8")).hexdigest()


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command or not COMMIT_PATTERN.search(command):
        sys.exit(0)

    try:
        current_hash = staged_diff_hash()
    except subprocess.CalledProcessError:
        sys.exit(0)

    stored_hash = MARKER_PATH.read_text().strip() if MARKER_PATH.exists() else None

    if stored_hash != current_hash:
        print(
            "Blocked: no up-to-date security review on record for the "
            "currently staged changes (.claude/hooks/require_security_review.py). "
            "Run the 'security-review' skill, confirm it's clean, then run "
            "`.venv/Scripts/python.exe tools/mark_security_reviewed.py` "
            "before retrying the commit.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
