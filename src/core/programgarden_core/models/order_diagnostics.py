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

OVERSEAS_STOCK_REJECT_CODES: Dict[str, Dict[str, str]] = {}
OVERSEAS_FUTURES_REJECT_CODES: Dict[str, Dict[str, str]] = {}
KOREA_STOCK_REJECT_CODES: Dict[str, Dict[str, str]] = {}

_MARKET_TABLES: Dict[str, Dict[str, Dict[str, str]]] = {
    "overseas_stock": OVERSEAS_STOCK_REJECT_CODES,
    "overseas_futures": OVERSEAS_FUTURES_REJECT_CODES,
    "korea_stock": KOREA_STOCK_REJECT_CODES,
}


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
