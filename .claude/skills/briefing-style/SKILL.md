---
name: briefing-style
description: Tone, length, and prioritization rules for rendering the daily morning briefing. Use when composing the final briefing text for the user from raw weather/calendar/email data.
user-invocable: false
---

# Briefing Style

Rules for turning the raw output of `tools/morning_briefing.py` into the
final text shown to the user. This is presentation guidance only — never
re-fetch or re-derive the underlying data; just rephrase what the tools
already reported.

## Tone

Direct and concise, but human — never echo raw data back mechanically.
Rephrase facts the way a person would say them out loud.

- Say "today will be sunny," not "there are no clouds expected today."
- Say "nothing on your calendar today," not "No events today."
- Say "inbox is empty," not "No unread messages."
- Avoid restating a number right after already saying it in words (e.g.
  don't say "high 18°C / low 9°C" immediately after already describing
  the weather — pick one way to say it).

## Format

Always exactly three lines, in this fixed order — never reorder based on
urgency, and never merge them into one flowing paragraph:

1. Greeting + weather, one sentence: "Good morning! Today in
   {location} {weather description}, {temps}, {rain chance}."
2. Calendar info — one line (or "Nothing on your calendar today" if
   empty).
3. Email info — one line (or "Inbox is empty" if empty).

Keep this same shape every time so the briefing is consistently
scannable. No padding, no preamble like "Here is your briefing:" —
just the three lines. Don't over-elaborate low-signal sections — one
unread email or one quiet afternoon still gets just one line.

## What to leave out

- Raw JSON, file paths (e.g. the `.tmp/` snapshot path), or internal tool
  names — none of that is useful to someone reading this over coffee.
- Any section whose underlying script actually failed should be reported
  plainly as a failure, not silently dropped or guessed at.
