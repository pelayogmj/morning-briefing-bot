"""Orchestrate the automated morning briefing: fetch data, infer today's
likely location from the calendar, decide whether to invoke Claude for
styling, and send the result via Telegram.

Entry point for the GitHub Actions scheduled workflow (see
.github/workflows/morning-briefing.yml). For interactive use, use the
/briefing command instead -- this script is built for unattended runs.
"""
import os
import shutil
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
from get_weather import fetch_forecast, format_summary, parse_today, save_snapshot
from manage_pause_state import load_state, resolve_effective_timezone, save_state
from resolve_location import geocode
from send_telegram import send_message

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEADLESS_TIMEOUT_SECONDS = 300
SKILL_PATH = ".claude/skills/briefing-style/SKILL.md"

# shutil.which (not a bare "claude" string) resolves platform-specific
# executable extensions -- on Windows, the npm global install is a
# claude.cmd wrapper, and subprocess.run's list-argument form doesn't do
# the shell's PATHEXT resolution needed to find it, failing with
# FileNotFoundError even though `claude` works fine typed directly into
# a shell. Linux (CI) has no such issue, but resolving properly here
# means this script actually works for local testing too.
CLAUDE_EXECUTABLE = shutil.which("claude") or "claude"


def run_headless_claude(prompt, extra_args):
    """Run `claude -p` with the given prompt fed via stdin, not as a CLI
    argument.

    A multi-line prompt passed as a positional argument got silently
    truncated at the first newline on Windows -- invoking the npm
    .cmd wrapper routes through cmd.exe's own command-line parsing,
    which doesn't handle embedded newlines in arguments. Stdin input
    sidesteps that entirely and works identically on both platforms.

    encoding="utf-8" is explicit and required: the briefing-style skill
    uses emoji, and without it, text=True decodes using Windows' default
    console codepage (cp1252), which can't handle them and crashes.
    """
    result = subprocess.run(
        [CLAUDE_EXECUTABLE, "-p", *extra_args],
        input=prompt,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=HEADLESS_TIMEOUT_SECONDS,
    )
    return result


def infer_travel_location(events):
    """Ask a minimal headless Claude call whether today's events imply
    travel to a specific city -- covers informal cases a plain `location`
    field check would miss, like an event titled "Meeting in Paris" or
    "Train to Zurich" with no structured location set.

    This call is granted NO tools at all (not even reading the skill
    file) -- it can only return text. Event titles/locations come from
    the user's own calendar, but anyone who can send them a calendar
    invite can influence this input, so keeping it tool-less means even
    a maliciously crafted invite attempting prompt injection can at
    worst produce a wrong city guess (harmless -- falls back to home on
    a bad geocode), never anything more dangerous.

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

    result = run_headless_claude(
        prompt,
        ["--permission-prompts", "none", "--tools", "", "--output-format", "text"],
    )
    if result.returncode != 0:
        print(
            f"Warning: location inference failed, using home location "
            f"({result.stderr.strip()})",
            file=sys.stderr,
        )
        return None

    answer = result.stdout.strip()
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


def compose_styled_briefing(weather_line, events_block, inbox_block):
    """Invoke headless Claude to render the full styled briefing.

    All data is fetched deterministically by this script (main(), below)
    and handed to Claude directly in the prompt -- it gets no Bash tool
    at all for this step, only Read access to the one skill file.

    This replaced an earlier design where Claude was asked to fetch the
    data itself via Bash (even with one fully concrete pre-resolved
    command): its actual tool-call invocation kept not matching the
    literal --allowedTools pattern and getting silently auto-denied
    under --permission-prompts none, so it explained the failure in
    prose instead of erroring -- which then got sent as if it were the
    real briefing. Removing Bash from this step removes that whole class
    of failure. It also closes a real security gap: this step renders
    actual email content, and a maliciously crafted email attempting
    prompt injection could previously have tried to get an unattended
    Bash-capable Claude to run something. With no Bash tool available,
    the worst case is bad *text*, never an executed command.

    Authenticates via CLAUDE_CODE_OAUTH_TOKEN (set in the environment),
    bound to the Pro plan's usage limits rather than pay-per-token API
    billing.
    """
    prompt = (
        "Render today's morning briefing as prose. Here is the raw data "
        "already fetched -- do not re-fetch, re-derive, or invent "
        "anything beyond it:\n\n"
        f"Weather: {weather_line}\n\n"
        f"Calendar: {events_block}\n\n"
        f"Inbox: {inbox_block}\n\n"
        f"Read {SKILL_PATH} and follow its tone, format, and content "
        "rules exactly."
    )

    result = run_headless_claude(
        prompt,
        [
            "--permission-prompts",
            "none",
            "--tools",
            "Read",
            "--allowedTools",
            f"Read({SKILL_PATH})",
            "--output-format",
            "text",
        ],
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"headless claude failed (exit {result.returncode}): {result.stderr}"
        )
    return result.stdout.strip()


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

    try:
        events = parse_events(fetch_today_events())
    except Exception as exc:
        print(f"Error: could not fetch calendar events ({exc})", file=sys.stderr)
        sys.exit(1)

    try:
        messages = parse_unread_messages(fetch_top_unread(DEFAULT_LIMIT))
    except Exception as exc:
        print(f"Error: could not fetch Gmail messages ({exc})", file=sys.stderr)
        sys.exit(1)

    if not events and not messages:
        # Nothing but weather to report -- no Claude call at all, home
        # location only (nothing to infer travel from), genuinely free.
        location_name, lat, lon = home_name, home_lat, home_lon
    else:
        location_name, lat, lon = resolve_todays_location(
            home_name, home_lat, home_lon, events
        )

    try:
        forecast = fetch_forecast(lat, lon)
    except Exception as exc:
        print(f"Error: could not fetch weather data ({exc})", file=sys.stderr)
        sys.exit(1)
    save_snapshot(forecast)
    weather_line = format_summary(location_name, parse_today(forecast))

    if not events and not messages:
        message = weather_line
    else:
        try:
            message = compose_styled_briefing(
                weather_line,
                format_events_summary(events),
                format_inbox_summary(messages),
            )
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
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
