import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from get_gmail import format_inbox_summary, parse_unread_messages


def test_parse_unread_messages_display_name_and_bare_address():
    messages = [
        {
            "snippet": "Please find attached the invoice for...",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Invoice due"},
                    {"name": "From", "value": "Jane Doe <jane@example.com>"},
                ]
            },
        },
        {
            "snippet": "This is a reminder that your subscription...",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Reminder"},
                    {"name": "From", "value": "noreply@example.com"},
                ]
            },
        },
    ]
    assert parse_unread_messages(messages) == [
        {
            "subject": "Invoice due",
            "sender": "Jane Doe",
            "snippet": "Please find attached the invoice for...",
        },
        {
            "subject": "Reminder",
            "sender": "noreply@example.com",
            "snippet": "This is a reminder that your subscription...",
        },
    ]


def test_parse_unread_messages_missing_headers():
    messages = [{"payload": {"headers": []}}]
    assert parse_unread_messages(messages) == [
        {"subject": "(no subject)", "sender": "(unknown sender)", "snippet": ""}
    ]


def test_format_inbox_summary_populated():
    messages = [
        {"subject": "Invoice due", "sender": "Jane Doe", "snippet": "Please find attached..."},
        {"subject": "Reminder", "sender": "noreply@example.com", "snippet": ""},
    ]
    assert format_inbox_summary(messages) == (
        "Top unread emails:\n"
        "  1. Invoice due — Jane Doe\n"
        "     Please find attached...\n"
        "  2. Reminder — noreply@example.com"
    )


def test_format_inbox_summary_empty():
    assert format_inbox_summary([]) == "No unread messages."
