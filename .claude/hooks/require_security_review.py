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

# The repo is resolved from the `cwd` field of the hook's input payload
# (the folder the Bash command actually runs in), via `git rev-parse
# --show-toplevel`. Neither this file's own path nor the hook process's
# working directory is reliable in a git worktree: both can point at the
# main checkout, which silently made this hook check the wrong repo's
# (empty) staged diff and block every commit made from a worktree.
COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b")


def repo_root(cwd=None):
    if cwd and not Path(cwd).is_dir():
        cwd = None
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd or None,
        capture_output=True,
        check=True,
        text=True,
    )
    return Path(result.stdout.strip())


def staged_diff_hash(project_root):
    # Raw bytes (no text=True) -- diffs can contain arbitrary UTF-8
    # content (e.g. emoji in a .md file) that Windows' default console
    # codepage can't decode; hashing bytes directly avoids that entirely.
    result = subprocess.run(
        ["git", "diff", "--cached"],
        cwd=project_root,
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command or not COMMIT_PATTERN.search(command):
        sys.exit(0)

    try:
        project_root = repo_root(payload.get("cwd"))
        current_hash = staged_diff_hash(project_root)
    except subprocess.CalledProcessError:
        sys.exit(0)

    marker_path = project_root / ".claude" / ".security-review-passed"
    stored_hash = marker_path.read_text().strip() if marker_path.exists() else None

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
