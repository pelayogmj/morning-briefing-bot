# Workflow: Morning Weather Briefing

## Objective
Produce today's one-paragraph weather summary for the configured location.

## Required inputs
Set in `.env`:
- `LOCATION_NAME` — display name for the briefing (e.g. `Zurich`)
- `LAT` — latitude
- `LON` — longitude

## Tool to use
`tools/get_weather.py` — run via the project's virtualenv:

```
.venv/Scripts/python tools/get_weather.py
```

(Activate the venv first if you prefer: `.venv/Scripts/activate` then `python tools/get_weather.py`.)

## Expected output
- A printed one-paragraph summary, e.g.:
  `Good morning! Today in Zurich: partly cloudy, high 18°C / low 9°C, 20% chance of rain.`
- A raw JSON snapshot of the Open-Meteo response saved to `.tmp/weather_<YYYY-MM-DD>.json` (disposable; useful for debugging or for later stages to reuse).

## Edge cases
- **Missing `.env` config** (`LOCATION_NAME`/`LAT`/`LON` not set): the script prints a clear error to stderr and exits non-zero. It does not guess or fall back to defaults.
- **Transient connection reset** (observed repeatedly in practice — `ConnectionResetError` from Open-Meteo for no apparent server-side reason): `fetch_forecast` retries automatically up to 3 times with a 2s delay before giving up, since this is a network blip, not a real failure.
- **Network or API failure that persists past retries** (Open-Meteo unreachable, non-2xx response): the script prints a clear error to stderr and exits non-zero. It does not print stale or fabricated data.
- **Unknown weather code**: falls back to the string `"unknown conditions"` rather than failing (Open-Meteo's WMO code list may include codes outside the small lookup table in `tools/get_weather.py`).

## Notes
Source: free Open-Meteo forecast API (`https://api.open-meteo.com/v1/forecast`), no API key required.
