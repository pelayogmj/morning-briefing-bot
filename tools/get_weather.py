"""Print today's weather summary for the configured location using Open-Meteo."""

import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"

# MET Norway's free Locationforecast API, used only as a fallback when
# Open-Meteo is unavailable even after its own retries -- a second,
# independently-hosted source so a single provider's outage (or, per
# research, shared-IP throttling on GitHub's hosted runners) doesn't take
# the weather block down. No API key, but their Terms of Service require
# a descriptive User-Agent naming the app and a contact/repo link -- a
# generic or missing one gets throttled (429) or blocked (403).
FALLBACK_FORECAST_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
FALLBACK_USER_AGENT = "MorningBriefingBot/1.0 github.com/pelayogmj/morning-briefing-bot"

# Open-Meteo occasionally resets the connection (observed repeatedly as
# ConnectionResetError on Windows) or times out reading a response
# (observed in CI as a ReadTimeout) for no server-side reason -- transient
# network blips, not real failures. Retry a couple of times before giving
# up. Both ConnectionError and Timeout are caught -- requests.ReadTimeout
# is a Timeout subclass, NOT a ConnectionError subclass, so catching only
# ConnectionError (as this used to) silently skips retrying on a timeout.
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
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def save_snapshot(api_response):
    TMP_DIR.mkdir(exist_ok=True)
    snapshot_path = TMP_DIR / f"weather_{date.today().isoformat()}.json"
    snapshot_path.write_text(json.dumps(api_response, indent=2))
    return snapshot_path


def fetch_fallback_forecast(lat, lon):
    response = requests.get(
        FALLBACK_FORECAST_URL,
        params={"lat": lat, "lon": lon},
        headers={"User-Agent": FALLBACK_USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def parse_fallback_today(api_response, now=None):
    """Extract today's high/low and a coarse rain-expected flag from a
    MET Norway forecast.

    Unlike Open-Meteo, MET Norway has no single daily max/min field and
    no rain *probability* for non-Nordic locations (confirmed live for
    Zurich) -- only hourly air_temperature, a 6-hour-window
    air_temperature_max/min, and precipitation_amount (mm, not a
    percentage). This aggregates every timeseries entry whose UTC date
    matches `now` (today, if not given) into one high/low, and flags
    rain as "expected" if any matching entry's precipitation_amount is
    above zero -- a coarser yes/no signal than Open-Meteo's percentage,
    reported as such rather than invented as a fake number.

    Returns None if no timeseries entry matches today (e.g. an
    unexpected response shape) -- the caller falls back further rather
    than reporting bogus data.
    """
    now = now or datetime.now(timezone.utc)
    today = now.date()

    highs, lows = [], []
    rain_expected = False
    for entry in api_response.get("properties", {}).get("timeseries", []):
        entry_time = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
        if entry_time.date() != today:
            continue
        details = entry.get("data", {}).get("next_6_hours", {}).get("details", {})
        if "air_temperature_max" in details:
            highs.append(details["air_temperature_max"])
        if "air_temperature_min" in details:
            lows.append(details["air_temperature_min"])
        if details.get("precipitation_amount", 0) > 0:
            rain_expected = True

    if not highs or not lows:
        return None

    return {"high": max(highs), "low": min(lows), "rain_expected": rain_expected}


def format_fallback_summary(location_name, fallback_today):
    rain_clause = "rain is possible" if fallback_today["rain_expected"] else "no rain is expected"
    return (
        f"Good morning! Today in {location_name}: high "
        f"{fallback_today['high']:.0f}°C / low {fallback_today['low']:.0f}°C, "
        f"{rain_clause}."
    )


def fetch_weather_line(location_name, lat, lon):
    """The single entry point orchestrators should call: try Open-Meteo
    (with its own built-in retries) first, fall back to MET Norway if
    that's still unavailable, and only report "unavailable" if both
    independent sources fail. Never raises -- a dead weather API
    shouldn't block the rest of an otherwise-complete briefing.
    """
    try:
        forecast = fetch_forecast(lat, lon)
        save_snapshot(forecast)
        return format_summary(location_name, parse_today(forecast))
    except requests.RequestException as exc:
        print(f"Warning: primary weather source failed ({exc})", file=sys.stderr)

    try:
        fallback_today = parse_fallback_today(fetch_fallback_forecast(lat, lon))
        if fallback_today is None:
            raise ValueError("no matching forecast entries for today")
        return format_fallback_summary(location_name, fallback_today)
    except Exception as exc:
        print(f"Warning: fallback weather source also failed ({exc})", file=sys.stderr)

    return "Weather data is currently unavailable."


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

    print(fetch_weather_line(location_name, lat, lon))


if __name__ == "__main__":
    main()
