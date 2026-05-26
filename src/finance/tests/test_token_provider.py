"""Tests for the opt-in token_provider callback on TokenManager / LS.

Verified League §3.2.3: a configured provider makes a remote server the single
token issuer (this client becomes a pure consumer). With no provider, the
original self-issue path via GenerateToken must be unchanged (backward compat).

Run in the finance package env:
    cd src/finance && poetry run pytest tests/test_token_provider.py -v
"""

import time

import pytest

from programgarden_finance.ls.token_manager import TokenManager


def test_provider_unset_is_backward_compatible(monkeypatch):
    """No provider → token is self-issued via GenerateToken (unchanged path)."""

    class _Block:
        access_token = "ISSUED_TOKEN"
        token_type = "Bearer"
        scope = None
        expires_in = 3600

    class _Resp:
        block = _Block()

    class _Req:
        def req(self):
            return _Resp()

    class _GenOK:
        def token(self, *a, **k):
            return _Req()

    monkeypatch.setattr(
        "programgarden_finance.ls.oauth.generate_token.GenerateToken", _GenOK
    )

    tm = TokenManager(appkey="K", appsecretkey="S")
    assert tm.has_provider() is False
    assert tm.ensure_fresh_token(force_refresh=True) is True
    assert tm.access_token == "ISSUED_TOKEN"


def test_provider_set_skips_self_issue_and_injects(monkeypatch):
    """Provider set → GenerateToken is never constructed; the provided token is
    injected and is_expired() reflects it."""

    class _Boom:
        def __init__(self, *a, **k):
            raise AssertionError("GenerateToken must not be used in provider mode")

    monkeypatch.setattr(
        "programgarden_finance.ls.oauth.generate_token.GenerateToken", _Boom
    )

    calls = {"n": 0}

    def provider():
        calls["n"] += 1
        return (f"SERVER_TOKEN_{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    assert tm.ensure_fresh_token(force_refresh=True) is True
    assert tm.access_token == "SERVER_TOKEN_1"
    assert calls["n"] == 1
    assert tm.is_expired() is False


def test_provider_recalled_on_expiry(monkeypatch):
    monkeypatch.setattr(
        "programgarden_finance.ls.oauth.generate_token.GenerateToken",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no self-issue")),
    )
    calls = {"n": 0}

    def provider():
        calls["n"] += 1
        return (f"T{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.token_provider = provider
    tm.ensure_fresh_token(force_refresh=True)
    assert calls["n"] == 1
    # Simulate the injected token aging out.
    tm.acquired_at = time.time() - 10_000
    assert tm.is_expired() is True
    tm.ensure_fresh_token()
    assert calls["n"] == 2 and tm.access_token == "T2"


@pytest.mark.asyncio
async def test_async_provider(monkeypatch):
    calls = {"n": 0}

    async def aprovider():
        calls["n"] += 1
        return (f"ASYNC_{calls['n']}", time.time() + 3600)

    tm = TokenManager()
    tm.async_token_provider = aprovider
    assert await tm.ensure_fresh_token_async(force_refresh=True) is True
    assert tm.access_token == "ASYNC_1" and calls["n"] == 1


def test_no_provider_no_appkey_returns_false():
    """Unchanged: with neither a provider nor credentials, refresh fails soft."""
    tm = TokenManager()
    assert tm.has_provider() is False
    assert tm._refresh_token() is False
