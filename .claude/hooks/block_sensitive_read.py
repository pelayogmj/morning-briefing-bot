#!/usr/bin/env python3
"""PreToolUse hook: block Claude from reading .env/credentials.json/token.json.

Extends the curriculum's literal ".env" example to all three gitignored
secret files already named in CLAUDE.md's "never commit secrets" rule.
"""
import json
import sys
from pathlib import Path

SENSITIVE_NAMES = {".env", "credentials.json", "token.json"}


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    if Path(file_path).name in SENSITIVE_NAMES:
        print(
            f"Blocked: reading {Path(file_path).name} directly is disallowed "
            "by project policy (.claude/hooks/block_sensitive_read.py). "
            "These files hold secrets and must never be read, printed, or "
            "quoted.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
