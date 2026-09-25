"""Create a Google Doc with a title and body from a text file.

Usage:
    python scripts/create_google_doc.py --title "Doc Title" --body working/body.txt
"""

import argparse
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_FILE = Path.home() / ".google-cli-credentials" / "token.json"


def load_credentials():
    if not TOKEN_FILE.exists():
        print(f"Token not found at {TOKEN_FILE}. Run google_docs_auth.py first.",
              file=sys.stderr)
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds.valid:
        print("Token is invalid or expired. Run google_docs_auth.py again.",
              file=sys.stderr)
        sys.exit(1)
    return creds


def create_doc(title, body):
    creds = load_credentials()
    docs_service = build("docs", "v1", credentials=creds)

    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if body:
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": body}}]},
        ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"Title: {title}")
    print(f"URL:   {url}")
    return url


def main():
    parser = argparse.ArgumentParser(description="Create a Google Doc")
    parser.add_argument("--title", required=True, help="Document title")
    parser.add_argument("--body", required=True, help="Path to a UTF-8 text file with the body")
    args = parser.parse_args()

    body_path = Path(args.body)
    if not body_path.exists():
        print(f"Body file not found: {body_path}", file=sys.stderr)
        sys.exit(1)

    body_text = body_path.read_text(encoding="utf-8")
    create_doc(args.title, body_text)


if __name__ == "__main__":
    main()
