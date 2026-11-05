import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from get_calendar import format_events_summary, parse_events


def test_parse_events_handles_all_day_and_timed():
    items = [
        {"summary": "Company holiday", "start": {"date": "2026-11-05"}},
        {
            "summary": "Team sync",
            "start": {"dateTime": "2026-11-05T09:00:00+01:00"},
        },
    ]
    assert parse_events(items) == [
        {"summary": "Company holiday", "time": None, "all_day": True, "location": ""},
        {"summary": "Team sync", "time": "09:00", "all_day": False, "location": ""},
    ]


def test_parse_events_defaults_missing_summary():
    items = [{"start": {"dateTime": "2026-11-05T14:30:00+01:00"}}]
    assert parse_events(items) == [
        {"summary": "(no title)", "time": "14:30", "all_day": False, "location": ""}
    ]


def test_parse_events_captures_location():
    items = [
        {
            "summary": "Client meeting",
            "start": {"dateTime": "2026-11-05T10:00:00+01:00"},
            "location": "London Office",
        }
    ]
    assert parse_events(items) == [
        {
            "summary": "Client meeting",
            "time": "10:00",
            "all_day": False,
            "location": "London Office",
        }
    ]


def test_format_events_summary_populated():
    events = [
        {"summary": "Company holiday", "time": None, "all_day": True, "location": ""},
        {"summary": "Team sync", "time": "09:00", "all_day": False, "location": ""},
    ]
    assert format_events_summary(events) == (
        "Today's events:\n"
        "  - All day: Company holiday\n"
        "  - 09:00 Team sync"
    )


def test_format_events_summary_empty():
    assert format_events_summary([]) == "No events today."
