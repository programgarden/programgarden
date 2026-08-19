"""Runtime order diagnostics for AI-chatbot-friendly live trading callbacks.

Unlike the pre-trade ``validation`` module (which produces ``ErrorInfo`` for
``validate()`` / ``dry_run`` paths), this module covers *live runtime* order
outcomes:

1. **Order rejection** — maps an LS Securities response code (``rsp_cd``) to a
   structured ``OrderRejectInfo`` (English cause + remediation tip) so the
   consuming chatbot can reason about *why* an order was rejected and *what to
   fix*, instead of passing through the raw broker message only.
2. **Empty order result** — the ``EmptyOrderReason`` enum lets a consumer
   deterministically distinguish "no trading signal today (normal)" from
   "upstream data pipeline failed (broken)".

This is a pure, dependency-free data layer (no imports from other packages).
All user-facing strings here follow the ``ErrorInfo`` convention: ``cause`` is a
single English sentence (like ``ErrorInfo.message``) and ``tip`` is a single
English line (like ``ErrorInfo.suggestion``).

The ``rsp_cd`` mapping tables intentionally start **empty**. Entries are added
only after a code is observed and confirmed in live trading — never guessed
from incomplete LS specs. Until a code is registered, ``map_reject_code``
falls back to the raw broker message with ``known=False``.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderRejectInfo(BaseModel):
    """Structured diagnostic for a broker-rejected order.

    Always carries the raw broker message (``raw_msg``) as a fallback so the
    consumer never loses the original text, even for unmapped codes.
    """

    rsp_cd: str = Field(
        description="LS Securities response code, e.g. '40570'. '00000' means success.",
    )
    cause: str = Field(
        description=(
            "One-sentence English explanation of why the order was rejected. "
            "Falls back to raw_msg when the code is not in the mapping table."
        ),
    )
    tip: Optional[str] = Field(
        default=None,
        description=(
            "Single-line English remediation hint. None when the code is "
            "unmapped (no known fix to suggest)."
        ),
    )
    raw_msg: str = Field(
        default="",
        description="Original LS broker message (rsp_msg / error_msg), always included.",
    )
    known: bool = Field(
        description=(
            "True when a structured cause/tip is available (from the "
            "reject-code table OR a recognized order-lifecycle case); False "
            "when only the raw broker message is available."
        ),
    )

    model_config = ConfigDict(extra="forbid")


class EmptyOrderReason(str, Enum):
    """Why an order node produced no order.

    Lets a consumer distinguish a normal no-op from a pipeline failure so that
    "no order today" is never silently treated the same as "data fetch broke".
    """

    NO_SIGNAL = "no_signal"
    """Upstream produced an empty result normally (no trading signal today)."""

    FETCH_FAILED = "fetch_failed"
    """Upstream data lookup itself failed (broken pipeline)."""

    NO_SYMBOL = "no_symbol"
    """No symbol was specified (missing configuration)."""


# ---------------------------------------------------------------------------
# Market-specific reject-code tables.
#
# Structure: rsp_cd -> {"cause": <english one-sentence>, "tip": <english one-liner>}
#
# Only live-verified, real rsp_cd values are registered here. Do NOT guess
# codes or causes from incomplete LS specifications — register a code only
# after it is observed and confirmed in live trading.
# ---------------------------------------------------------------------------

# Live-verified 2026-08-19 on a real LS overseas-stock account (COSAT00301).
# Each entry was produced by deliberately triggering the rejection and reading
# the returned rsp_cd/rsp_msg — none of these are inferred from the LS spec.
OVERSEAS_STOCK_REJECT_CODES: Dict[str, Dict[str, str]] = {
    "02201": {
        "cause": "The account does not have enough cash to place this order.",
        "tip": "Reduce the quantity or price, or deposit more cash, then retry.",
    },
    "02259": {
        "cause": "No order exists for the original order number given.",
        "tip": (
            "Re-read the open orders and use an order number from that list; "
            "the number may be wrong or the order may already be gone."
        ),
    },
    "03053": {
        "cause": "The broker does not recognize the symbol code.",
        "tip": "Check the symbol spelling and that it is listed on the given exchange.",
    },
    "03759": {
        "cause": (
            "The original order has no remaining quantity to modify or cancel "
            "(it was already filled or already cancelled)."
        ),
        "tip": (
            "Re-read the order status before retrying — a filled order cannot be "
            "cancelled, and an already-cancelled order needs no action."
        ),
    },
}
OVERSEAS_FUTURES_REJECT_CODES: Dict[str, Dict[str, str]] = {}

# Live-verified 2026-08-19 on a real LS Korea-stock account (CSPAT00601 new /
# CSPAT00801 cancel). Same shape as the overseas table: rsp_cd carries the cause
# and error_msg comes back empty, so a rejection is only visible through rsp_cd.
#
# One shape difference worth knowing: a rejected *cancel* (CSPAT00801) still
# returns block2, but with OrdNo=0 — unlike a rejected *new* order, which comes
# back with no block2 at all. The executor's "OrdNo missing or 0" guard is what
# catches it.
KOREA_STOCK_REJECT_CODES: Dict[str, Dict[str, str]] = {
    "01524": {
        "cause": "The broker does not recognize the symbol code.",
        "tip": "Check the symbol code — Korean issues are 6 digits, optionally prefixed with 'A'.",
    },
    "03056": {
        "cause": "No order exists for the original order number given.",
        "tip": (
            "Re-read the open orders (t0425) and use an order number from that "
            "list; the number may be wrong or the order may already be gone."
        ),
    },
    "03181": {
        "cause": "The order price is below the daily lower price limit.",
        "tip": (
            "Korean equities trade inside a daily price band. Move the price "
            "inside the band (the quote TR reports the upper/lower limits)."
        ),
    },
}

_MARKET_TABLES: Dict[str, Dict[str, Dict[str, str]]] = {
    "overseas_stock": OVERSEAS_STOCK_REJECT_CODES,
    "overseas_futures": OVERSEAS_FUTURES_REJECT_CODES,
    "korea_stock": KOREA_STOCK_REJECT_CODES,
}


# Response codes that mean "the broker accepted the order". Live-measured on a
# real LS account (2026-08-19): new buy "00040", new sell "00039", cancel
# "00156". "00000" is the generic success code kept for defensiveness.
ORDER_ACCEPTED_RSP_CDS = frozenset({"00000", "00039", "00040", "00156"})


def diagnose_missing_order_no(
    market: str, rsp_cd: str, raw_msg: str = ""
) -> OrderRejectInfo:
    """Diagnose a response that carries no order number.

    🔴 Callers used to assume this always meant "the broker accepted it but the
    order number is missing", and told the user it was probably a closed market
    or a broker delay. Live measurement on a real account (2026-08-19) showed
    that assumption is wrong: an LS business rejection arrives with an **empty
    ``error_msg``, an error ``rsp_cd``, and no response block at all** — e.g.
    ``02201`` (not enough cash) or ``03053`` (unknown symbol). So that branch
    swallowed real rejections and reported the wrong cause — telling a user
    whose account was short on cash that the market was probably closed.

    Only a genuine accept code falls back to the lifecycle explanation; anything
    else is routed to the live-verified reject table.
    """
    rsp_cd = str(rsp_cd or "")
    raw_msg = str(raw_msg or "")

    if rsp_cd and rsp_cd not in ORDER_ACCEPTED_RSP_CDS:
        return map_reject_code(market, rsp_cd, raw_msg)

    return OrderRejectInfo(
        rsp_cd=rsp_cd,
        cause=(
            "Order accepted but no order number returned "
            "(likely market closed or broker delay)"
        ),
        tip=(
            "Verify market hours and re-query open orders to confirm whether "
            "the order was actually placed."
        ),
        raw_msg=raw_msg,
        known=True,
    )


def map_reject_code(market: str, rsp_cd: str, raw_msg: str = "") -> OrderRejectInfo:
    """Map an LS reject ``rsp_cd`` to a structured ``OrderRejectInfo``.

    Looks up ``rsp_cd`` in the table for ``market``. If found, returns a mapped
    diagnostic (``known=True``); if the code's mapped ``cause`` is empty, falls
    back to ``raw_msg``. If the market or code is unknown, returns a raw
    fallback (``known=False``, ``tip=None``).

    Args:
        market: One of "overseas_stock", "overseas_futures", "korea_stock".
            An unknown market string is handled defensively (raw fallback).
        rsp_cd: LS Securities response code. Success codes ("00000") are
            filtered by callers, but are handled defensively here.
        raw_msg: Original LS broker message, used as the fallback cause.

    Returns:
        OrderRejectInfo with cause/tip/known populated.
    """
    # Defensive casts: callers may pass non-str rsp_cd (e.g. int OrdNo) or a
    # None raw_msg from a mocked LS response — never let that raise.
    rsp_cd = str(rsp_cd or "")
    raw_msg = str(raw_msg or "")

    table = _MARKET_TABLES.get(market, {})
    entry = table.get(rsp_cd)

    if entry is not None:
        cause = entry.get("cause") or raw_msg or (
            f"Order rejected by broker (code {rsp_cd}, no diagnostic mapping)"
        )
        tip = entry.get("tip") or None
        return OrderRejectInfo(
            rsp_cd=rsp_cd,
            cause=cause,
            tip=tip,
            raw_msg=raw_msg,
            known=True,
        )

    cause = raw_msg or f"Order rejected by broker (code {rsp_cd}, no diagnostic mapping)"
    return OrderRejectInfo(
        rsp_cd=rsp_cd,
        cause=cause,
        tip=None,
        raw_msg=raw_msg,
        known=False,
    )
