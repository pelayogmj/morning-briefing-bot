# Morning Briefing Bot

A self-hosted bot that sends you one daily message on Telegram: today's
weather, calendar, unread email, to-do list, and a short news roundup.
It runs for free on GitHub Actions and uses Claude to write the final
text in plain, human prose instead of raw data dumps.

## Sample briefing

This is made up, not a real send. It shows the fixed shape every
briefing follows.

```
Good morning! Today in Paris expect sun with a few clouds, high 19°C /
low 11°C, 10% chance of rain.

Today's events are:
• 10:00 dentist appointment
• 13:00 lunch with Sam
• 18:30 gym

Your unread emails are:
• A newsletter recapping last week's top three tech stories.
• A reminder that your package is arriving tomorrow.

Today's tasks are:
• Finish the quarterly report
• Call the plumber

Spain's parliament approved a new rent control bill for large cities.
```

Weather, calendar, inbox, and tasks always appear. News only appears
when something is genuinely worth mentioning; most days it's silent.
If a data source fails, that block says so plainly instead of being
guessed at or dropped silently.

## Features

- Weather from Open-Meteo, with MET Norway as an automatic fallback if
  the primary source is down.
- Google Calendar events for today, read via direct API access.
- Unread Gmail, summarized by content rather than just subject lines.
- Google Tasks, with overdue items called out explicitly.
- A short news roundup (world, Europe, your home country, markets),
  shown only when something is actually significant.
- Automatic travel detection: if today's calendar implies you're
  somewhere else (an explicit location field, or a title like "Flight
  to London"), the weather block switches to that city for the day.
- Telegram commands to pause/resume the bot, change its send time, or
  override its timezone while traveling, without touching any code.
- Runs on a schedule with no server to maintain, using GitHub Actions'
  free tier plus a free external cron ping for reliable timing.

## Claude Code features used

- **Skill** (`.claude/skills/briefing-style/SKILL.md`) — the tone,
  format, and prioritization rules used to turn raw data into the
  final briefing text.
- **Slash command** (`.claude/commands/briefing.md`, invoked as
  `/briefing`) — runs the briefing interactively inside a Claude Code
  session and applies the skill above.
- **Subagent** (`.claude/agents/email-triager.md`) — a separate agent
  that ranks unread email by urgency, usable on its own.
- **Hooks** (`.claude/hooks/`) — enforce things a prompt alone can't
  guarantee: blocking reads of secret files, blocking destructive
  shell commands, requiring a security review before any commit, and
  running tests automatically after editing a tool.
- **Headless Claude** — the unattended GitHub Actions run calls the
  `claude` CLI directly (no interactive session) to write the final
  briefing text from already-fetched data, and separately to judge
  whether today's calendar implies travel.
- **MCP** — Google Calendar and Gmail MCP servers, usable inside an
  interactive Claude Code session (e.g. for `/briefing`). The
  unattended GitHub Actions run does not use MCP; it calls the Google
  APIs directly, since MCP servers only work with a live session.

## Architecture

```
GitHub Actions (hourly schedule + external cron ping)
        |
        v
tools/manage_pause_state.py   -- reads Telegram commands, decides
        |                         SEND or SKIP, never calls Claude
        v  (only if SEND)
tools/send_morning_briefing.py
        |
        +--> tools/get_weather.py     (Open-Meteo, MET Norway fallback)
        +--> tools/get_calendar.py    (Google Calendar API)
        +--> tools/get_gmail.py       (Gmail API)
        +--> tools/get_tasks.py       (Google Tasks API)
        +--> tools/fetch_news.py      (free RSS feeds)
        |
        v
headless `claude` call (reads the skill, writes the final text)
        |
        v
tools/send_telegram.py  -- sends the message
```

Bot state (paused/resumed, timezone override, custom send time, last
send date) lives on its own orphan git branch (`briefing-state`), kept
separate from the project's real history.

The interactive path (`/briefing` inside Claude Code) uses
`tools/morning_briefing.py` instead, and can use MCP for Calendar and
Gmail since a live session is available.

## Setup

See [SETUP.md](SETUP.md) for a full walkthrough, written for someone
who has never used Google Cloud: Google OAuth, a Telegram bot, GitHub
Actions secrets, the external cron pinger, and a first test run.

Quick local setup, once you have `credentials.json` from Google Cloud:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env`, then run any Google-auth tool once to go through the
one-time interactive consent flow:

```powershell
.venv\Scripts\python.exe tools/get_tasks.py
```

Run tests:

```powershell
.venv\Scripts\python.exe -m pytest
```

## Telegram commands

Send these as plain messages to your bot:

| Command | Effect |
|---|---|
| `stop` / `pause` | Pause the daily briefing |
| `continue` / `resume` / `start` | Resume it |
| `timezone <city name>` | Use this city's timezone until reset, e.g. `timezone Paris` |
| `timezone reset` | Go back to your home timezone |
| `time HH:MM` | Set the daily send time, e.g. `time 06:30` |
| `time reset` | Restore the default send time (07:00) |
| `help` | List all commands |

## Costs

Built entirely on free tiers:

- GitHub Actions: free for public repos; on a private repo, roughly
  275 minutes/month at hourly polling, well under the 2,000 free
  minutes/month on the free plan.
- Weather, news, and geocoding: free, no API key.
- Google Calendar/Gmail/Tasks APIs: free within normal personal-use
  limits.
- Telegram Bot API: free.
- Claude: billed through your own Claude Pro/Max subscription (via
  `claude setup-token`), not a separate pay-per-token API key, so
  usage is bounded by your existing plan.
- External cron pinger (e.g. cron-job.org): free tier.

## Limitations

- GitHub's own `schedule:` trigger is unreliable on low-activity
  repos; this project relies on an external service pinging the
  workflow instead (see SETUP.md).
- Needs a one-time interactive Google OAuth consent from a human; it
  can't bootstrap that step unattended.
- MET Norway's weather fallback has no rain percentage for most
  non-Nordic locations, so it reports "rain possible" rather than a
  number.
- News significance judgments come from Claude's own reading of RSS
  headlines/descriptions, not a dedicated ranking model.
- Designed around one user and one Telegram chat, not multi-user.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
