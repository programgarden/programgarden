"""Pydantic models for LS Securities OpenAPI t1927 (Domestic Stock per-issue short-selling daily trend).

t1927 returns the daily short-selling trend for a single issue across a
date range: short-sell volume / value, share of total volume, average
short-sell price, cumulative short-sell volume, and uptick-rule applied /
exempted breakdowns.

Response carries:
    - ``OutBlock`` (``cont_block``) — single-field continuation cursor
      (``date``).
    - ``OutBlock1`` (``block``) — list of per-day rows.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale of price / value fields and time ordering of rows are
      NOT declared in the source available to this codebase; consume as
      returned by LS.
    - ``cont_block.date`` is the LS continuation cursor; pass back verbatim
      on follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1927.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1927RequestHeader(BlockRequestHeader):
    """t1927 request header. Inherits the standard LS request header schema."""
    pass


class T1927ResponseHeader(BlockResponseHeader):
    """t1927 response header. Inherits the standard LS response header schema."""
    pass


class T1927InBlock(BaseModel):
    """t1927InBlock — input block for the per-issue short-selling daily trend query."""

    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code (e.g., '005930' for Samsung Electronics).",
        examples=["005930"],
    )
    date: str = Field(
        default="",
        title="일자 (Date)",
        description=(
            "Single-day query date in 'YYYYMMDD' format. Empty string when "
            "using the date-range fields below."
        ),
        examples=[""],
    )
    sdate: str = Field(
        default="",
        title="시작일자 (Start date)",
        description="Range start date in 'YYYYMMDD' format.",
        examples=["20260201"],
    )
    edate: str = Field(
        default="",
        title="종료일자 (End date)",
        description="Range end date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )


class T1927OutBlock(BaseModel):
    """t1927OutBlock — continuation block (date cursor)."""

    date: str = Field(
        default="",
        title="일자CTS (Continuation date)",
        description=(
            "Continuation cursor in 'YYYYMMDD' format for the next paged "
            "request. Empty when no further history is available. Treat as "
            "opaque LS-defined token."
        ),
        examples=[""],
    )


class T1927OutBlock1(BaseModel):
    """t1927OutBlock1 — per-day short-selling trend row.

    Decimal scale of price / value fields and time ordering of rows are
    NOT declared in the source available to this codebase; consume as
    returned by LS.
    """

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Trade date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Close price)",
        description="Closing price of the issue for the day. Decimal scale not declared in available source.",
        examples=[78000],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Change direction)",
        description=(
            "Change direction code vs. previous close. '1' = upper limit "
            "(상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower "
            "limit (하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change amount)",
        description="Change amount vs. previous close.",
        examples=[500, -500, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change ratio)",
        description="Change ratio (%) vs. previous close.",
        examples=[0.65, -0.65, 0.0],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description="Total traded volume in shares for the day.",
        examples=[15000000],
    )
    value: int = Field(
        default=0,
        title="거래대금 (Trade value)",
        description=(
            "Total traded value (price × volume) for the day. Decimal "
            "scale not declared in available source."
        ),
        examples=[1185000000000],
    )
    gm_vo: int = Field(
        default=0,
        title="공매도수량 (Short-sell volume)",
        description="Short-selling volume in shares for the day.",
        examples=[200000],
    )
    gm_va: int = Field(
        default=0,
        title="공매도대금 (Short-sell value)",
        description="Short-selling traded value for the day.",
        examples=[15800000000],
    )
    gm_per: float = Field(
        default=0.0,
        title="공매도거래비중 (Short-sell share of volume)",
        description="Share (%) of short-selling volume in total volume for the day.",
        examples=[1.33, 0.0],
    )
    gm_avg: int = Field(
        default=0,
        title="평균공매도단가 (Average short-sell price)",
        description="Average price per share of short-sell trades for the day.",
        examples=[79000],
    )
    gm_vo_sum: int = Field(
        default=0,
        title="누적공매도수량 (Cumulative short-sell volume)",
        description="Cumulative short-selling volume aggregated up to the row's date.",
        examples=[5000000],
    )
    gm_vo1: int = Field(
        default=0,
        title="업틱룰적용공매도수량 (Uptick-rule applied short-sell volume)",
        description=(
            "Short-selling volume executed under the uptick rule "
            "(업틱룰 적용) for the day."
        ),
        examples=[150000],
    )
    gm_va1: int = Field(
        default=0,
        title="업틱룰적용공매도대금 (Uptick-rule applied short-sell value)",
        description="Short-selling value executed under the uptick rule for the day.",
        examples=[11850000000],
    )
    gm_vo2: int = Field(
        default=0,
        title="업틱룰예외공매도수량 (Uptick-rule exempt short-sell volume)",
        description=(
            "Short-selling volume executed under uptick-rule exemptions "
            "(업틱룰 예외) for the day."
        ),
        examples=[50000],
    )
    gm_va2: int = Field(
        default=0,
        title="업틱룰예외공매도대금 (Uptick-rule exempt short-sell value)",
        description="Short-selling value executed under uptick-rule exemptions for the day.",
        examples=[3950000000],
    )


class T1927Request(BaseModel):
    """t1927 request envelope."""

    header: T1927RequestHeader = T1927RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1927",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1927",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1927Response(BaseModel):
    """t1927 response envelope."""

    header: Optional[T1927ResponseHeader] = None
    cont_block: Optional[T1927OutBlock] = None
    block: list[T1927OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1927RequestHeader",
    "T1927ResponseHeader",
    "T1927InBlock",
    "T1927OutBlock",
    "T1927OutBlock1",
    "T1927Request",
    "T1927Response",
]
