---
description: Gather weather/calendar/email data and render today's briefing
allowed-tools: Bash(.venv/Scripts/python.exe tools/*.py:*)
---

Run today's morning briefing and present it to the user in natural,
human-toned prose.

Steps:
1. Run `.venv/Scripts/python.exe tools/morning_briefing.py` from the
   project root using the Bash tool, and read its raw output (weather
   paragraph, calendar events block, inbox block).
2. Read `.claude/skills/briefing-style/SKILL.md` and follow its tone,
   length, and prioritization rules exactly.
3. Compose the final briefing as prose following that guidance — do not
   just print the tool's raw mechanical text back to the user.
4. If the script exits with an error (any section failed), report that
   failure plainly instead of fabricating or omitting that section.
