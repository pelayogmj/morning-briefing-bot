# Workflow: Morning Briefing (combined)

## Objective
Print the full daily briefing: weather, today's calendar events, and top unread emails, in one command.

## Required inputs
Union of the three individual workflows' inputs:
- `.env`: `LOCATION_NAME`, `LAT`, `LON` (weather), optional `CALENDAR_ID`, optional `EMAIL_COUNT`.
- `credentials.json` / `token.json` at the project root (Calendar + Gmail OAuth).

See `workflows/morning_weather_briefing.md`, `workflows/calendar_briefing.md`, and `workflows/gmail_briefing.md` for each section's details.

## Tool to use
`tools/morning_briefing.py` via the project's venv:

```
.venv/Scripts/python.exe tools/morning_briefing.py
```

## Expected output
Three stacked sections, separated by blank lines: the weather paragraph, the events block, the inbox block.

## Edge cases
**Deliberate design choice**: if any one section fails (missing config, auth failure, network error), the whole briefing aborts with that section's error message — it does not print a partial briefing with one section silently missing. This matches Stage 1's "fail loudly, never fabricate" convention. To debug which section is broken, run that section's own tool directly (`tools/get_weather.py`, `tools/get_calendar.py`, or `tools/get_gmail.py`) — each stays independently runnable.
