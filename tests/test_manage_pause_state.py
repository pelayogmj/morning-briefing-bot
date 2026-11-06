import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from manage_pause_state import (
    DEFAULT_STATE,
    HELP_TEXT,
    apply_commands,
    is_time_to_send,
    parse_command,
    resolve_effective_timezone,
    should_send,
    validate_send_time,
)


def fake_geocode(place_name):
    """Stub for apply_commands' geocode_fn -- no live network calls."""
    known = {
        "paris": ("Paris", 48.8566, 2.3522, "Europe/Paris"),
        "nowhereville": ("Nowhereville", 0.0, 0.0, None),
    }
    return known.get(place_name.lower())


# -- parse_command -----------------------------------------------------


def test_parse_command_pause_words():
    assert parse_command("stop") == ("pause", None)
    assert parse_command("Pause") == ("pause", None)
    assert parse_command("  STOP  ") == ("pause", None)


def test_parse_command_resume_words():
    assert parse_command("continue") == ("resume", None)
    assert parse_command("Resume") == ("resume", None)
    assert parse_command("start") == ("resume", None)


def test_parse_command_time_set():
    assert parse_command("time 06:00") == ("time_set", "06:00")
    assert parse_command("Time 6:00") == ("time_set", "6:00")


def test_parse_command_timezone_set():
    assert parse_command("timezone Paris") == ("timezone_set", "Paris")
    assert parse_command("Timezone London") == ("timezone_set", "London")


def test_parse_command_timezone_reset():
    assert parse_command("timezone reset") == ("timezone_reset", None)
    assert parse_command("Timezone Reset") == ("timezone_reset", None)


def test_parse_command_time_reset():
    assert parse_command("time reset") == ("time_reset", None)
    assert parse_command("Time Reset") == ("time_reset", None)


def test_parse_command_help_words():
    assert parse_command("help") == ("help", None)
    assert parse_command("HELP") == ("help", None)
    assert parse_command("--help") == ("help", None)
    assert parse_command("-h") == ("help", None)
    assert parse_command("/help") == ("help", None)
    assert parse_command("commands") == ("help", None)
    assert parse_command("?") == ("help", None)


def test_parse_command_unrecognized():
    assert parse_command("hi") == (None, None)
    assert parse_command("stop please") == (None, None)
    assert parse_command("") == (None, None)


# -- validate_send_time -------------------------------------------------


def test_validate_send_time_valid():
    assert validate_send_time("06:00") == "06:00"
    assert validate_send_time("6:00") == "06:00"
    assert validate_send_time("23:59") == "23:59"


def test_validate_send_time_invalid():
    assert validate_send_time("25:00") is None
    assert validate_send_time("06:60") is None
    assert validate_send_time("not a time") is None


# -- apply_commands -------------------------------------------------------


def test_apply_commands_pause_sends_confirmation_once():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(state, ["stop"], fake_geocode)
    assert new_state["paused"] is True
    assert len(confirmations) == 1

    # Already paused -- re-applying "stop" should not re-confirm.
    new_state2, confirmations2 = apply_commands(new_state, ["stop"], fake_geocode)
    assert new_state2["paused"] is True
    assert confirmations2 == []


def test_apply_commands_last_command_wins():
    state = dict(DEFAULT_STATE)
    new_state, _ = apply_commands(state, ["stop", "hi", "continue"], fake_geocode)
    assert new_state["paused"] is False


def test_apply_commands_time_set_valid():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(state, ["time 06:00"], fake_geocode)
    assert new_state["send_time"] == "06:00"
    assert "06:00" in confirmations[0]


def test_apply_commands_time_set_invalid_leaves_state_unchanged():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(state, ["time 99:99"], fake_geocode)
    assert new_state["send_time"] == DEFAULT_STATE["send_time"]
    assert "Couldn't understand" in confirmations[0]


def test_apply_commands_help_sends_help_text_without_changing_state():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(state, ["help"], fake_geocode)
    assert new_state == state
    assert confirmations == [HELP_TEXT]


def test_apply_commands_timezone_set_resolves_via_geocode():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(state, ["timezone Paris"], fake_geocode)
    assert new_state["timezone_override"] == "Europe/Paris"
    assert "Europe/Paris" in confirmations[0]


def test_apply_commands_timezone_set_unresolvable():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(
        state, ["timezone Nonexistentplace"], fake_geocode
    )
    assert new_state["timezone_override"] is None
    assert "Couldn't find" in confirmations[0]


def test_apply_commands_timezone_reset():
    state = {**DEFAULT_STATE, "timezone_override": "Europe/Paris"}
    new_state, confirmations = apply_commands(state, ["timezone reset"], fake_geocode)
    assert new_state["timezone_override"] is None
    assert "automatic" in confirmations[0]


def test_apply_commands_time_reset():
    state = {**DEFAULT_STATE, "send_time": "06:30"}
    new_state, confirmations = apply_commands(state, ["time reset"], fake_geocode)
    assert new_state["send_time"] == DEFAULT_STATE["send_time"]
    assert DEFAULT_STATE["send_time"] in confirmations[0]


def test_apply_commands_ignores_unrecognized_messages():
    state = dict(DEFAULT_STATE)
    new_state, confirmations = apply_commands(
        state, ["good morning", "thanks!"], fake_geocode
    )
    assert new_state == state
    assert confirmations == []


# -- resolve_effective_timezone / is_time_to_send ------------------------


def test_resolve_effective_timezone_override_wins():
    state = {**DEFAULT_STATE, "timezone_override": "Europe/Paris"}
    assert resolve_effective_timezone(state, "Europe/Zurich") == "Europe/Paris"


def test_resolve_effective_timezone_falls_back_to_home():
    state = dict(DEFAULT_STATE)
    assert resolve_effective_timezone(state, "Europe/Zurich") == "Europe/Zurich"


def test_is_time_to_send_matching_hour_not_yet_sent():
    state = {**DEFAULT_STATE, "send_time": "07:00"}
    now = datetime(2026, 11, 5, 7, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    assert is_time_to_send(state, "Europe/Zurich", now=now) is True


def test_is_time_to_send_before_target():
    state = {**DEFAULT_STATE, "send_time": "07:00"}
    now = datetime(2026, 11, 5, 6, 30, tzinfo=ZoneInfo("Europe/Zurich"))
    assert is_time_to_send(state, "Europe/Zurich", now=now) is False


def test_is_time_to_send_catches_up_after_delayed_hour():
    # A run meant for the 07:00 slot can start late (GitHub's scheduled
    # cron is best-effort) -- a later poll the same day, still before
    # any send, must still catch up rather than staying skipped.
    state = {**DEFAULT_STATE, "send_time": "07:00"}
    now = datetime(2026, 11, 5, 10, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    assert is_time_to_send(state, "Europe/Zurich", now=now) is True


def test_is_time_to_send_already_sent_today():
    state = {
        **DEFAULT_STATE,
        "send_time": "07:00",
        "last_sent_date": "2026-11-05",
    }
    now = datetime(2026, 11, 5, 7, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    assert is_time_to_send(state, "Europe/Zurich", now=now) is False


def test_is_time_to_send_new_day_after_last_sent():
    state = {
        **DEFAULT_STATE,
        "send_time": "07:00",
        "last_sent_date": "2026-11-04",
    }
    now = datetime(2026, 11, 5, 7, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    assert is_time_to_send(state, "Europe/Zurich", now=now) is True


def test_is_time_to_send_uses_timezone_override():
    # 07:00 in Zurich (UTC+1) is 06:00 UTC; override to a timezone where
    # the "current" instant (6:00 UTC) is NOT the 07:00 target hour.
    state = {
        **DEFAULT_STATE,
        "send_time": "07:00",
        "timezone_override": "America/New_York",
    }
    now_utc = datetime(2026, 11, 5, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert is_time_to_send(state, "Europe/Zurich", now=now_utc) is False


# -- should_send (the overall SEND/SKIP decision, incl. forced) ---------


def test_should_send_forced_bypasses_hour_and_already_sent_gate():
    state = {
        **DEFAULT_STATE,
        "send_time": "07:00",
        "last_sent_date": "2026-11-05",
    }
    wrong_hour = datetime(2026, 11, 5, 15, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    assert should_send(state, "Europe/Zurich", forced=True, now=wrong_hour) is True


def test_should_send_forced_still_respects_pause():
    state = {**DEFAULT_STATE, "paused": True}
    assert should_send(state, "Europe/Zurich", forced=True) is False


def test_should_send_not_forced_uses_normal_gate():
    state = {**DEFAULT_STATE, "send_time": "07:00"}
    matching_hour = datetime(2026, 11, 5, 7, 0, tzinfo=ZoneInfo("Europe/Zurich"))
    before_target = datetime(2026, 11, 5, 6, 30, tzinfo=ZoneInfo("Europe/Zurich"))
    assert should_send(state, "Europe/Zurich", now=matching_hour) is True
    assert should_send(state, "Europe/Zurich", now=before_target) is False
