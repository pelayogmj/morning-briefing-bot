# Workflow: Calendar Briefing

## Objective
List today's Google Calendar events via direct API access (not MCP — see `CLAUDE.md` for why).

## Required inputs
- `credentials.json` at the project root (Google Cloud OAuth client, type "Desktop app").
- `token.json` at the project root — created automatically on first run via a one-time interactive browser consent; refreshed automatically afterward.
- Optional `CALENDAR_ID` in `.env` (defaults to `"primary"`, the signed-in user's main calendar).

## Tool to use
`tools/get_calendar.py` via the project's venv:

```
.venv/Scripts/python.exe tools/get_calendar.py
```

## Expected output
A bulleted list of today's events (all-day events marked separately from timed ones), or `No events today.` when the calendar is empty.

## Edge cases
- **Missing `credentials.json`**: clear error to stderr, exit non-zero, with instructions to download it from Google Cloud Console (see `CLAUDE.md`).
- **Expired/revoked token**: the script attempts a silent refresh; if that fails, `token.json` should be deleted so the next run re-triggers the interactive consent flow.
- **No events today**: prints `No events today.` rather than an empty block.
- **Network/API failure**: clear error to stderr, exit non-zero — no stale or fabricated data.
