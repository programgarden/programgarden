"""Pydantic models for LS Securities OpenAPI t1903 (ETF daily history / ETF일별추이).

t1903 returns a per-day historical time series for a Korean-market ETF
or ETN issue. The response carries:

    - ``OutBlock`` (``cont_block``) — header row with the continuation
      cursor (``date``) plus the issue's Korean name and the benchmark
      sector / index name.
    - ``OutBlock1`` (``block``) — list of per-day rows: trade date,
      closing price + previous-close direction + change, traded volume,
      NAV + NAV change vs. price (``navdiff``), NAV-period change
      (``navchange``), tracking error (``crate``), premium / discount
      (``grate``), benchmark index value (``jisu``) + previous-close
      change + change ratio.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1``
      rows are NOT declared in the source available to this codebase;
      consume as returned by LS. Domestic ETF prices in LS feeds are
      typically integer KRW per share, but this is not asserted as a
      contract.
    - ``cont_block.date`` is the LS continuation cursor; pass back
      verbatim (in ``InBlock.date``) on follow-up requests to retrieve
      older history.
    - ``sign`` direction codes follow the standard LS stock convention
      ('1' = 상한 / '2' = 상승 / '3' = 보합 / '4' = 하한 / '5' = 하락).
    - The two NAV-related delta fields (``navdiff`` vs. ``navchange``)
      and the two change fields (``change`` vs. previous close,
      ``jichange`` for the index) follow the source labels exactly —
      no attempt is made to redefine which field is "vs. price" vs.
      "vs. previous close" beyond what the source label states.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1903.py``
      (``shcode='069500'`` = KODEX 200).
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1903RequestHeader(BlockRequestHeader):
    """t1903 request header. Inherits the standard LS request header schema."""
    pass


class T1903ResponseHeader(BlockResponseHeader):
    """t1903 response header. Inherits the standard LS response header schema."""
    pass


class T1903InBlock(BaseModel):
    """t1903InBlock — input block for the ETF daily-history query."""

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean ETF / ETN short code (e.g., '069500' for KODEX 200).",
        examples=["069500"],
    )
    date: str = Field(
        default="",
        title="일자 (Date / continuation key)",
        description=(
            "Continuation date for paged queries, in 'YYYYMMDD' format. "
            "Empty on the first request; on follow-ups, pass back the "
            "``date`` returned in the previous response's ``cont_block``. "
            "Treat as opaque LS-defined cursor."
        ),
        examples=[""],
    )


class T1903OutBlock(BaseModel):
    """t1903OutBlock — header / continuation block for the ETF daily-history response."""

    date: str = Field(
        default="",
        title="일자 (Continuation date)",
        description=(
            "Continuation date for the next paged request, in 'YYYYMMDD' "
            "format. Pass back verbatim in ``InBlock.date`` to retrieve "
            "older rows. Empty when no further history is available."
        ),
        examples=[""],
    )
    hname: str = Field(
        default="",
        title="종목명 (Issue name)",
        description="Korean ETF / ETN issue name.",
        examples=["KODEX 200"],
    )
    upname: str = Field(
        default="",
        title="업종지수명 (Sector / benchmark index name)",
        description="Sector / benchmark index name that the ETF tracks.",
        examples=["KOSPI200"],
    )


class T1903OutBlock1(BaseModel):
    """t1903OutBlock1 — per-day row in the ETF daily-history response.

    Decimal scale, currency unit, and time ordering of rows are NOT
    declared in the source available to this codebase; consume as
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
        title="현재가 (Closing price)",
        description="Closing price for the trade date. Decimal scale not declared in available source.",
        examples=[37520],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-close direction)",
        description=(
            "Direction code vs. previous close. '1' = upper limit (상한), "
            "'2' = up (상승), '3' = unchanged (보합), '4' = lower limit "
            "(하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change vs. previous close)",
        description="Closing-price change vs. previous trade-date close. Sign convention not declared in available source.",
        examples=[120, -85, 0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the trade date.",
        examples=[2500000],
    )
    navdiff: float = Field(
        default=0.0,
        title="NAV대비 (NAV vs. price)",
        description=(
            "NAV-relative metric per the LS source label 'NAV대비'. "
            "Definition (absolute deviation vs. percentage) not declared "
            "in available source; consume as returned by LS."
        ),
        examples=[1.85, -1.20, 0.0],
    )
    nav: float = Field(
        default=0.0,
        title="NAV",
        description=(
            "Net Asset Value per share for the trade date. Decimal scale "
            "not declared in available source; consume as returned by LS."
        ),
        examples=[37498.21],
    )
    navchange: float = Field(
        default=0.0,
        title="전일대비 (NAV change vs. previous trade-date NAV)",
        description=(
            "NAV change vs. previous trade-date NAV per the LS source "
            "label '전일대비'. Sign convention not declared in available "
            "source."
        ),
        examples=[120.45, -85.20, 0.0],
    )
    crate: float = Field(
        default=0.0,
        title="추적오차 (Tracking error)",
        description=(
            "Tracking error (%) of the ETF vs. its underlying index for "
            "the trade date. Decimal scale and sign convention not "
            "declared in available source."
        ),
        examples=[0.05, -0.03, 0.0],
    )
    grate: float = Field(
        default=0.0,
        title="괴리 (Premium / discount)",
        description=(
            "Premium / discount (%) of market price relative to NAV for "
            "the trade date. Decimal scale not declared; sign convention "
            "(positive = premium vs. negative = discount) not asserted."
        ),
        examples=[0.06, -0.04, 0.0],
    )
    jisu: float = Field(
        default=0.0,
        title="지수 (Benchmark index value)",
        description="Benchmark index closing value for the trade date. Decimal scale not declared in available source.",
        examples=[375.42],
    )
    jichange: float = Field(
        default=0.0,
        title="전일대비 (Index change vs. previous trade-date close)",
        description=(
            "Benchmark index change vs. previous trade-date close per "
            "the LS source label '전일대비'. Sign convention not declared "
            "in available source."
        ),
        examples=[1.25, -0.85, 0.0],
    )
    jirate: float = Field(
        default=0.0,
        title="전일대비율 (Index change ratio)",
        description="Benchmark index change ratio (%) vs. previous trade-date close. Decimal scale not declared in available source.",
        examples=[0.33, -0.22, 0.0],
    )


class T1903Request(BaseModel):
    """t1903 request envelope."""

    header: T1903RequestHeader = T1903RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1903",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1903Response(BaseModel):
    """t1903 response envelope."""

    header: Optional[T1903ResponseHeader] = None
    cont_block: Optional[T1903OutBlock] = None
    block: list[T1903OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1903RequestHeader",
    "T1903ResponseHeader",
    "T1903InBlock",
    "T1903OutBlock",
    "T1903OutBlock1",
    "T1903Request",
    "T1903Response",
]
