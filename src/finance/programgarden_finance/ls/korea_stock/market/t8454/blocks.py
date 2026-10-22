"""Pydantic models for LS Securities OpenAPI t8454 ((통합)주식시간대별체결2 / unified per-trade tape).

t8454 returns intraday per-trade rows for a Korean stock symbol across the
unified KRX/NXT venues, returning the trade time, last price, sign, change,
trade strength, side-resolved volumes/counts, and the originating exchange
name. Pagination is via ``cts_time`` (continuation cursor).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English; the Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``cts_time`` is an opaque LS-defined continuation token; pass back
      verbatim on follow-up requests.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8454RequestHeader(BlockRequestHeader):
    """t8454 request header. Inherits the standard LS request header schema."""
    pass


class T8454ResponseHeader(BlockResponseHeader):
    """t8454 response header. Inherits the standard LS response header schema."""
    pass


class T8454InBlock(BaseModel):
    """t8454InBlock — input block for the unified per-trade tape query."""

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    cvolume: int = Field(
        default=0,
        title="특이거래량 (Notable trade quantity threshold)",
        description="Filter threshold — rows with trade quantity greater than this value are flagged. 0 means no filter.",
        examples=[0, 1000],
    )
    starttime: str = Field(
        default="",
        title="시작시간 (Start time)",
        description="Start of the time window in 'HHMM' or 'HHMMSS' format. Empty for session start.",
        examples=["", "0900"],
    )
    endtime: str = Field(
        default="",
        title="종료시간 (End time)",
        description="End of the time window in 'HHMM' or 'HHMMSS' format. Empty for session end.",
        examples=["", "1530"],
    )
    cts_time: str = Field(
        default="",
        title="시간CTS (Continuation cursor)",
        description="Continuation cursor for paged queries. Empty on first request; pass back ``cts_time`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[""],
    )
    exchgubun: str = Field(
        default="",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합). Empty defaults per LS "
            "convention."
        ),
        examples=["", "K", "N", "U"],
    )


class T8454OutBlock(BaseModel):
    """t8454OutBlock — continuation block (echoes ``cts_time`` and exchange-resolved short code)."""

    cts_time: str = Field(
        default="",
        title="시간CTS (Continuation cursor)",
        description="Continuation cursor for the next paged request. Empty when no further rows are available.",
        examples=[""],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description="Exchange-resolved short code echoed for the issue. Format and semantics not declared in available source.",
        examples=[""],
    )


class T8454OutBlock1(BaseModel):
    """t8454OutBlock1 — per-trade row for the unified tape.

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    chetime: str = Field(
        default="",
        title="시간 (Trade time)",
        description="Trade time in 'HHMMSS' format.",
        examples=["093015"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Trade price)",
        description="Trade price for this row. Decimal scale not declared in available source.",
        examples=[79800],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. '1' = upper limit, '2' = "
            "up, '3' = unchanged, '4' = lower limit, '5' = down per LS "
            "convention."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of change versus previous close. Sign convention not declared in available source.",
        examples=[800, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change versus previous close. Sign convention not declared in available source.",
        examples=[1.02, 0.0, -0.5],
    )
    cvolume: int = Field(
        default=0,
        title="체결수량 (Trade quantity)",
        description="Trade quantity in shares for this row.",
        examples=[100, 5000],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description="LS-defined trade strength indicator. Formula not declared in available source.",
        examples=[105.32, 98.74],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares as of this row.",
        examples=[15000000],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결수량 (Sell-side trade volume)",
        description="Cumulative sell-aggressor trade volume in shares as of this row.",
        examples=[7500000],
    )
    mdchecnt: int = Field(
        default=0,
        title="매도체결건수 (Sell-side trade count)",
        description="Cumulative sell-aggressor trade count as of this row.",
        examples=[12000],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결수량 (Buy-side trade volume)",
        description="Cumulative buy-aggressor trade volume in shares as of this row.",
        examples=[7500000],
    )
    mschecnt: int = Field(
        default=0,
        title="매수체결건수 (Buy-side trade count)",
        description="Cumulative buy-aggressor trade count as of this row.",
        examples=[12000],
    )
    revolume: int = Field(
        default=0,
        title="순체결량 (Net trade volume)",
        description="Net trade volume (buy minus sell aggressor) in shares. Sign convention per LS.",
        examples=[0, 100, -50],
    )
    rechecnt: int = Field(
        default=0,
        title="순체결건수 (Net trade count)",
        description="Net trade count (buy minus sell aggressor). Sign convention per LS.",
        examples=[0, 5, -3],
    )
    exchname: str = Field(
        default="",
        title="거래소명 (Exchange name)",
        description="Originating exchange name for this trade row. Code/label values not declared in available source.",
        examples=["KRX", "NXT"],
    )


class T8454Request(BaseModel):
    """t8454 request envelope."""

    header: T8454RequestHeader = T8454RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8454",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8454",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8454Response(BaseModel):
    """t8454 response envelope."""

    header: Optional[T8454ResponseHeader] = None
    cont_block: Optional[T8454OutBlock] = None
    block: list[T8454OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8454RequestHeader",
    "T8454ResponseHeader",
    "T8454InBlock",
    "T8454OutBlock",
    "T8454OutBlock1",
    "T8454Request",
    "T8454Response",
]
