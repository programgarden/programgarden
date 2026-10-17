"""Opt-in replay transport for offline validation. Off unless a caller installs one.

A validation worker that has no network and no credentials can answer LS REST
TRs from recorded HTTP answers, so the real TR parsers and the engine's node
code run unchanged on scenario data. Nothing here acts unless a caller enters
``use_replay_transport(transport)``. The transport lives in a ``ContextVar``:
only the task that installed it (and tasks it creates while it is installed)
sees it; other tasks in the same event loop keep the real network path.

While a transport is installed:

- ``TRRequestAbstract.execute_async_with_session`` / ``execute_sync`` hand the
  request (header without ``authorization``, JSON body) to
  ``transport.answer(tr_cd, url, header, body)`` and return its
  ``(status, json, headers)`` answer. No socket is opened and no rate-limit
  wait happens;
- OAuth token issuance (``Token.req`` / ``req_async``) is refused;
- ``GenericTR`` does not retry transient failures and never force-reissues a
  token.

``transport.answer`` raises to refuse a call (for example an order TR or a TR
that has no recorded answer). An optional ``transport.refused(kind, detail)``
is told about refused token issuance.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from copy import deepcopy
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional, Tuple

__all__ = [
    "ReplayTransportRefused",
    "ReplayHTTPResponse",
    "active_transport",
    "use_replay_transport",
    "answer_request",
    "notify_refused",
    "replay_client",
]


class ReplayTransportRefused(RuntimeError):
    """A call the installed replay transport does not perform."""


_ACTIVE: ContextVar[Optional[Any]] = ContextVar("programgarden_finance_replay_transport", default=None)


def active_transport() -> Optional[Any]:
    """The transport installed for the current task, or ``None`` (the default)."""
    return _ACTIVE.get()


@contextmanager
def use_replay_transport(transport: Any) -> Iterator[Any]:
    """Answer LS REST TRs of the current task from ``transport`` inside the block."""
    if transport is None or not callable(getattr(transport, "answer", None)):
        raise TypeError("a replay transport needs an answer(tr_cd, url, header, body) method")
    token = _ACTIVE.set(transport)
    try:
        yield transport
    finally:
        _ACTIVE.reset(token)


class ReplayHTTPResponse:
    """The attributes TR response builders and evidence readers use on a response.

    ``json()`` returns a copy of the recorded body, as ``requests.Response.json``
    does (some readers re-read the raw body to tell omitted blocks from defaults).
    """

    reason = "replay"

    def __init__(self, status: int, headers: Dict[str, Any], payload: Any = None):
        self.status = self.status_code = int(status)
        self.headers = dict(headers)
        self._payload = payload

    def json(self) -> Any:
        return deepcopy(self._payload)

    @property
    def text(self) -> str:
        return json.dumps(self._payload, ensure_ascii=False)

    def raise_for_status(self) -> None:  # builders read ``status`` themselves
        return None


def answer_request(tr: Any, url: str, request_data: Any) -> Tuple[ReplayHTTPResponse, Dict[str, Any], Dict[str, Any]]:
    """Answer one TR request from the installed transport (called by ``tr_base``)."""
    transport = _ACTIVE.get()
    if transport is None:
        raise ReplayTransportRefused("no replay transport is installed")
    header = request_data.header.model_dump(by_alias=True)
    header.pop("authorization", None)  # a transport never sees a bearer token
    body = tr._build_json_body(request_data)
    status, payload, headers = transport.answer(str(header.get("tr_cd") or ""), url, header, body)
    headers = dict(headers or {})
    return ReplayHTTPResponse(status, headers, payload), payload, headers


def notify_refused(kind: str, detail: str) -> None:
    """Tell the installed transport that ``kind`` (e.g. ``"token"``) was refused."""
    transport = _ACTIVE.get()
    callback = getattr(transport, "refused", None)
    if callable(callback):
        callback(kind, detail)


def replay_client(paper_trading: bool) -> Any:
    """An LS client for replay: a placeholder unexpired token, no provider, no login.

    It is a fresh instance (never the process-wide singleton), so nothing a
    replay does changes a live client. Its token text is a fixed placeholder;
    the transport never receives it.
    """
    from programgarden_finance.ls import LS
    from programgarden_finance.ls.token_manager import TokenManager

    client = object.__new__(LS)
    client.__init__()
    client.token_manager = TokenManager(
        appkey="REPLAY", appsecretkey="", access_token="replay-placeholder", token_type="Bearer",
        expires_in=86_400, acquired_at=time.time(), paper_trading=bool(paper_trading),
    )
    return client
