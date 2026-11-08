import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from get_tasks import format_tasks_summary, is_todo_list_title, parse_tasks


# -- is_todo_list_title --------------------------------------------------


def test_is_todo_list_title_matches_various_spellings():
    assert is_todo_list_title("TODOs") is True
    assert is_todo_list_title("To-Do List") is True
    assert is_todo_list_title("to do") is True
    assert is_todo_list_title("ToDo") is True


def test_is_todo_list_title_rejects_unrelated_list():
    assert is_todo_list_title("Groceries") is False


# -- parse_tasks ----------------------------------------------------------


def test_parse_tasks_extracts_title_and_due_date():
    items = [{"title": "Renew passport", "due": "2026-11-05T00:00:00.000Z"}]
    assert parse_tasks(items) == [{"title": "Renew passport", "due": date(2026, 11, 5)}]


def test_parse_tasks_handles_missing_due():
    items = [{"title": "Buy milk"}]
    assert parse_tasks(items) == [{"title": "Buy milk", "due": None}]


def test_parse_tasks_defaults_missing_title():
    items = [{"due": "2026-11-05T00:00:00.000Z"}]
    assert parse_tasks(items) == [{"title": "(no title)", "due": date(2026, 11, 5)}]


# -- format_tasks_summary --------------------------------------------------

TODAY = date(2026, 11, 5)


def test_format_tasks_summary_bullets_due_today():
    tasks = [{"title": "Submit report", "due": TODAY}]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "Today's tasks are:\n• Submit report"
    )


def test_format_tasks_summary_labels_overdue():
    tasks = [{"title": "Call dentist", "due": date(2026, 11, 2)}]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "Today's tasks are:\n• Call dentist (due 2026-11-02, overdue)"
    )


def test_format_tasks_summary_mixes_overdue_and_due_today_sorted():
    tasks = [
        {"title": "Submit report", "due": TODAY},
        {"title": "Call dentist", "due": date(2026, 11, 2)},
    ]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "Today's tasks are:\n"
        "• Call dentist (due 2026-11-02, overdue)\n"
        "• Submit report"
    )


def test_format_tasks_summary_excludes_future_dated_task():
    tasks = [{"title": "Plan trip", "due": date(2026, 12, 1)}]
    assert format_tasks_summary(tasks, today=TODAY) == "No tasks today. Your to-do list is clear!"


def test_format_tasks_summary_dateless_open_items_singular():
    tasks = [{"title": "Read a book", "due": None}]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "No tasks today. You still have 1 open item on your to-do "
        "list — it's a good day to tick them off!"
    )


def test_format_tasks_summary_dateless_open_items_plural():
    tasks = [
        {"title": "Read a book", "due": None},
        {"title": "Clean garage", "due": None},
        {"title": "Learn guitar", "due": None},
    ]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "No tasks today. You still have 3 open items on your to-do "
        "list — it's a good day to tick them off!"
    )


def test_format_tasks_summary_future_task_excluded_from_dateless_count():
    tasks = [
        {"title": "Read a book", "due": None},
        {"title": "Plan trip", "due": date(2026, 12, 1)},
    ]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "No tasks today. You still have 1 open item on your to-do "
        "list — it's a good day to tick them off!"
    )


def test_format_tasks_summary_due_today_takes_priority_over_dateless():
    tasks = [
        {"title": "Submit report", "due": TODAY},
        {"title": "Read a book", "due": None},
    ]
    assert format_tasks_summary(tasks, today=TODAY) == (
        "Today's tasks are:\n• Submit report"
    )


def test_format_tasks_summary_all_clear():
    assert format_tasks_summary([], today=TODAY) == "No tasks today. Your to-do list is clear!"
