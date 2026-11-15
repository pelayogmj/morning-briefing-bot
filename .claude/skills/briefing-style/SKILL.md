---
name: briefing-style
description: Tone, length, and prioritization rules for rendering the daily morning briefing. Use when composing the final briefing text for the user from raw weather/calendar/email data.
user-invocable: false
---

# Briefing Style

Rules for turning the raw output of `tools/get_weather.py`,
`tools/get_calendar.py`, `tools/get_gmail.py`, `tools/get_tasks.py`, and
`tools/fetch_news.py` into the final text shown to the user — used by both the interactive
`/briefing` command and the automated `tools/send_morning_briefing.py`
pipeline. This is presentation guidance only — never re-fetch or
re-derive the underlying data; just rephrase (and, for news, filter)
what the tools already reported.

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

Always four required blocks plus one optional 5th, in this fixed
order, **separated by a blank line** — never reorder based on urgency,
and never merge them into one flowing paragraph. This is plain text
(no Markdown/HTML bold or asterisks — it won't render as formatting
and may break delivery) — use an emoji at the start of each block
instead to make it scannable at a glance:

1. **🌤️ Weather** (pick the emoji to match conditions — e.g. ☀️ clear,
   ⛅/☁️ cloudy/overcast, 🌧️ rain, ❄️ snow, 🌫️ fog, ⛈️ thunderstorms):
   "Good morning! Today in {location} {weather description}, {temps},
   {rain chance}." Three possible raw shapes, handle each honestly:
   - Full data (description, high/low, a rain percentage): use the
     template above.
   - A fallback reading (just high/low and "rain is possible"/"no rain
     is expected", no condition description or percentage — this means
     the primary weather source was down and a backup with less detail
     was used): report the high/low and that rain clause plainly, e.g.
     "it'll be between {low} and {high}, with rain possible" — don't
     invent a sky condition (clear/cloudy/etc.) or a fake percentage
     you weren't given.
   - Unavailable (both weather sources failed): say so in one short
     line — e.g. "Weather data isn't available this morning." — don't
     force it into the template.
2. **📅 Calendar** — if there's at least one event, start with "Today's
   events are:" then a bulleted list (`•`, not `-`), one event per
   bullet, each stating its time and title, e.g.:
   "Today's events are:
   • 12:30 lunch with Alex
   • 15:00 team meeting
   • 21:00 dinner with Megan"
   If there are no events: just "Nothing on your calendar today." — no
   lead-in line, no bullets, that one line only.
3. **📬 Inbox** — if there's at least one unread email, start with "Your
   unread emails are:" then a bulleted list (`•`, not `-` or numbers),
   one email per bullet. For each, write a short summary of what it's
   actually *about*, using its snippet (the short content preview each
   email tool run provides) — not a reworded subject line. E.g. given
   subject "Fwd: You've been invited..." and a snippet about a
   collaboration invite, write "• You've got a forwarded invite to
   collaborate on a project." Never blend multiple emails into one
   bullet or merge them into prose. If there are no unread emails: just
   "Inbox is empty." — no lead-in line, no bullets.
4. **📋 Tasks** — unlike every other block, render the raw data **as-is**
   rather than rephrasing it: `tools/get_tasks.py` already decides which
   of three cases applies and hands you the finished text, lead-in line
   and bullets included where relevant — don't re-derive due dates,
   re-decide the case, or paraphrase it into prose.
   - If the raw block starts with "Today's tasks are:" followed by a
     bulleted list (`•`), keep it exactly as given — this is the one
     block in the briefing meant to read as a scannable checklist rather
     than a flowing sentence. An overdue task's bullet already states
     its original due date and the word "overdue" — never soften or
     drop that label.
   - Otherwise it's already a single finished line (either reporting how
     many dateless open items remain, or that the to-do list is clear)
     — pass it through unchanged.
   - Always present — never omitted, unlike News below.
5. **🌍 News** (optional — the only block that can be fully omitted;
   unlike the four above, it never falls back to a placeholder like
   "nothing notable"). Two dimensions, not one flat list: regions
   (global, Spain, Switzerland, Europe) crossed with topics (politics/
   social/environmental, and financial markets as a cross-cutting lens
   on those same regions — not a separate 5th place). Rules:
   - Only include this block if something is genuinely significant.
     If nothing meets that bar, skip the block entirely — no "quiet
     news day today" line, nothing. Silence is the correct output on
     most days.
   - Hard cap: 1–5 sentences *total*, not per region/topic. One clearly
     significant item beats three marginal ones — never pad toward the
     cap just to fill it.
   - **Each sentence is one short clause, core fact only** — roughly
     15–20 words, no backstory, no quotes, no "which comes after/amid
     ..." context clauses, no restating the same fact two ways. Say
     "Spain raised its minimum wage by 5%," not "Spain's government
     announced today that it will be raising the minimum wage by 5%,
     a move that comes after months of pressure from unions." If a
     story needs more than one short clause to state the core fact,
     cut the rest rather than extending the sentence.
   - **Judge substance, not headline tone.** Headlines (financial or
     otherwise) are often written to grab attention rather than
     neutrally state significance. Use each item's title *and*
     description together to judge genuine newsworthiness — a dramatic-
     sounding title isn't proof something matters, and a flat-sounding
     one doesn't mean it doesn't.
   - For markets specifically: mention a concrete figure (e.g. "+1.2%")
     only if the source material actually states one — never invent a
     number; describe direction/reason in plain words otherwise.

Keep this same shape every time so the briefing is consistently
scannable. No padding, no preamble like "Here is your briefing:" —
just the blocks above, each starting with its emoji. Don't
over-elaborate low-signal sections — one unread email or one quiet
afternoon still gets just one short line.

## What to leave out

- Raw JSON, file paths (e.g. the `.tmp/` snapshot path), or internal tool
  names — none of that is useful to someone reading this over coffee.
- Any section whose underlying script actually failed should be reported
  plainly as a failure, not silently dropped or guessed at.
