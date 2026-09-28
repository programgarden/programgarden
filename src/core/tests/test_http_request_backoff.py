"""HTTPRequestNode 외부 API 보호 테스트 (owner 우려 2026-09-28).

- 429 응답 시 `Retry-After` 헤더를 파싱해 예외에 실어 백오프에 반영한다.
- 호스트별 동시성 세마포어(기본 1)는 호스트별로 재사용된다.
"""

import asyncio

import pytest

from programgarden_core.nodes.data import (
    HTTPRequestNode,
    HTTPRateLimitError,
    HTTP_MAX_CONCURRENCY_PER_HOST,
    _host_semaphore,
    _parse_retry_after,
)


# ── _parse_retry_after ──────────────────────────────────────────────────────

def test_parse_retry_after_delta_seconds():
    assert _parse_retry_after("120") == 120.0
    assert _parse_retry_after("0") == 0.0


def test_parse_retry_after_none_and_invalid():
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None
    assert _parse_retry_after("not-a-date") is None
    assert _parse_retry_after("-5") is None  # 음수는 무시


def test_parse_retry_after_http_date_future():
    from email.utils import format_datetime
    from datetime import datetime, timezone, timedelta

    future = datetime.now(timezone.utc) + timedelta(seconds=100)
    val = _parse_retry_after(format_datetime(future))
    assert val is not None and 80 <= val <= 110


# ── per-host concurrency semaphore ──────────────────────────────────────────

def test_host_semaphore_reused_per_host():
    s1 = _host_semaphore("https://api.example.com/a?x=1")
    s2 = _host_semaphore("https://api.example.com/b")   # 같은 호스트
    s3 = _host_semaphore("https://other.example.org/x")  # 다른 호스트
    assert s1 is s2
    assert s1 is not s3
    assert isinstance(s1, asyncio.Semaphore)
    # 기본 상한 == 상수(1)
    assert getattr(s1, "_value", None) == HTTP_MAX_CONCURRENCY_PER_HOST


# ── 429 Retry-After capture (fake aiohttp response sequence) ────────────────

class _FakeResp:
    def __init__(self, status, headers=None, body=None):
        self.status = status
        self.headers = headers or {}
        self._body = body if body is not None else {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("not json")

    async def text(self):
        return str(self._body)


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def request(self, **kwargs):
        return self._resp


@pytest.mark.asyncio
async def test_429_raises_with_retry_after(monkeypatch):
    aiohttp = pytest.importorskip("aiohttp")
    resp = _FakeResp(429, headers={"Retry-After": "42"})
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp))
    node = HTTPRequestNode(id="h", url="https://api.example.com/quote")
    with pytest.raises(HTTPRateLimitError) as ei:
        await node.execute(context=None)
    assert ei.value.retry_after == 42.0


@pytest.mark.asyncio
async def test_429_without_retry_after_header(monkeypatch):
    aiohttp = pytest.importorskip("aiohttp")
    resp = _FakeResp(429, headers={})
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp))
    node = HTTPRequestNode(id="h", url="https://api.example.com/quote")
    with pytest.raises(HTTPRateLimitError) as ei:
        await node.execute(context=None)
    assert ei.value.retry_after is None


@pytest.mark.asyncio
async def test_200_success_returns_response(monkeypatch):
    aiohttp = pytest.importorskip("aiohttp")
    resp = _FakeResp(200, body={"price": 189.2})
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp))
    node = HTTPRequestNode(id="h", url="https://api.example.com/quote")
    out = await node.execute(context=None)
    assert out["success"] is True
    assert out["status_code"] == 200
    assert out["response"] == {"price": 189.2}


@pytest.mark.asyncio
async def test_4xx_returns_failure_without_raising(monkeypatch):
    aiohttp = pytest.importorskip("aiohttp")
    resp = _FakeResp(404, body={"error": "not found"})
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: _FakeSession(resp))
    node = HTTPRequestNode(id="h", url="https://api.example.com/quote")
    out = await node.execute(context=None)
    assert out["success"] is False
    assert out["status_code"] == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("dry_run,retry_after", [(False, 120), (True, 10)])
async def test_retry_after_over_budget_makes_exactly_one_request(monkeypatch, dry_run, retry_after):
    """Exercise the HTTP adapter and retry executor together, without network I/O."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from programgarden_core.retry_executor import RetryExecutor

    aiohttp = pytest.importorskip("aiohttp")
    requests = []

    class Session(_FakeSession):
        def request(self, **kwargs):
            requests.append(kwargs)
            return super().request(**kwargs)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kw: Session(
        _FakeResp(429, headers={"Retry-After": str(retry_after)})))
    sleep = AsyncMock()
    monkeypatch.setattr("programgarden_core.retry_executor.asyncio.sleep", sleep)
    node = HTTPRequestNode(id="rate_limited", url="https://api.example.com/estimates")
    context = SimpleNamespace(is_dry_run=dry_run)
    with pytest.raises(HTTPRateLimitError) as error:
        await RetryExecutor().execute_with_retry(node, lambda: node.execute(context), context)
    assert error.value.retry_after == retry_after
    assert len(requests) == 1
    sleep.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("dry_run,retry_after", [(False, 30), (True, 5)])
async def test_retry_at_budget_boundary_waits_before_second_request(monkeypatch, dry_run, retry_after):
    from types import SimpleNamespace
    from programgarden_core.retry_executor import RetryExecutor

    aiohttp = pytest.importorskip("aiohttp")
    events = []
    responses = iter([_FakeResp(429, headers={"Retry-After": str(retry_after)}),
                      _FakeResp(200, body={"price": 189.2})])

    class Session(_FakeSession):
        def request(self, **kwargs):
            events.append("request")
            return super().request(**kwargs)

    async def sleep(delay):
        events.append(("wait", delay))

    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kw: Session(next(responses)))
    monkeypatch.setattr("programgarden_core.retry_executor.asyncio.sleep", sleep)
    node = HTTPRequestNode(id="rate_limited", url="https://api.example.com/estimates")
    context = SimpleNamespace(is_dry_run=dry_run)
    result = await RetryExecutor().execute_with_retry(node, lambda: node.execute(context), context)
    assert result["success"] is True
    assert events == ["request", ("wait", retry_after), "request"]
