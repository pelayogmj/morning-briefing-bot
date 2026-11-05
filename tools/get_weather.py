"""Print today's weather summary for the configured location using Open-Meteo."""

import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"

# Open-Meteo occasionally resets the connection (observed repeatedly as
# ConnectionResetError on Windows) for no server-side reason -- a transient
# network blip, not a real failure. Retry a couple of times before giving up.
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

# WMO weather codes (subset relevant to Open-Meteo's `weathercode` field).
WEATHER_CODES = {
    0: "clear sky",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "foggy with rime",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorms",
}


def describe_weather_code(code):
    """Map a WMO weather code to a short human-readable description."""
    return WEATHER_CODES.get(code, "unknown conditions")


def format_summary(location_name, daily):
    """Build the one-paragraph briefing from a parsed 'today' daily record.

    `daily` is a dict with keys: high, low, precipitation_probability, weather_code.
    """
    description = describe_weather_code(daily["weather_code"])
    return (
        f"Good morning! Today in {location_name}: {description}, "
        f"high {daily['high']:.0f}°C / low {daily['low']:.0f}°C, "
        f"{daily['precipitation_probability']:.0f}% chance of rain."
    )


def parse_today(api_response):
    """Extract today's (index 0) values from the Open-Meteo `daily` block."""
    daily = api_response["daily"]
    return {
        "high": daily["temperature_2m_max"][0],
        "low": daily["temperature_2m_min"][0],
        "precipitation_probability": daily["precipitation_probability_max"][0],
        "weather_code": daily["weathercode"][0],
    }


def fetch_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "timezone": "auto",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def save_snapshot(api_response):
    TMP_DIR.mkdir(exist_ok=True)
    snapshot_path = TMP_DIR / f"weather_{date.today().isoformat()}.json"
    snapshot_path.write_text(json.dumps(api_response, indent=2))
    return snapshot_path


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
        api_response = fetch_forecast(lat, lon)
    except requests.RequestException as exc:
        print(f"Error: could not fetch weather data ({exc})", file=sys.stderr)
        sys.exit(1)

    snapshot_path = save_snapshot(api_response)
    today = parse_today(api_response)
    print(format_summary(location_name, today))
    print(f"(raw forecast saved to {snapshot_path})")


if __name__ == "__main__":
    main()
