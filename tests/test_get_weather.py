import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from get_weather import describe_weather_code, format_summary, parse_today


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
