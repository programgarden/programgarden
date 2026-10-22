"""Offline parser + asyncio Future matching test for CSPAT00601 + SC1 flow.

EN:
    Validates the OrdNo-matching pattern from
    example/korea_stock/run_CSPAT00601_with_SC1.py without a WebSocket. Three
    layers verified:
      1. SC1RealResponseBody Pydantic parse on a synthetic payload (full fill,
         partial fill, rejection).
      2. OrdNo type-cast contract: CSPAT00601 block2.OrdNo (int) ↔ SC1 body.ordno
         (str). Direct equality fails — str() cast required.
      3. asyncio.Future resolution lifecycle: partial fills accumulate, full
         fill (unercqty == "0") resolves the future, rejection
         (ordxctptncode == "14") sets an exception.

    No live LS connection, no WebSocket frame parsing. Live end-to-end
    verification must happen during market hours (09:00–15:30 KST).

KO:
    실전 라이브 수신 없이 CSPAT00601 + SC1 매칭 패턴의 파서/로직 부분만
    검증합니다. 장 마감 시간대(저녁) 검증 용도. 실라이브 end-to-end 검증은
    장중에 별도 수행 필요.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from programgarden_finance.ls.korea_stock.real.SC1.blocks import (
    SC1RealResponse,
    SC1RealResponseBody,
)


def _sc1_body_dict(**overrides: Any) -> Dict[str, str]:
    """Build a complete SC1RealResponseBody-shaped dict.

    All 133 fields are required `str`; default to "" and apply overrides for
    the fields the test actually inspects.
    """
    base = {name: "" for name in SC1RealResponseBody.model_fields}
    base.update({k: str(v) for k, v in overrides.items()})
    return base


def _make_sc1_response(**overrides: Any) -> SC1RealResponse:
    body = SC1RealResponseBody.model_validate(_sc1_body_dict(**overrides))
    return SC1RealResponse(
        header=None,
        body=body,
        rsp_cd="00000",
        rsp_msg="정상처리되었습니다.",
    )


# ---------------------------------------------------------------------------
# Layer 1 — Pydantic parser
# ---------------------------------------------------------------------------


def test_sc1_body_parses_full_fill_payload():
    """Synthetic full-fill payload validates and exposes the documented fields."""
    payload = _sc1_body_dict(
        ordno="1234567",
        execqty="10",
        execprc="73500",
        unercqty="0",
        ordqty="10",
        ordxctptncode="11",
        shtnIsuno="A005930",
        Isunm="삼성전자",
        exectime="091532123",
    )
    body = SC1RealResponseBody.model_validate(payload)

    assert body.ordno == "1234567"
    assert body.execqty == "10"
    assert body.execprc == "73500"
    assert body.unercqty == "0"
    assert body.ordxctptncode == "11"
    assert body.shtnIsuno == "A005930"
    assert body.Isunm == "삼성전자"


def test_sc1_body_parses_partial_fill_payload():
    """Partial fill: execqty < ordqty, unercqty > 0."""
    body = SC1RealResponseBody.model_validate(_sc1_body_dict(
        ordno="1234567",
        ordqty="10",
        execqty="3",
        unercqty="7",
        ordxctptncode="11",
    ))

    assert int(body.execqty) == 3
    assert int(body.unercqty) == 7
    assert int(body.execqty) + int(body.unercqty) == int(body.ordqty)


def test_sc1_body_parses_rejection_payload():
    """Rejection event uses ordxctptncode='14' + rjtqty > 0."""
    body = SC1RealResponseBody.model_validate(_sc1_body_dict(
        ordno="9999999",
        ordqty="10",
        rjtqty="10",
        unercqty="10",
        ordxctptncode="14",
        msgcode="01478",
    ))

    assert body.ordxctptncode == "14"
    assert body.rjtqty == "10"
    assert body.msgcode == "01478"


def test_sc1_body_rejects_missing_required_field():
    """Sanity: all fields are required — omitting one raises ValidationError."""
    payload = _sc1_body_dict()
    payload.pop("ordno")

    with pytest.raises(Exception):
        SC1RealResponseBody.model_validate(payload)


# ---------------------------------------------------------------------------
# Layer 2 — OrdNo type-cast contract
# ---------------------------------------------------------------------------


def test_ordno_int_vs_str_requires_cast():
    """CSPAT00601.block2.OrdNo is int; SC1.body.ordno is str. Direct == fails."""
    cspat_ordno_int = 1234567
    sc1_ordno_str = "1234567"

    assert cspat_ordno_int != sc1_ordno_str
    assert str(cspat_ordno_int) == sc1_ordno_str


# ---------------------------------------------------------------------------
# Layer 3 — asyncio.Future matching lifecycle
# ---------------------------------------------------------------------------


class _OrderMatcher:
    """Mirrors the on_sc1_message dispatch in run_CSPAT00601_with_SC1.py."""

    FILL = "11"
    REJECT = "14"

    def __init__(self):
        self.pending: Dict[str, asyncio.Future] = {}
        self.fills: Dict[str, list] = {}

    def track(self, ord_no_int: int) -> asyncio.Future:
        ord_no = str(ord_no_int)
        fut = asyncio.get_running_loop().create_future()
        self.pending[ord_no] = fut
        return fut

    def on_sc1(self, resp: SC1RealResponse) -> None:
        if resp.body is None:
            return
        ordno = resp.body.ordno
        fut = self.pending.get(ordno)
        if fut is None:
            return
        code = resp.body.ordxctptncode

        if code == self.FILL:
            self.fills.setdefault(ordno, []).append({
                "execqty": int(resp.body.execqty or "0"),
                "execprc": int(resp.body.execprc or "0"),
            })
            if resp.body.unercqty == "0" and not fut.done():
                fut.set_result("filled")
        elif code == self.REJECT:
            if not fut.done():
                fut.set_exception(RuntimeError(
                    f"rejected: rjtqty={resp.body.rjtqty} msgcode={resp.body.msgcode}"
                ))


@pytest.mark.asyncio
async def test_full_fill_resolves_future():
    matcher = _OrderMatcher()
    fut = matcher.track(1234567)

    matcher.on_sc1(_make_sc1_response(
        ordno="1234567",
        ordqty="10",
        execqty="10",
        execprc="73500",
        unercqty="0",
        ordxctptncode="11",
    ))

    assert fut.done()
    assert fut.result() == "filled"
    assert sum(f["execqty"] for f in matcher.fills["1234567"]) == 10


@pytest.mark.asyncio
async def test_partial_then_full_fill_accumulates_then_resolves():
    matcher = _OrderMatcher()
    fut = matcher.track(1234567)

    matcher.on_sc1(_make_sc1_response(
        ordno="1234567",
        ordqty="10",
        execqty="3",
        execprc="73500",
        unercqty="7",
        ordxctptncode="11",
    ))
    assert not fut.done()
    assert sum(f["execqty"] for f in matcher.fills["1234567"]) == 3

    matcher.on_sc1(_make_sc1_response(
        ordno="1234567",
        ordqty="10",
        execqty="7",
        execprc="73600",
        unercqty="0",
        ordxctptncode="11",
    ))
    assert fut.done()
    assert fut.result() == "filled"
    assert sum(f["execqty"] for f in matcher.fills["1234567"]) == 10


@pytest.mark.asyncio
async def test_rejection_sets_future_exception():
    matcher = _OrderMatcher()
    fut = matcher.track(9999999)

    matcher.on_sc1(_make_sc1_response(
        ordno="9999999",
        ordqty="10",
        rjtqty="10",
        unercqty="10",
        ordxctptncode="14",
        msgcode="01478",
    ))

    assert fut.done()
    with pytest.raises(RuntimeError, match="rejected"):
        fut.result()


@pytest.mark.asyncio
async def test_unrelated_ordno_does_not_resolve_future():
    """SC1 events for other accounts/orders must be ignored."""
    matcher = _OrderMatcher()
    fut = matcher.track(1234567)

    matcher.on_sc1(_make_sc1_response(
        ordno="9999999",
        ordqty="10",
        execqty="10",
        unercqty="0",
        ordxctptncode="11",
    ))

    assert not fut.done()
    assert "1234567" not in matcher.fills


@pytest.mark.asyncio
async def test_timeout_path_when_no_fill_arrives():
    """If no SC1 fill within timeout, asyncio.wait_for raises TimeoutError."""
    matcher = _OrderMatcher()
    fut = matcher.track(1234567)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(fut, timeout=0.05)
