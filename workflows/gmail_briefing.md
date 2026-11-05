# Workflow: Gmail Briefing

## Objective
List the top unread emails (subject + sender only — no body) via direct Gmail API access (not MCP — see `CLAUDE.md`).

## Required inputs
- `credentials.json` and `token.json` at the project root (same OAuth setup as the calendar briefing; see `workflows/calendar_briefing.md`). Scope used: `gmail.readonly` (read-only, no send/modify — deliberately narrow).
- Optional `EMAIL_COUNT` in `.env` (defaults to 5).

## Tool to use
`tools/get_gmail.py` via the project's venv:

```
.venv/Scripts/python.exe tools/get_gmail.py
```

## Expected output
A numbered list of up to `EMAIL_COUNT` unread messages as `subject — sender`, or `No unread messages.` when the inbox has none.

## Edge cases
- **Missing `credentials.json`**: clear error to stderr, exit non-zero.
- **Fewer unread than `EMAIL_COUNT`**: just lists what's there.
- **`From` header has no display name** (bare address like `noreply@example.com`): the address itself is shown as the sender.
- **Network/API failure**: clear error to stderr, exit non-zero.
