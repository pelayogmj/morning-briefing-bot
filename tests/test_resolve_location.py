import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from resolve_location import parse_geocode_response


def test_parse_geocode_response_match():
    data = {
        "results": [
            {
                "name": "Paris",
                "latitude": 48.8566,
                "longitude": 2.3522,
                "country": "France",
                "timezone": "Europe/Paris",
            },
            {
                "name": "Paris",
                "latitude": 33.6609,
                "longitude": -95.5555,
                "country": "United States",
                "timezone": "America/Chicago",
            },
        ]
    }
    assert parse_geocode_response(data) == ("Paris", 48.8566, 2.3522, "Europe/Paris")


def test_parse_geocode_response_missing_timezone():
    data = {"results": [{"name": "Nowhere", "latitude": 0.0, "longitude": 0.0}]}
    assert parse_geocode_response(data) == ("Nowhere", 0.0, 0.0, None)


def test_parse_geocode_response_no_match():
    assert parse_geocode_response({"results": []}) is None
    assert parse_geocode_response({}) is None
