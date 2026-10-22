"""Pydantic models for LS Securities OpenAPI t1941 (Domestic Stock per-issue stock-loan daily trend).

t1941 returns the daily stock-loan (대차거래) trend for a single issue
across a date range: per-day close, total volume, new loan executions,
loan returns, outstanding loan balance (quantity + value), and net loan
balance change.

Response carries:
    - ``OutBlock1`` (``block``) — list of per-day rows. No ``cont_block``
      is present for this TR per source.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale of price / value fields and time ordering of rows are
      NOT declared in the source available to this codebase; consume as
      returned by LS.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1941.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1941RequestHeader(BlockRequestHeader):
    """t1941 request header. Inherits the standard LS request header schema."""
    pass


class T1941ResponseHeader(BlockResponseHeader):
    """t1941 response header. Inherits the standard LS response header schema."""
    pass


class T1941InBlock(BaseModel):
    """t1941InBlock — input block for the per-issue stock-loan daily trend query."""

    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code (e.g., '005930' for Samsung Electronics).",
        examples=["005930"],
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


class T1941OutBlock1(BaseModel):
    """t1941OutBlock1 — per-day stock-loan trend row.

    Decimal scale of price / value fields and time ordering of rows are
    NOT declared in the source available to this codebase; consume as
    returned by LS. Net loan balance change (``tovoldif``) can take any
    sign — positive, negative, and zero examples preserved.
    """

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Trade date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    price: int = Field(
        default=0,
        title="종가 (Close price)",
        description="Closing price of the issue for the day. Decimal scale not declared in available source.",
        examples=[78000],
    )
    sign: str = Field(
        default="",
        title="대비구분 (Change direction)",
        description=(
            "Change direction code vs. previous close. '1' = upper limit "
            "(상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower "
            "limit (하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="대비 (Change amount)",
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
    upvolume: int = Field(
        default=0,
        title="당일체결 (Daily new loan executions)",
        description=(
            "New stock-loan executions (대차 체결) for the day, in shares."
        ),
        examples=[100000],
    )
    dnvolume: int = Field(
        default=0,
        title="당일상환 (Daily loan repayments)",
        description=(
            "Stock-loan repayments / returns (대차 상환) for the day, in "
            "shares."
        ),
        examples=[50000],
    )
    tovolume: int = Field(
        default=0,
        title="당일잔고 (Daily outstanding loan balance)",
        description=(
            "Outstanding stock-loan balance (대차잔고) at the end of the "
            "day, in shares."
        ),
        examples=[5000000],
    )
    tovalue: int = Field(
        default=0,
        title="잔고금액 (Outstanding loan value)",
        description=(
            "Value of the outstanding stock-loan balance. Decimal scale "
            "and currency unit not declared in available source."
        ),
        examples=[395000000000],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    tovoldif: int = Field(
        default=0,
        title="대차증감 (Loan balance change)",
        description=(
            "Net change in outstanding stock-loan balance vs. previous day "
            "(대차 증감 = upvolume - dnvolume)."
        ),
        examples=[50000, -50000, 0],
    )


class T1941Request(BaseModel):
    """t1941 request envelope."""

    header: T1941RequestHeader = T1941RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1941",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1941"
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1941Response(BaseModel):
    """t1941 response envelope."""

    header: Optional[T1941ResponseHeader] = None
    block: list[T1941OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1941RequestHeader",
    "T1941ResponseHeader",
    "T1941InBlock",
    "T1941OutBlock1",
    "T1941Request",
    "T1941Response",
]
