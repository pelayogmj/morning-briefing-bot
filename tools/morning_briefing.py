"""Combined morning briefing: weather + today's calendar + top unread emails.

Reuses the fetch/parse/format functions from the individual get_*.py tools.
Each of those remains independently runnable for debugging a single section.
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from get_calendar import fetch_today_events, format_events_summary, parse_events
from get_gmail import DEFAULT_LIMIT, fetch_top_unread, format_inbox_summary, parse_unread_messages
from get_weather import fetch_forecast, format_summary, parse_today, save_snapshot

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

    try:
        weather_response = fetch_forecast(lat, lon)
    except requests.RequestException as exc:
        print(f"Error: could not fetch weather data ({exc})", file=sys.stderr)
        sys.exit(1)
    save_snapshot(weather_response)
    weather_line = format_summary(location_name, parse_today(weather_response))

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

    print(weather_line)
    print()
    print(events_block)
    print()
    print(inbox_block)


if __name__ == "__main__":
    main()
