"""Credential selection tests for the Snowflake setup validator."""

from scripts import validate_snowflake_setup as validator


def _base_env(monkeypatch):
    values = {
        "SNOWFLAKE_ACCOUNT": "ORG-ACCOUNT",
        "SNOWFLAKE_USER": "COURSE_AGENT",
        "SNOWFLAKE_WAREHOUSE": "COURSE_WH",
        "SNOWFLAKE_DATABASE": "COURSE_DB",
        "SNOWFLAKE_ROLE": "COURSE_READER",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_validator_builds_explicit_pat_kwargs(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("SNOWFLAKE_AUTHENTICATOR", "programmatic_access_token")
    monkeypatch.setenv("SNOWFLAKE_TOKEN", "secret-token")
    monkeypatch.delenv("SNOWFLAKE_PASSWORD", raising=False)

    kwargs = validator.snowflake_connect_kwargs(schema="NOVAMART")

    assert kwargs["authenticator"] == "PROGRAMMATIC_ACCESS_TOKEN"
    assert kwargs["token"] == "secret-token"
    assert kwargs["schema"] == "NOVAMART"
    assert "password" not in kwargs


def test_validator_keeps_password_kwargs(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("SNOWFLAKE_AUTHENTICATOR", "password")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "legacy-secret")
    monkeypatch.delenv("SNOWFLAKE_TOKEN", raising=False)

    kwargs = validator.snowflake_connect_kwargs()

    assert kwargs["password"] == "legacy-secret"
    assert "authenticator" not in kwargs
    assert "token" not in kwargs


def test_validator_accepts_auth_method_alias(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.delenv("SNOWFLAKE_AUTHENTICATOR", raising=False)
    monkeypatch.setenv("SNOWFLAKE_AUTH_METHOD", "pat")
    monkeypatch.setenv("SNOWFLAKE_TOKEN", "secret-token")
    monkeypatch.delenv("SNOWFLAKE_PASSWORD", raising=False)

    assert validator.check_env_vars() is True
    assert validator.snowflake_connect_kwargs()["token"] == "secret-token"
