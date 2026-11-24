# Contributing

## Setup

Follow [SETUP.md](SETUP.md) to get a working local environment, or at
minimum:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running tests

```powershell
.venv\Scripts\python.exe -m pytest
```

Tests live in `tests/`, one file per tool in `tools/`. They cover
pure logic (parsing, formatting) without live API calls. If you add
or change a tool, add or update its test file.

## Hooks

If you're working inside Claude Code on this repo, `.claude/settings.json`
wires a few hooks that enforce rules a prompt alone can't guarantee:

- Blocks reading `.env`, `credentials.json`, or `token.json`.
- Blocks destructive shell commands (`rm -rf`, force push, `git reset
  --hard`, `git clean -f`).
- Blocks `git commit` until a security review has been recorded for
  the currently staged diff (see `tools/mark_security_reviewed.py`
  and CLAUDE.md's "Hooks enforce; prompts only ask" section). Any
  further staging change invalidates that review.
- Runs `pytest` automatically after editing a `.py` file and reports
  failures right away.

These run whether or not you're aware of them; you don't need to
invoke anything to benefit from them.

## Pull requests

- Keep PRs focused on one change.
- Add or update tests for any logic change.
- Make sure `pytest` passes before opening the PR.
- Never commit `.env`, `credentials.json`, `token.json`, or
  `.mcp.json` (all gitignored already) or paste real secret values
  into an issue or PR description.
- Describe what changed and why in the PR description; keep the
  commit history readable.
