"""Print today's Google Calendar events via direct API access (no MCP)."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth import SCOPES, get_credentials

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


def fetch_today_events():
    creds = get_credentials(SCOPES)
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now().astimezone()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    calendar_id = os.environ.get("CALENDAR_ID", "primary")

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


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
