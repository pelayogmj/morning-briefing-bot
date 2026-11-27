"""Orchestrate the automated morning briefing: fetch data, infer today's
likely location from the calendar, have an LLM style the briefing, and
send the result via Telegram.

Entry point for the GitHub Actions scheduled workflow (see
.github/workflows/morning-briefing.yml). For interactive use, use the
/briefing command instead -- this script is built for unattended runs.

Both LLM calls go through tools/llm.py's run_llm(), which is
provider-neutral (LLM_PROVIDER env var) and grants the model no tools.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from get_calendar import fetch_today_events, format_events_summary, parse_events
from get_gmail import (
    DEFAULT_LIMIT,
    fetch_top_unread,
    format_inbox_summary,
    parse_unread_messages,
)
from fetch_news import fetch_all_headlines, format_headlines_block
from get_tasks import fetch_tasks, format_tasks_summary, parse_tasks
from get_weather import fetch_weather_line
from llm import LLMError, run_llm
from manage_pause_state import load_state, resolve_effective_timezone, save_state
from resolve_location import geocode
from send_telegram import send_message

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = PROJECT_ROOT / ".claude" / "skills" / "briefing-style" / "SKILL.md"


def strip_frontmatter(text):
    """Remove a leading YAML frontmatter block (--- ... ---), if any."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + len("\n---"):].lstrip("\n")
    return text


def load_style_rules(path=SKILL_PATH):
    """The briefing-style skill's rules, as plain text for the prompt.

    SKILL.md stays the single source of truth (the interactive /briefing
    command uses it as a Claude skill); here it's inlined into the prompt
    so the model needs no file-reading tool, which any provider supports.
    """
    return strip_frontmatter(Path(path).read_text(encoding="utf-8"))


def infer_travel_location(events):
    """Ask a minimal LLM call whether today's events imply travel to a
    specific city -- covers informal cases a plain `location` field check
    would miss, like an event titled "Meeting in Paris" or "Train to
    Zurich" with no structured location set.

    The model has NO tools -- it can only return text. Event
    titles/locations come from the user's own calendar, but anyone who
    can send them a calendar invite can influence this input, so a
    maliciously crafted invite attempting prompt injection can at worst
    produce a wrong city guess (harmless -- falls back to home on a bad
    geocode), never anything more dangerous.

    Returns a place name string, or None if no travel is indicated (or
    the call fails -- non-fatal, since this is an enhancement on top of
    an otherwise-complete briefing, not core data).
    """
    if not events:
        return None

    event_lines = "\n".join(
        f"- {e['summary']}" + (f" (location: {e['location']})" if e["location"] else "")
        for e in events
    )
    prompt = (
        "Here are today's calendar events:\n"
        f"{event_lines}\n\n"
        "Based ONLY on these, is the user likely traveling to a specific "
        "city today? Consider both explicit location fields and titles "
        "that imply travel (e.g. 'Meeting in Paris', 'Train to Zurich', "
        "'Flight to London'). Reply with ONLY the city name if so, or "
        "exactly HOME if there's no indication of travel. No other text."
    )

    try:
        answer = run_llm(prompt)
    except (LLMError, OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"Warning: location inference failed, using home location ({exc})",
            file=sys.stderr,
        )
        return None

    if not answer or answer.upper() == "HOME":
        return None
    return answer


def resolve_todays_location(home_name, home_lat, home_lon, events):
    """Pick today's (name, lat, lon): a geocoded travel location inferred
    from the calendar, or the configured home default.

    geocode() returns a 4-tuple (name, lat, lon, timezone) -- only the
    first 3 are relevant here (the weather call doesn't need a
    timezone); send-timing's effective timezone is resolved separately,
    from an explicit chat override or HOME_TIMEZONE, not from this
    calendar-based inference.
    """
    place_name = infer_travel_location(events)
    if place_name:
        try:
            geocoded = geocode(place_name)
        except Exception as exc:
            print(
                f"Warning: could not geocode '{place_name}', using home "
                f"location ({exc})",
                file=sys.stderr,
            )
            geocoded = None
        if geocoded:
            return geocoded[0], geocoded[1], geocoded[2]
    return home_name, home_lat, home_lon


def build_briefing_prompt(
    style_rules, weather_line, events_block, inbox_block, tasks_block, news_block
):
    """The full, self-contained styling prompt: raw data plus the style
    rules inlined, so the model needs no tools at all."""
    return (
        "Render today's morning briefing. Here is the raw data already "
        "fetched -- do not re-fetch, re-derive, or invent anything beyond "
        "it:\n\n"
        f"Weather: {weather_line}\n\n"
        f"Calendar: {events_block}\n\n"
        f"Inbox: {inbox_block}\n\n"
        f"Tasks: {tasks_block}\n\n"
        f"News headlines (raw, unfiltered -- judge for yourself what, if "
        f"anything, is actually significant enough to mention):\n{news_block}\n\n"
        "Follow these tone, format, and content rules exactly. Reply with "
        "only the finished briefing text.\n\n"
        "<style_rules>\n"
        f"{style_rules}\n"
        "</style_rules>"
    )


def compose_styled_briefing(weather_line, events_block, inbox_block, tasks_block, news_block):
    """Have the LLM render the full styled briefing.

    All data is fetched deterministically by this script (main(), below)
    and handed over directly in the prompt, together with the style
    rules -- the model gets no tools at all for this step.

    History: Claude was once asked to fetch data itself via Bash, then
    later to Read the skill file under an --allowedTools pattern. Both
    times its tool call silently failed to match the allowed pattern and
    got auto-denied, so it explained the failure in prose instead of
    erroring -- which then got sent as if it were the real briefing.
    Inlining everything removes that whole class of failure, and closes a
    security gap: this step renders real email content, and with no tools
    a malicious email attempting prompt injection can at worst produce
    bad *text*, never an executed command or a file read.
    """
    prompt = build_briefing_prompt(
        load_style_rules(),
        weather_line,
        events_block,
        inbox_block,
        tasks_block,
        news_block,
    )
    return run_llm(prompt)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print("Usage: send_morning_briefing.py <path-to-state-file>", file=sys.stderr)
        sys.exit(1)
    state_path = Path(sys.argv[1])

    load_dotenv(PROJECT_ROOT / ".env")

    home_name = os.environ.get("LOCATION_NAME")
    home_lat = os.environ.get("LAT")
    home_lon = os.environ.get("LON")
    home_timezone = os.environ.get("HOME_TIMEZONE")
    if not home_name or not home_lat or not home_lon or not home_timezone:
        print(
            "Error: LOCATION_NAME, LAT, LON, and HOME_TIMEZONE must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    state = load_state(state_path)
    effective_timezone = resolve_effective_timezone(state, home_timezone)

    # Calendar and Tasks both measure "today" in the effective timezone,
    # never the runner's UTC clock (that mismatch listed all-day events a
    # day early).
    local_date = datetime.now(ZoneInfo(effective_timezone)).date()

    try:
        events = parse_events(fetch_today_events(effective_timezone))
    except Exception as exc:
        print(f"Error: could not fetch calendar events ({exc})", file=sys.stderr)
        sys.exit(1)

    try:
        messages = parse_unread_messages(fetch_top_unread(DEFAULT_LIMIT))
    except Exception as exc:
        print(f"Error: could not fetch Gmail messages ({exc})", file=sys.stderr)
        sys.exit(1)

    try:
        tasks = parse_tasks(fetch_tasks())
    except Exception as exc:
        print(f"Error: could not fetch Google Tasks ({exc})", file=sys.stderr)
        sys.exit(1)

    # infer_travel_location() already returns None for an empty events
    # list, which cascades to the home default below -- no special-case
    # branch needed here for an empty calendar.
    location_name, lat, lon = resolve_todays_location(
        home_name, home_lat, home_lon, events
    )

    # fetch_weather_line() is soft-fail, unlike Calendar/Gmail/Tasks
    # above: it tries Open-Meteo (with its own retries), falls back to
    # MET Norway if that's still down, and only reports "unavailable" if
    # both fail -- never raises, so a dead weather API alone doesn't
    # block the rest of an otherwise-complete briefing from sending.
    weather_line = fetch_weather_line(location_name, lat, lon)

    # News is checked every day regardless of calendar/inbox state -- the
    # "genuinely zero-Claude quiet day" case is gone by design: Claude now
    # always runs, to judge whether anything is significant enough to
    # mention. A feed failure is non-fatal (see fetch_news.py).
    news_block = format_headlines_block(fetch_all_headlines())
    tasks_block = format_tasks_summary(tasks, today=local_date)

    try:
        message = compose_styled_briefing(
            weather_line,
            format_events_summary(events),
            format_inbox_summary(messages),
            tasks_block,
            news_block,
        )
    except (LLMError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Error: could not compose styled briefing ({exc})", file=sys.stderr)
        sys.exit(1)

    print(message)

    try:
        send_message(message, bot_token, chat_id)
    except Exception as exc:
        print(f"Error: could not send Telegram message ({exc})", file=sys.stderr)
        sys.exit(1)

    # Record today's send (in the effective timezone) only after a
    # confirmed successful send, so a failure partway through doesn't
    # falsely mark the day as already handled.
    state["last_sent_date"] = datetime.now(ZoneInfo(effective_timezone)).date().isoformat()
    save_state(state_path, state)


if __name__ == "__main__":
    main()
