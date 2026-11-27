import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from datetime import date

from get_calendar import filter_events_for_day, format_events_summary, parse_events

DAY = date(2026, 11, 5)


def _all_day(summary, start, end):
    return {"summary": summary, "start": {"date": start}, "end": {"date": end}}


def test_filter_excludes_tomorrows_all_day_event():
    # The original bug: a UTC-computed window overlaps tomorrow's
    # all-day event, so the API returns it a day early.
    items = [_all_day("Alex's birthday", "2026-11-06", "2026-11-07")]
    assert filter_events_for_day(items, DAY) == []


def test_filter_keeps_todays_all_day_event():
    items = [_all_day("Alex's birthday", "2026-11-05", "2026-11-06")]
    assert filter_events_for_day(items, DAY) == items


def test_filter_keeps_multi_day_event_spanning_today():
    items = [_all_day("Conference", "2026-11-04", "2026-11-07")]
    assert filter_events_for_day(items, DAY) == items


def test_filter_excludes_all_day_event_that_ended_yesterday():
    # end.date is exclusive: an event ending on DAY finished yesterday.
    items = [_all_day("Holiday", "2026-11-04", "2026-11-05")]
    assert filter_events_for_day(items, DAY) == []


def test_filter_keeps_timed_events_untouched():
    items = [{"summary": "Team sync", "start": {"dateTime": "2026-11-05T09:00:00+01:00"}}]
    assert filter_events_for_day(items, DAY) == items


def test_filter_all_day_event_without_end_counts_as_one_day():
    items = [{"summary": "Holiday", "start": {"date": "2026-11-05"}}]
    assert filter_events_for_day(items, DAY) == items
    assert filter_events_for_day(items, date(2026, 11, 6)) == []


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
