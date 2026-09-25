"""Authenticate with Google OAuth for Docs and Drive (drive.file) scopes.

Loads the desktop OAuth client from ~/.google-cli-credentials/credentials.json,
opens the system browser for consent, and saves the token to
~/.google-cli-credentials/token.json. Refreshes an existing token when possible.
"""

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

CRED_DIR = Path.home() / ".google-cli-credentials"
CRED_FILE = CRED_DIR / "credentials.json"
TOKEN_FILE = CRED_DIR / "token.json"


def authenticate():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CRED_FILE.exists():
            print(f"OAuth client not found at {CRED_FILE}", file=sys.stderr)
            sys.exit(1)
        flow = InstalledAppFlow.from_client_secrets_file(str(CRED_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")


if __name__ == "__main__":
    authenticate()
