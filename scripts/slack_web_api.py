#!/usr/bin/env python3
"""Verify a Slack user connection and send one explicitly approved message."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv


SLACK_API = "https://slack.com/api"
DEFAULT_TIMEOUT_SECONDS = 30


class SlackApiError(RuntimeError):
    """A safe-to-display Slack API failure."""


def api_call(
    method: str,
    token: str,
    params: dict[str, Any] | None = None,
    *,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Call one Slack Web API method without ever returning or printing the token."""
    body = urlencode(params or {}).encode("utf-8")
    request = Request(
        f"{SLACK_API}/{method}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ai-analyst-slack-helper/1.0",
        },
        method="POST",
    )

    for attempt in range(2):
        try:
            with opener(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt == 0:
                wait_seconds = max(int(exc.headers.get("Retry-After", "1")), 1)
                sleep(wait_seconds)
                continue
            raise SlackApiError(f"Slack returned HTTP {exc.code} for {method}.") from exc
        except (URLError, TimeoutError) as exc:
            raise SlackApiError(
                f"The request to Slack did not complete for {method}. No automatic write retry was attempted."
            ) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SlackApiError(f"Slack returned an unreadable response for {method}.") from exc

        if not payload.get("ok"):
            raise SlackApiError(f"Slack returned {payload.get('error', 'unknown_error')} for {method}.")
        return payload

    raise SlackApiError(f"Slack rate-limited {method} twice. Wait before trying again.")


def require_token() -> str:
    load_dotenv()
    token = os.getenv("SLACK_USER_TOKEN", "").strip()
    if not token:
        raise SlackApiError("SLACK_USER_TOKEN is missing from .env.")
    if not token.startswith("xoxp-"):
        raise SlackApiError("SLACK_USER_TOKEN is not a Slack user token beginning with xoxp-.")
    return token


def verify_identity(token: str) -> dict[str, str]:
    result = api_call("auth.test", token)
    identity = {
        "workspace": str(result.get("team", "")),
        "workspace_id": str(result.get("team_id", "")),
        "user": str(result.get("user", "")),
        "user_id": str(result.get("user_id", "")),
        "workspace_url": str(result.get("url", "")),
    }
    expected_team_id = os.getenv("SLACK_WORKSPACE_ID", "").strip()
    if expected_team_id and identity["workspace_id"] != expected_team_id:
        raise SlackApiError(
            "Slack authenticated successfully, but the token belongs to a different workspace."
        )
    return identity


def resolve_channel(token: str, channel_name: str) -> dict[str, str]:
    cursor = ""
    while True:
        params = {"types": "public_channel", "exclude_archived": "true", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        result = api_call("conversations.list", token, params)
        for channel in result.get("channels", []):
            if channel.get("name") == channel_name:
                resolved = {
                    "channel": str(channel.get("name", "")),
                    "channel_id": str(channel.get("id", "")),
                }
                expected_channel_id = os.getenv("SLACK_CHANNEL_ID", "").strip()
                if expected_channel_id and resolved["channel_id"] != expected_channel_id:
                    raise SlackApiError(
                        "Slack found the channel name, but its id does not match SLACK_CHANNEL_ID."
                    )
                return resolved
        cursor = str(result.get("response_metadata", {}).get("next_cursor", "")).strip()
        if not cursor:
            break
    raise SlackApiError(f"Slack could not find the public channel named {channel_name}.")


def post_message(token: str, channel_id: str, message: str) -> dict[str, str]:
    result = api_call("chat.postMessage", token, {"channel": channel_id, "text": message})
    timestamp = str(result.get("ts", ""))
    posted = {
        "channel_id": str(result.get("channel", channel_id)),
        "timestamp": timestamp,
    }
    try:
        permalink_result = api_call(
            "chat.getPermalink",
            token,
            {"channel": channel_id, "message_ts": timestamp},
        )
        posted["permalink"] = str(permalink_result.get("permalink", ""))
    except SlackApiError as exc:
        posted["permalink"] = ""
        posted["permalink_error"] = str(exc)
    return posted


def read_message(path: str) -> str:
    message = Path(path).read_text(encoding="utf-8").strip()
    if not message:
        raise SlackApiError("The message file is empty.")
    return message


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("verify", help="Verify the Slack workspace and user.")

    resolve = commands.add_parser("resolve", help="Resolve one public channel name.")
    resolve.add_argument("--channel-name", default=os.getenv("SLACK_CHANNEL_NAME", "show-and-tell"))

    preview = commands.add_parser("preview", help="Print the exact message that would be sent.")
    preview.add_argument("--message-file", required=True)

    post = commands.add_parser("post", help="Post one approved message and return its permalink.")
    post.add_argument("--channel-id", default=os.getenv("SLACK_CHANNEL_ID", ""))
    post.add_argument("--message-file", required=True)
    post.add_argument(
        "--send",
        action="store_true",
        help="Required acknowledgement that the preview was approved.",
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "preview":
            print(read_message(args.message_file))
            return 0

        token = require_token()
        if args.command == "verify":
            print(json.dumps(verify_identity(token), indent=2))
            return 0

        if args.command == "resolve":
            verify_identity(token)
            print(json.dumps(resolve_channel(token, args.channel_name), indent=2))
            return 0

        if args.command == "post":
            if not args.send:
                raise SlackApiError("Refusing to post without --send after an explicit preview approval.")
            if not args.channel_id:
                raise SlackApiError("Provide --channel-id or set SLACK_CHANNEL_ID in .env.")
            verify_identity(token)
            channel_name = os.getenv("SLACK_CHANNEL_NAME", "show-and-tell").strip()
            resolved = resolve_channel(token, channel_name)
            if resolved["channel_id"] != args.channel_id:
                raise SlackApiError("The approved channel id does not match the resolved channel.")
            print(json.dumps(post_message(token, args.channel_id, read_message(args.message_file)), indent=2))
            return 0
    except SlackApiError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
