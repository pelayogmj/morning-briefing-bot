"""Combined morning briefing: weather + today's calendar + top unread emails.

Reuses the fetch/parse/format functions from the individual get_*.py tools.
Each of those remains independently runnable for debugging a single section.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from fetch_news import fetch_all_headlines, format_headlines_block
from get_calendar import fetch_today_events, format_events_summary, local_today, parse_events
from get_gmail import DEFAULT_LIMIT, fetch_top_unread, format_inbox_summary, parse_unread_messages
from get_tasks import fetch_tasks, format_tasks_summary, parse_tasks
from get_weather import fetch_weather_line

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(PROJECT_ROOT / ".env")

    location_name = os.environ.get("LOCATION_NAME")
    lat = os.environ.get("LAT")
    lon = os.environ.get("LON")
    if not location_name or not lat or not lon:
        print(
            "Error: LOCATION_NAME, LAT, and LON must be set in .env",
            file=sys.stderr,
        )
        sys.exit(1)

    # fetch_weather_line() is soft-fail, unlike the other blocks below:
    # it tries Open-Meteo first, falls back to MET Norway if that's
    # down, and only reports "unavailable" if both fail.
    weather_line = fetch_weather_line(location_name, lat, lon)

    # "Today" is measured in HOME_TIMEZONE if set, else this machine's
    # zone -- see get_calendar.resolve_timezone_name.
    try:
        calendar_items = fetch_today_events()
    except Exception as exc:
        print(f"Error: could not fetch calendar events ({exc})", file=sys.stderr)
        sys.exit(1)
    events_block = format_events_summary(parse_events(calendar_items))

    limit = int(os.environ.get("EMAIL_COUNT", DEFAULT_LIMIT))
    try:
        messages = fetch_top_unread(limit)
    except Exception as exc:
        print(f"Error: could not fetch Gmail messages ({exc})", file=sys.stderr)
        sys.exit(1)
    inbox_block = format_inbox_summary(parse_unread_messages(messages))

    try:
        tasks = fetch_tasks()
    except Exception as exc:
        print(f"Error: could not fetch Google Tasks ({exc})", file=sys.stderr)
        sys.exit(1)
    tasks_block = format_tasks_summary(parse_tasks(tasks), today=local_today())

    news_block = format_headlines_block(fetch_all_headlines())

    print(weather_line)
    print()
    print(events_block)
    print()
    print(inbox_block)
    print()
    print(tasks_block)
    print()
    print(news_block)


if __name__ == "__main__":
    main()
