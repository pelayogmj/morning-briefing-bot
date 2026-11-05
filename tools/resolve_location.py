"""Resolve a free-text place name to coordinates via Open-Meteo's free,
no-key geocoding API -- used when today's calendar implies travel to a
specific city, so the weather section reflects where the user actually
is rather than always reporting their configured home location.
"""
import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def parse_geocode_response(data):
    """Extract (name, lat, lon, timezone) from a raw Open-Meteo geocoding
    response. `timezone` is an IANA string (e.g. "Europe/Paris"), already
    included in the geocoding response -- no separate timezone API needed.

    Returns None if there's no match -- not an error, just "couldn't
    resolve this name," which callers should treat as a reason to fall
    back to the configured home location, not a failure.
    """
    results = data.get("results")
    if not results:
        return None
    top = results[0]
    return top["name"], top["latitude"], top["longitude"], top.get("timezone")


def geocode(place_name):
    response = requests.get(
        GEOCODING_URL, params={"name": place_name, "count": 1}, timeout=10
    )
    response.raise_for_status()
    return parse_geocode_response(response.json())
