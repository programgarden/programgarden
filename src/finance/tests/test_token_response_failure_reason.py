"""A failed token request keeps its reason.

``Token.req`` / ``req_async`` always built ``TokenResponse(..., error_msg=str(e))`` on failure,
but the model had no such field, so pydantic dropped it: callers saw ``header=None, block=None``
and nothing else. A chatbot built on the SDK told a user whose app key LS had REFUSED
(HTTP 403, ``IGW00103 유효하지 않은 AppKey입니다.``) that the login failed "for an unknown reason,
try again shortly" (observed 2026-09-18/19).
"""
from __future__ import annotations

import asyncio

import pytest
import requests

from programgarden_finance.ls.oauth.generate_token import GenerateToken, TokenInBlock
from programgarden_finance.ls.oauth.generate_token.token import blocks
from programgarden_finance.ls.oauth.generate_token.token.blocks import TokenResponse

REFUSED_BODY = '{"error_description": "유효하지 않은 AppKey입니다.", "error_code": "IGW00103"}'
ISSUED_BODY = {"access_token": "tok", "expires_in": 3600, "scope": "oob", "token_type": "Bearer"}


def _request():
    return GenerateToken().token(TokenInBlock(appkey="k", appsecretkey="s"))


def test_the_model_keeps_the_failure_fields():
    resp = TokenResponse(header=None, block=None, status_code=403, error_msg="HTTP 403 Forbidden",
                         error_code="IGW00103", error_description="유효하지 않은 AppKey입니다.")
    assert (resp.status_code, resp.error_code) == (403, "IGW00103")
    assert resp.error_msg == "HTTP 403 Forbidden"
    assert resp.error_description == "유효하지 않은 AppKey입니다."


def test_a_successful_response_has_no_error():
    resp = TokenResponse(header=None, block=None)
    assert resp.error_msg is None and resp.status_code is None and resp.error_code is None


class _SyncResponse:
    def __init__(self, status, text="", payload=None, reason="Forbidden"):
        self.status_code, self.text, self.reason = status, text, reason
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._payload


def test_sync_refusal_carries_status_and_ls_reason(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda **_k: _SyncResponse(403, REFUSED_BODY))
    resp = _request().req()
    assert resp.block is None
    assert resp.status_code == 403
    assert resp.error_code == "IGW00103"
    assert resp.error_description == "유효하지 않은 AppKey입니다."
    assert resp.error_msg.startswith("HTTP 403") and "IGW00103" in resp.error_msg


def test_sync_non_json_error_body_is_kept_short(monkeypatch):
    monkeypatch.setattr(requests, "post",
                        lambda **_k: _SyncResponse(502, "<html>" + "x" * 5000, reason="Bad Gateway"))
    resp = _request().req()
    assert resp.status_code == 502 and resp.error_code is None
    assert resp.error_msg.startswith("HTTP 502 Bad Gateway: <html>")
    assert len(resp.error_msg) < 400


def test_sync_connection_failure_keeps_its_message(monkeypatch):
    def boom(**_k):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", boom)
    resp = _request().req()
    assert resp.status_code is None, "the server was never reached"
    assert "connection refused" in resp.error_msg


def test_sync_success_reports_the_status(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda **_k: _SyncResponse(200, payload=ISSUED_BODY, reason="OK"))
    resp = _request().req()
    assert resp.block.access_token == "tok" and resp.status_code == 200 and resp.error_msg is None


class _AsyncResponse:
    def __init__(self, status, text="", payload=None, reason="Forbidden"):
        self.status, self._text, self.reason, self._payload = status, text, reason, payload
        self.headers = {"Content-Type": "application/json"}

    async def text(self):
        return self._text

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False


class _AsyncSession:
    def __init__(self, response):
        self._response = response

    def post(self, **_k):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False


def _patch_aiohttp(monkeypatch, response):
    import programgarden_finance.ls.oauth.generate_token.token as token_module

    monkeypatch.setattr(token_module.aiohttp, "ClientSession", lambda *a, **k: _AsyncSession(response))


def test_async_refusal_carries_status_and_ls_reason(monkeypatch):
    _patch_aiohttp(monkeypatch, _AsyncResponse(403, REFUSED_BODY))
    resp = asyncio.run(_request().req_async())
    assert (resp.status_code, resp.error_code) == (403, "IGW00103")
    assert resp.error_description == "유효하지 않은 AppKey입니다."


def test_async_success_reports_the_status(monkeypatch):
    _patch_aiohttp(monkeypatch, _AsyncResponse(200, payload=ISSUED_BODY, reason="OK"))
    resp = asyncio.run(_request().req_async())
    assert resp.block.access_token == "tok" and resp.status_code == 200 and resp.error_msg is None


def test_only_the_two_ls_fields_are_lifted_from_an_error_body(monkeypatch):
    """Nothing else from the body is copied — it could echo request data."""
    body = '{"error_code": "X1", "error_description": "bad", "appkey": "SECRET-KEY-VALUE"}'
    monkeypatch.setattr(requests, "post", lambda **_k: _SyncResponse(400, body, reason="Bad Request"))
    resp = _request().req()
    assert "SECRET-KEY-VALUE" not in (resp.error_msg or "")
    assert blocks.TokenResponse.model_fields.keys() >= {"status_code", "error_msg", "error_code", "error_description"}
