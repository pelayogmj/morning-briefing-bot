"""Record that the currently staged diff has passed a security review.

Run this after the 'security-review' skill has been run and judged clean,
right before `git commit`. Writes a hash of `git diff --cached` to
.claude/.security-review-passed, which the require_security_review.py
PreToolUse hook checks before allowing a commit to proceed.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKER_PATH = PROJECT_ROOT / ".claude" / ".security-review-passed"


def main():
    # Capture raw bytes (no text=True) -- diffs can contain arbitrary
    # UTF-8 content (e.g. emoji in a .md file), which Windows' default
    # console codepage can't decode. Hashing bytes directly sidesteps
    # any decode/re-encode ambiguity entirely.
    result = subprocess.run(
        ["git", "diff", "--cached"],
        cwd=PROJECT_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        print(
            f"Error: git diff --cached failed: {result.stderr.decode('utf-8', 'replace')}",
            file=sys.stderr,
        )
        sys.exit(1)

    staged_diff = result.stdout
    if not staged_diff.strip():
        print(
            "Error: no staged changes found (git diff --cached is empty).",
            file=sys.stderr,
        )
        sys.exit(1)

    digest = hashlib.sha256(staged_diff).hexdigest()
    MARKER_PATH.write_text(digest)
    print(f"Recorded security review for current staged changes ({digest[:12]}...).")


if __name__ == "__main__":
    main()
