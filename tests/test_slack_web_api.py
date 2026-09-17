import io
import json
from urllib.error import HTTPError

import pytest

from scripts.slack_web_api import SlackApiError, api_call, post_message, resolve_channel


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_api_call_never_places_token_in_url_or_body():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse({"ok": True, "team": "AI Analyst Lab"})

    result = api_call("auth.test", "xoxp-test", opener=opener)

    assert result["ok"] is True
    assert "xoxp-test" not in captured["url"]
    assert "xoxp-test" not in captured["body"]
    assert captured["authorization"] == "Bearer xoxp-test"


def test_api_call_honors_retry_after_once():
    calls = 0
    waits = []

    def opener(_request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise HTTPError(
                "https://slack.com/api/auth.test",
                429,
                "rate limited",
                {"Retry-After": "2"},
                io.BytesIO(b""),
            )
        return FakeResponse({"ok": True})

    assert api_call("auth.test", "xoxp-test", opener=opener, sleep=waits.append)["ok"]
    assert waits == [2]


def test_resolve_channel_pages_and_checks_expected_id(monkeypatch):
    replies = iter(
        [
            {"ok": True, "channels": [], "response_metadata": {"next_cursor": "page-2"}},
            {
                "ok": True,
                "channels": [{"name": "show-and-tell", "id": "C0ACN1QM0RL"}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
    )
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C0ACN1QM0RL")
    monkeypatch.setattr("scripts.slack_web_api.api_call", lambda *_args, **_kwargs: next(replies))

    assert resolve_channel("xoxp-test", "show-and-tell") == {
        "channel": "show-and-tell",
        "channel_id": "C0ACN1QM0RL",
    }


def test_resolve_channel_rejects_wrong_channel_id(monkeypatch):
    monkeypatch.setenv("SLACK_CHANNEL_ID", "EXPECTED")
    monkeypatch.setattr(
        "scripts.slack_web_api.api_call",
        lambda *_args, **_kwargs: {
            "ok": True,
            "channels": [{"name": "show-and-tell", "id": "WRONG"}],
            "response_metadata": {"next_cursor": ""},
        },
    )

    with pytest.raises(SlackApiError, match="does not match"):
        resolve_channel("xoxp-test", "show-and-tell")


def test_post_message_returns_permalink(monkeypatch):
    replies = iter(
        [
            {"ok": True, "channel": "C0ACN1QM0RL", "ts": "123.456"},
            {"ok": True, "permalink": "https://example.slack.com/archives/C0ACN1QM0RL/p123456"},
        ]
    )
    monkeypatch.setattr("scripts.slack_web_api.api_call", lambda *_args, **_kwargs: next(replies))

    assert post_message("xoxp-test", "C0ACN1QM0RL", "hello") == {
        "channel_id": "C0ACN1QM0RL",
        "timestamp": "123.456",
        "permalink": "https://example.slack.com/archives/C0ACN1QM0RL/p123456",
    }


def test_post_message_preserves_timestamp_when_permalink_fails(monkeypatch):
    replies = iter(
        [
            {"ok": True, "channel": "C0ACN1QM0RL", "ts": "123.456"},
            SlackApiError("Slack returned internal_error for chat.getPermalink."),
        ]
    )

    def fake_call(*_args, **_kwargs):
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr("scripts.slack_web_api.api_call", fake_call)
    result = post_message("xoxp-test", "C0ACN1QM0RL", "hello")

    assert result["timestamp"] == "123.456"
    assert result["permalink"] == ""
    assert "chat.getPermalink" in result["permalink_error"]
