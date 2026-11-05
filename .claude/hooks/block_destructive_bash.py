#!/usr/bin/env python3
"""PreToolUse hook: block a short list of destructive Bash commands.

Encodes, as an enforced backstop, the same patterns Claude is already
asked to avoid on its own (see the Git Safety Protocol in its system
instructions) -- a hook guarantees it, a prompt only asks nicely.
"""
import json
import re
import sys

DESTRUCTIVE_PATTERNS = [
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bgit\s+push\b.*(--force\b|-f\b)"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\b.*-f"),
    re.compile(r"\bgit\s+branch\s+-D\b"),
]


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            print(
                "Blocked: command matches a disallowed destructive pattern "
                f"({pattern.pattern}) in .claude/hooks/block_destructive_bash.py. "
                "If this is genuinely needed, ask the user to run it "
                "themselves.",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
