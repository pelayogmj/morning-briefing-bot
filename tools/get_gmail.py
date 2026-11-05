"""Print the top unread emails (subject + sender) via direct Gmail API access."""

import os
import sys
from email.utils import parseaddr
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

from google_auth import SCOPES, get_credentials

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIMIT = 5


def parse_unread_messages(messages):
    """Extract {subject, sender, snippet} from raw Gmail API message resources.

    `snippet` is a short plain-text preview Gmail generates itself; it's
    already present in a `format=metadata` response, no extra scope or API
    call needed.
    """
    parsed = []
    for message in messages:
        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }
        subject = headers.get("Subject", "(no subject)")
        from_header = headers.get("From")
        if from_header:
            display_name, address = parseaddr(from_header)
            sender = display_name if display_name else address
        else:
            sender = "(unknown sender)"
        parsed.append(
            {
                "subject": subject,
                "sender": sender,
                "snippet": message.get("snippet", ""),
            }
        )
    return parsed


def format_inbox_summary(messages):
    if not messages:
        return "No unread messages."
    lines = ["Top unread emails:"]
    for i, message in enumerate(messages, start=1):
        lines.append(f"  {i}. {message['subject']} — {message['sender']}")
        if message["snippet"]:
            lines.append(f"     {message['snippet']}")
    return "\n".join(lines)


def fetch_top_unread(limit=DEFAULT_LIMIT):
    creds = get_credentials(SCOPES)
    service = build("gmail", "v1", credentials=creds)

    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["UNREAD", "INBOX"], maxResults=limit)
        .execute()
    )
    message_refs = results.get("messages", [])

    messages = []
    for ref in message_refs:
        full_message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=["Subject", "From"],
            )
            .execute()
        )
        messages.append(full_message)
    return messages


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv(PROJECT_ROOT / ".env")
    limit = int(os.environ.get("EMAIL_COUNT", DEFAULT_LIMIT))

    try:
        messages = fetch_top_unread(limit)
    except Exception as exc:
        print(f"Error: could not fetch Gmail messages ({exc})", file=sys.stderr)
        sys.exit(1)

    print(format_inbox_summary(parse_unread_messages(messages)))


if __name__ == "__main__":
    main()
