"""Print today's Google Calendar events via direct API access (no MCP)."""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth import SCOPES, get_credentials

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def filter_events_for_day(items, day):
    """Drop all-day events that don't actually cover `day`.

    The Calendar API returns any event overlapping the requested time
    window. An all-day event is anchored to the *calendar's* timezone, so
    when the window is computed in a different zone (e.g. a UTC CI
    runner) tomorrow's all-day event overlaps today's window by an hour
    or more and would be listed a day early. All-day events carry plain
    dates with an exclusive `end.date`, so keep one only if
    start.date <= day < end.date (which still handles multi-day events).
    Timed events are kept as returned.
    """
    kept = []
    for item in items:
        start = item.get("start", {})
        if "date" not in start:
            kept.append(item)
            continue
        start_day = date.fromisoformat(start["date"])
        end_raw = item.get("end", {}).get("date")
        end_day = date.fromisoformat(end_raw) if end_raw else start_day + timedelta(days=1)
        if start_day <= day < end_day:
            kept.append(item)
    return kept


def parse_events(items):
    """Extract {summary, time, all_day, location} from raw Calendar API `items`.

    `location` is the event's free-text location field (empty string if
    unset) -- used to infer today's likely city for travel days, see
    tools/resolve_location.py.
    """
    events = []
    for item in items:
        summary = item.get("summary", "(no title)")
        location = item.get("location", "")
        start = item.get("start", {})
        if "date" in start:
            events.append(
                {"summary": summary, "time": None, "all_day": True, "location": location}
            )
        else:
            date_time = start.get("dateTime", "")
            time_str = date_time[11:16] if len(date_time) >= 16 else date_time
            events.append(
                {"summary": summary, "time": time_str, "all_day": False, "location": location}
            )
    return events


def format_events_summary(events):
    if not events:
        return "No events today."
    lines = ["Today's events:"]
    for event in events:
        if event["all_day"]:
            lines.append(f"  - All day: {event['summary']}")
        else:
            lines.append(f"  - {event['time']} {event['summary']}")
    return "\n".join(lines)


def resolve_timezone_name(timezone_name=None):
    """The IANA zone "today" is measured in: the given name, else
    HOME_TIMEZONE, else None (meaning the machine's own local zone)."""
    return timezone_name or os.environ.get("HOME_TIMEZONE") or None


def local_today(timezone_name=None):
    """Today's date in the zone resolve_timezone_name() picks."""
    timezone_name = resolve_timezone_name(timezone_name)
    if timezone_name:
        return datetime.now(ZoneInfo(timezone_name)).date()
    return date.today()


def fetch_today_events(timezone_name=None):
    """Fetch today's events, where "today" is the local day in
    `timezone_name` (see resolve_timezone_name) -- never the machine's
    clock zone by accident, since CI runners are UTC."""
    creds = get_credentials(SCOPES)
    service = build("calendar", "v3", credentials=creds)

    timezone_name = resolve_timezone_name(timezone_name)
    if timezone_name:
        now = datetime.now(ZoneInfo(timezone_name))
    else:
        now = datetime.now().astimezone()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    calendar_id = os.environ.get("CALENDAR_ID", "primary")

    list_args = {
        "calendarId": calendar_id,
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_day.isoformat(),
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if timezone_name:
        # Makes the API return timed events' dateTime in this zone, so the
        # HH:MM parse_events() shows is local time for the user.
        list_args["timeZone"] = timezone_name

    result = service.events().list(**list_args).execute()
    return filter_events_for_day(result.get("items", []), start_of_day.date())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(PROJECT_ROOT / ".env")

    try:
        items = fetch_today_events()
    except Exception as exc:
        print(f"Error: could not fetch calendar events ({exc})", file=sys.stderr)
        sys.exit(1)

    print(format_events_summary(parse_events(items)))


if __name__ == "__main__":
    main()
