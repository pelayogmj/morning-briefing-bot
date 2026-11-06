"""Check Telegram for pause/resume/timezone/time commands, update
persisted control state accordingly, and decide whether this hourly
poll is the one that should actually send the briefing.

Entry point for the GitHub Actions workflow's "Check pause/resume
state" step. The state file lives on a dedicated orphan branch
(briefing-state), checked out separately from the main job -- this
script doesn't know or care about that, it just reads/writes whatever
path it's given.

Never invokes headless Claude -- this check runs every poll and must
stay free; only tools/send_morning_briefing.py (run on the one poll
that actually matches) uses Claude, unchanged from before.

Usage: python tools/manage_pause_state.py <path-to-state-file>
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from resolve_location import geocode
from send_telegram import send_message

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GET_UPDATES_URL_TEMPLATE = "https://api.telegram.org/bot{token}/getUpdates"

PAUSE_WORDS = {"stop", "pause"}
RESUME_WORDS = {"continue", "resume", "start"}
HELP_WORDS = {"help", "--help", "-h", "/help", "commands", "?"}

TIME_COMMAND_PATTERN = re.compile(r"^time\s+(\d{1,2}:\d{2})$", re.IGNORECASE)
TIME_RESET_PATTERN = re.compile(r"^time\s+reset$", re.IGNORECASE)
TIMEZONE_COMMAND_PATTERN = re.compile(r"^timezone\s+(.+)$", re.IGNORECASE)
TIMEZONE_RESET_PATTERN = re.compile(r"^timezone\s+reset$", re.IGNORECASE)

HELP_TEXT = (
    "\U0001f4d6 Available commands:\n"
    "• stop / pause — pause the daily briefing\n"
    "• continue / resume / start — resume it\n"
    "• timezone <city> — set delivery timezone from a city name "
    "(e.g. \"timezone Paris\")\n"
    "• timezone reset — reset timezone to automatic\n"
    "• time HH:MM — set daily send time, 24h format "
    "(e.g. \"time 06:30\")\n"
    "• time reset — reset send time to the default (07:00)\n"
    "• help — show this message"
)

DEFAULT_STATE = {
    "paused": False,
    "last_update_id": 0,
    "last_sent_date": None,
    "timezone_override": None,
    "send_time": "07:00",
}


def parse_command(text):
    """Return (command, argument) for a recognized message.

    Commands: "pause", "resume", "timezone_set" (argument: a city
    name), "timezone_reset", "time_set" (argument: a raw "H:MM"/"HH:MM"
    string, not yet validated), "time_reset". (None, None) for anything
    unrecognized.
    """
    normalized = text.strip()
    lowered = normalized.lower()

    if lowered in PAUSE_WORDS:
        return "pause", None
    if lowered in RESUME_WORDS:
        return "resume", None
    if lowered in HELP_WORDS:
        return "help", None

    if TIME_RESET_PATTERN.match(normalized):
        return "time_reset", None

    time_match = TIME_COMMAND_PATTERN.match(normalized)
    if time_match:
        return "time_set", time_match.group(1)

    if TIMEZONE_RESET_PATTERN.match(normalized):
        return "timezone_reset", None

    timezone_match = TIMEZONE_COMMAND_PATTERN.match(normalized)
    if timezone_match:
        return "timezone_set", timezone_match.group(1).strip()

    return None, None


def validate_send_time(value):
    """Normalize a "H:MM"/"HH:MM" 24h string to "HH:MM", or None if the
    hour/minute are out of range."""
    match = re.match(r"^(\d{1,2}):(\d{2})$", value)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def apply_commands(state, messages, geocode_fn=geocode):
    """Apply each recognized command in `messages`, in order. Returns
    (new_state, confirmations) -- does not mutate the input `state`.

    `geocode_fn` is injectable so tests never make a live network call.
    """
    state = dict(state)
    confirmations = []

    for text in messages:
        command, argument = parse_command(text)

        if command == "pause":
            if not state["paused"]:
                state["paused"] = True
                confirmations.append(
                    "⏸️ Briefings paused — send 'continue' to resume."
                )

        elif command == "resume":
            if state["paused"]:
                state["paused"] = False
                confirmations.append("▶️ Briefings resumed.")

        elif command == "help":
            confirmations.append(HELP_TEXT)

        elif command == "time_set":
            normalized = validate_send_time(argument)
            if normalized:
                state["send_time"] = normalized
                confirmations.append(f"⏰ Briefing time set to {normalized}.")
            else:
                confirmations.append(
                    f"Couldn't understand '{argument}' as a 24h time (expected HH:MM)."
                )

        elif command == "time_reset":
            state["send_time"] = DEFAULT_STATE["send_time"]
            confirmations.append(
                f"⏰ Briefing time reset to {DEFAULT_STATE['send_time']} (default)."
            )

        elif command == "timezone_reset":
            state["timezone_override"] = None
            confirmations.append(
                "\U0001f550 Timezone reset to automatic (home default)."
            )

        elif command == "timezone_set":
            geocoded = geocode_fn(argument)
            timezone = geocoded[3] if geocoded else None
            if timezone:
                state["timezone_override"] = timezone
                confirmations.append(
                    f"\U0001f550 Timezone set to {timezone} (from '{argument}')."
                )
            else:
                confirmations.append(f"Couldn't find a timezone for '{argument}'.")

    return state, confirmations


def resolve_effective_timezone(state, home_timezone):
    return state.get("timezone_override") or home_timezone


def is_time_to_send(state, home_timezone, now=None):
    """True if, right now (local time in the effective timezone), we're
    at or past `send_time` and haven't already sent today (local date).

    `now`, if given, must be a tz-aware datetime (for testing);
    otherwise the real current time is used.

    Deliberately "at or past", not an exact hour match: GitHub's
    scheduled-workflow cron is best-effort and can be delayed by tens
    of minutes under load (observed directly -- a run meant for one
    hour slot actually started 25 minutes into the next). An exact
    match has no way to recover from that -- a delayed run just misses
    its window and the whole day goes unsent. "At or past" means
    whichever poll first lands after send_time that day catches up and
    sends, even if the intended hour's run was delayed or skipped
    entirely.
    """
    tz = ZoneInfo(resolve_effective_timezone(state, home_timezone))
    current = now.astimezone(tz) if now is not None else datetime.now(tz)

    if state.get("last_sent_date") == current.date().isoformat():
        return False

    target_hour, target_minute = (
        int(part) for part in state.get("send_time", "07:00").split(":")
    )
    return (current.hour, current.minute) >= (target_hour, target_minute)


def should_send(state, home_timezone, forced=False, now=None):
    """The overall SEND/SKIP decision: never when paused; otherwise the
    normal hour/already-sent gate, unless `forced` (a manual
    workflow_dispatch run -- "test it right now" should actually send
    right now, bypassing the gate -- but never bypassing an explicit
    pause).
    """
    if state["paused"]:
        return False
    return forced or is_time_to_send(state, home_timezone, now=now)


def fetch_updates(bot_token, offset):
    url = GET_UPDATES_URL_TEMPLATE.format(token=bot_token)
    response = requests.get(url, params={"offset": offset, "timeout": 0}, timeout=10)
    response.raise_for_status()
    return response.json().get("result", [])


def load_state(path):
    if path.exists():
        return {**DEFAULT_STATE, **json.loads(path.read_text())}
    return dict(DEFAULT_STATE)


def save_state(path, state):
    path.write_text(json.dumps(state))


def main():
    if len(sys.argv) != 2:
        print("Usage: manage_pause_state.py <path-to-state-file>", file=sys.stderr)
        sys.exit(1)
    state_path = Path(sys.argv[1])

    load_dotenv(PROJECT_ROOT / ".env")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    home_timezone = os.environ.get("HOME_TIMEZONE")
    if not bot_token or not chat_id or not home_timezone:
        print(
            "Error: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and HOME_TIMEZONE "
            "must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    state = load_state(state_path)

    try:
        updates = fetch_updates(bot_token, state["last_update_id"] + 1)
    except requests.RequestException as exc:
        print(
            f"Warning: could not check Telegram for commands ({exc}); "
            "proceeding with existing state.",
            file=sys.stderr,
        )
        updates = []

    messages = [
        update["message"]["text"]
        for update in updates
        if "message" in update and "text" in update["message"]
    ]
    new_state, confirmations = apply_commands(state, messages)

    if updates:
        new_state["last_update_id"] = max(u["update_id"] for u in updates)

    save_state(state_path, new_state)

    for confirmation in confirmations:
        try:
            send_message(confirmation, bot_token, chat_id)
        except requests.RequestException as exc:
            print(f"Warning: could not send confirmation ({exc})", file=sys.stderr)

    forced = os.environ.get("FORCE_SEND") == "1"
    print("SEND" if should_send(new_state, home_timezone, forced=forced) else "SKIP")


if __name__ == "__main__":
    main()
