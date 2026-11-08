"""Shared Google OAuth helper for tools that need direct Calendar/Gmail API access.

Separate from any MCP server setup: this is what an unattended script (no
interactive Claude Code session to broker tool calls) authenticates with.
"""

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"

# All scopes any tool in this project needs, requested together in one
# consent so every tool can reuse the same cached token.json. A script
# requesting only its own narrower scope would silently share (and corrupt
# the usability of) a token.json authorized for a different, disjoint scope.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]


def get_credentials(scopes):
    """Return valid Credentials for the given OAuth scopes.

    Reuses a cached token.json, refreshing it if expired. On first-ever run
    (no token yet) this opens a browser for one-time interactive consent --
    must be run by a human, not from an unattended/headless context.
    """
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
        return creds

    if not CREDENTIALS_PATH.exists():
        print(
            f"Error: {CREDENTIALS_PATH.name} not found. Download an OAuth "
            "client (type: Desktop app) from Google Cloud Console and save "
            f"it as {CREDENTIALS_PATH}.",
            file=sys.stderr,
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), scopes)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return creds
