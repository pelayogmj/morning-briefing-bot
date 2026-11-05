"""Send a plain-text message to a Telegram chat via the Bot API.

Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment
(set via .env locally, or as GitHub Actions secrets in automation).
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def send_message(text, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        # Telegram's error body (e.g. "chat not found", "message is too
        # long") is far more useful than requests' generic "400 Client
        # Error" -- surface it instead of swallowing it.
        raise requests.exceptions.HTTPError(
            f"{exc} -- Telegram response: {response.text}", response=response
        ) from exc
    return response.json()


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print(
            "Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set",
            file=sys.stderr,
        )
        sys.exit(1)

    text = sys.stdin.read().strip()
    if not text:
        print("Error: no message text provided on stdin", file=sys.stderr)
        sys.exit(1)

    try:
        send_message(text, bot_token, chat_id)
    except requests.RequestException as exc:
        print(f"Error: could not send Telegram message ({exc})", file=sys.stderr)
        sys.exit(1)

    print("Sent.")


if __name__ == "__main__":
    main()
