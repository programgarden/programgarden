"""Pydantic models for LS Securities OpenAPI t8407 (API용주식멀티현재가조회 / multi-symbol stock current quote).

t8407 returns a current-price snapshot (price, sign, change, volume, top-of-book
quote, OHLC, daily limits) for up to ``nrec`` Korean stock symbols in a single
request. The input ``shcode`` is a concatenation of multiple 6-digit short codes
(e.g., ``"005930000660373220"`` = three symbols joined contiguously).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English, with the Korean label appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale and currency unit are NOT declared in the source
      available to this codebase; consume as returned by LS.
    - ``volume`` and ``cvolume`` are typically share counts; ``value`` per
      LS source label is in 백만원 (millions of KRW), preserved verbatim.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t8407.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8407RequestHeader(BlockRequestHeader):
    """t8407 request header. Inherits the standard LS request header schema."""
    pass


class T8407ResponseHeader(BlockResponseHeader):
    """t8407 response header. Inherits the standard LS response header schema."""
    pass


class T8407InBlock(BaseModel):
    """t8407InBlock — input block for the multi-symbol current quote query."""

    nrec: int = Field(
        default=0,
        title="건수 (Record count)",
        description="Number of symbols packed into ``shcode``. Must match the count of 6-digit codes concatenated in that field.",
        examples=[1, 3],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Symbol codes)",
        description=(
            "Concatenation of one or more 6-digit Korean stock short codes "
            "with no separator. Example: ``'005930000660373220'`` packs "
            "Samsung (005930), SK Hynix (000660), and LG Energy Solution "
            "(373220)."
        ),
        examples=["005930", "005930000660373220"],
    )


class T8407OutBlock1(BaseModel):
    """t8407OutBlock1 — per-symbol current quote row (one entry per requested symbol)."""

    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code echoed for this row.",
        examples=["005930"],
    )
    hname: str = Field(
        default="",
        title="종목명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current price for the issue. Decimal scale not declared in available source; consume as returned by LS.",
        examples=[79800],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Previous-day direction code per LS convention. '1' = upper "
            "limit (상한), '2' = up (상승), '3' = unchanged (보합), '4' = "
            "lower limit (하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Sign convention not declared in available source; treat as absolute value paired with ``sign``.",
        examples=[800, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change versus previous close. Sign convention not declared in available source.",
        examples=[1.02, 0.0, -0.5],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    offerho: int = Field(
        default=0,
        title="매도호가 (Best ask price)",
        description="Best ask price (top of book sell side).",
        examples=[79900],
    )
    bidho: int = Field(
        default=0,
        title="매수호가 (Best bid price)",
        description="Best bid price (top of book buy side).",
        examples=[79800],
    )
    cvolume: int = Field(
        default=0,
        title="체결수량 (Last trade quantity)",
        description="Quantity of the most recent trade in shares.",
        examples=[100],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description="LS-defined trade strength indicator (체결강도). Formula not declared in available source.",
        examples=[105.32, 98.74],
    )
    open: int = Field(
        default=0,
        title="시가 (Open)",
        description="Today's opening price.",
        examples=[79100],
    )
    high: int = Field(
        default=0,
        title="고가 (High)",
        description="Today's high price as of response time.",
        examples=[80000],
    )
    low: int = Field(
        default=0,
        title="저가 (Low)",
        description="Today's low price as of response time.",
        examples=[78900],
    )
    value: int = Field(
        default=0,
        title="거래대금(백만) (Trade value, millions)",
        description="Cumulative traded value in millions of KRW per LS source label '백만'.",
        examples=[1185000],
    )
    offerrem: int = Field(
        default=0,
        title="우선매도잔량 (Best ask quantity)",
        description="Quantity at the best ask price.",
        examples=[5000],
    )
    bidrem: int = Field(
        default=0,
        title="우선매수잔량 (Best bid quantity)",
        description="Quantity at the best bid price.",
        examples=[3500],
    )
    totofferrem: int = Field(
        default=0,
        title="총매도잔량 (Total ask quantity)",
        description="Aggregate ask-side resting quantity across the visible book.",
        examples=[1200000],
    )
    totbidrem: int = Field(
        default=0,
        title="총매수잔량 (Total bid quantity)",
        description="Aggregate bid-side resting quantity across the visible book.",
        examples=[980000],
    )
    jnilclose: int = Field(
        default=0,
        title="전일종가 (Previous close)",
        description="Previous trading day's closing price (reference price).",
        examples=[79000],
    )
    uplmtprice: int = Field(
        default=0,
        title="상한가 (Upper limit price)",
        description="Daily upper price limit (상한가) for the issue.",
        examples=[102700],
    )
    dnlmtprice: int = Field(
        default=0,
        title="하한가 (Lower limit price)",
        description="Daily lower price limit (하한가) for the issue.",
        examples=[55300],
    )


class T8407Request(BaseModel):
    """t8407 request envelope."""

    header: T8407RequestHeader = T8407RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8407",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8407",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8407Response(BaseModel):
    """t8407 response envelope."""

    header: Optional[T8407ResponseHeader] = None
    block: list[T8407OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8407RequestHeader",
    "T8407ResponseHeader",
    "T8407InBlock",
    "T8407OutBlock1",
    "T8407Request",
    "T8407Response",
]
