import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from get_weather import (
    describe_weather_code,
    format_fallback_summary,
    format_summary,
    parse_fallback_today,
    parse_today,
)


def test_describe_weather_code_known():
    assert describe_weather_code(0) == "clear sky"
    assert describe_weather_code(61) == "light rain"


def test_describe_weather_code_unknown():
    assert describe_weather_code(999) == "unknown conditions"


def test_parse_today_extracts_first_day():
    api_response = {
        "daily": {
            "temperature_2m_max": [18.2, 20.1],
            "temperature_2m_min": [9.4, 10.0],
            "precipitation_probability_max": [20, 50],
            "weathercode": [2, 61],
        }
    }
    assert parse_today(api_response) == {
        "high": 18.2,
        "low": 9.4,
        "precipitation_probability": 20,
        "weather_code": 2,
    }


def test_format_summary():
    daily = {
        "high": 18.0,
        "low": 9.0,
        "precipitation_probability": 20,
        "weather_code": 2,
    }
    summary = format_summary("Zurich", daily)
    assert summary == (
        "Good morning! Today in Zurich: partly cloudy, "
        "high 18°C / low 9°C, 20% chance of rain."
    )


# -- MET Norway fallback -----------------------------------------------

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def _entry(time_str, high=None, low=None, precipitation=0.0, has_details=True):
    details = {}
    if has_details:
        if high is not None:
            details["air_temperature_max"] = high
        if low is not None:
            details["air_temperature_min"] = low
        details["precipitation_amount"] = precipitation
    return {"time": time_str, "data": {"next_6_hours": {"details": details}}}


def test_parse_fallback_today_aggregates_high_low_across_matching_entries():
    api_response = {
        "properties": {
            "timeseries": [
                _entry("2026-11-15T06:00:00Z", high=8.0, low=3.0),
                _entry("2026-11-15T12:00:00Z", high=12.0, low=6.0),
            ]
        }
    }
    assert parse_fallback_today(api_response, now=NOW) == {
        "high": 12.0,
        "low": 3.0,
        "rain_expected": False,
    }


def test_parse_fallback_today_ignores_entries_from_other_dates():
    api_response = {
        "properties": {
            "timeseries": [
                _entry("2026-11-15T12:00:00Z", high=12.0, low=6.0),
                _entry("2026-11-16T06:00:00Z", high=20.0, low=15.0),
            ]
        }
    }
    assert parse_fallback_today(api_response, now=NOW) == {
        "high": 12.0,
        "low": 6.0,
        "rain_expected": False,
    }


def test_parse_fallback_today_detects_rain_expected():
    api_response = {
        "properties": {
            "timeseries": [_entry("2026-11-15T12:00:00Z", high=12.0, low=6.0, precipitation=1.5)]
        }
    }
    assert parse_fallback_today(api_response, now=NOW)["rain_expected"] is True


def test_parse_fallback_today_no_rain_when_all_zero():
    api_response = {
        "properties": {
            "timeseries": [_entry("2026-11-15T12:00:00Z", high=12.0, low=6.0, precipitation=0.0)]
        }
    }
    assert parse_fallback_today(api_response, now=NOW)["rain_expected"] is False


def test_parse_fallback_today_skips_entries_missing_details():
    api_response = {
        "properties": {
            "timeseries": [
                _entry("2026-11-15T00:00:00Z", has_details=False),
                _entry("2026-11-15T12:00:00Z", high=12.0, low=6.0),
            ]
        }
    }
    assert parse_fallback_today(api_response, now=NOW) == {
        "high": 12.0,
        "low": 6.0,
        "rain_expected": False,
    }


def test_parse_fallback_today_returns_none_when_no_matching_entries():
    api_response = {
        "properties": {"timeseries": [_entry("2026-11-16T12:00:00Z", high=12.0, low=6.0)]}
    }
    assert parse_fallback_today(api_response, now=NOW) is None


def test_format_fallback_summary_with_rain():
    fallback_today = {"high": 12.0, "low": 6.0, "rain_expected": True}
    assert format_fallback_summary("Zurich", fallback_today) == (
        "Good morning! Today in Zurich: high 12°C / low 6°C, rain is possible."
    )


def test_format_fallback_summary_without_rain():
    fallback_today = {"high": 12.0, "low": 6.0, "rain_expected": False}
    assert format_fallback_summary("Zurich", fallback_today) == (
        "Good morning! Today in Zurich: high 12°C / low 6°C, no rain is expected."
    )
