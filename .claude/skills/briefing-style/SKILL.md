---
name: briefing-style
description: Tone, length, and prioritization rules for rendering the daily morning briefing. Use when composing the final briefing text for the user from raw weather/calendar/email data.
user-invocable: false
---

# Briefing Style

Rules for turning the raw output of `tools/get_weather.py`,
`tools/get_calendar.py`, and `tools/get_gmail.py` into the final text
shown to the user — used by both the interactive `/briefing` command and
the automated `tools/send_morning_briefing.py` pipeline. This is
presentation guidance only — never re-fetch or re-derive the underlying
data; just rephrase what the tools already reported.

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

Always exactly three blocks, in this fixed order, **separated by a
blank line** — never reorder based on urgency, and never merge them
into one flowing paragraph. This is plain text (no Markdown/HTML bold
or asterisks — it won't render as formatting and may break delivery)
— use an emoji at the start of each block instead to make it scannable
at a glance:

1. **🌤️ Weather** (pick the emoji to match conditions — e.g. ☀️ clear,
   ⛅/☁️ cloudy/overcast, 🌧️ rain, ❄️ snow, 🌫️ fog, ⛈️ thunderstorms):
   "Good morning! Today in {location} {weather description}, {temps},
   {rain chance}."
2. **📅 Calendar** — combine *every* event from today into one flowing
   sentence (not bullets), each with its time and title, e.g.: "Today's
   events are: lunch with Alex at 12:30, a team meeting at 15:00, and
   dinner with Megan at 21:00." If there are no events: "Nothing on your
   calendar today."
3. **💬 Inbox** — for each unread email, write a short summary of what
   it's actually *about*, using its snippet (the short content preview
   each email tool run provides) — not a reworded subject line. E.g.
   given subject "Fwd: You've been invited..." and a snippet about a
   collaboration invite, write something like "You've got a forwarded
   invite to collaborate on a project." If there's exactly one email,
   write it as a single line with no number. **If there's more than
   one, use a numbered list** (`1.`, `2.`, ...), one email per line —
   never blend multiple emails into consecutive sentences, and never
   combine them into one sentence (unlike the calendar line, which does
   combine). If there are no unread emails: "Inbox is empty."

Keep this same shape every time so the briefing is consistently
scannable. No padding, no preamble like "Here is your briefing:" —
just the three blocks above, each starting with its emoji. Don't
over-elaborate low-signal sections — one unread email or one quiet
afternoon still gets just one short line.

## What to leave out

- Raw JSON, file paths (e.g. the `.tmp/` snapshot path), or internal tool
  names — none of that is useful to someone reading this over coffee.
- Any section whose underlying script actually failed should be reported
  plainly as a failure, not silently dropped or guessed at.
