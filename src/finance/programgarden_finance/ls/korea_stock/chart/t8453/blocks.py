"""Pydantic models for LS Securities OpenAPI t8453 (Domestic Stock tick / N-tick chart, unified).

t8453 returns OHLCV chart data for a domestic stock symbol at an N-tick
period (``ncnt`` ticks per bar). The response carries:

    - ``OutBlock`` (``cont_block``) — chart metadata: previous-day OHLCV,
      today's OHLCV, daily limits, session timing constants, NXT premarket /
      aftermarket session timing, and continuation keys
      (``cts_date`` / ``cts_time``).
    - ``OutBlock1`` (``block``) — list of per-bar rows (date, time, OHLC,
      volume, adjustment fields).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``cts_date`` / ``cts_time`` are LS continuation cursors; pass back
      verbatim on follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t8453.py``.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8453RequestHeader(BlockRequestHeader):
    """t8453 request header. Inherits the standard LS request header schema."""
    pass


class T8453ResponseHeader(BlockResponseHeader):
    """t8453 response header. Inherits the standard LS response header schema."""
    pass


class T8453InBlock(BaseModel):
    """t8453InBlock — input block for the tick / N-tick chart query."""

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code (e.g., '005930' for Samsung Electronics).",
        examples=["005930"],
    )
    ncnt: int = Field(
        default=0,
        title="단위 (Tick interval)",
        description="N-tick bar interval (e.g., 1 = 1-tick, 10 = 10-ticks per bar).",
        examples=[1, 10],
    )
    qrycnt: int = Field(
        default=0,
        title="요청건수 (Requested row count)",
        description="Number of rows to request. Maximum 500 per LS source.",
        examples=[50, 500],
    )
    nday: str = Field(
        default="",
        title="조회영업일수 (Business-day query mode)",
        description=(
            "Business-day query mode. '0' = unused (use date range below); "
            "values >= '1' = use as the number of business days back from "
            "today, per LS source."
        ),
        examples=["0", "1"],
    )
    sdate: str = Field(
        default="",
        title="시작일자 (Start date)",
        description="Start date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    stime: str = Field(
        default="",
        title="시작시간 (Start time)",
        description="Start time placeholder in 'HHMMSS' format. Currently unused per LS source.",
        examples=[""],
    )
    edate: str = Field(
        default="",
        title="종료일자 (End date)",
        description="End date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    etime: str = Field(
        default="",
        title="종료시간 (End time)",
        description="End time placeholder in 'HHMMSS' format. Currently unused per LS source.",
        examples=[""],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor (date component) for paged queries. Empty "
            "on the first request; on follow-ups, pass back the value "
            "returned in the previous response. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description=(
            "Continuation cursor (time component) for paged queries. Empty "
            "on the first request. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    comp_yn: Literal["N"] = Field(
        default="N",
        title="압축여부 (Compression flag)",
        description="Compression flag. Always 'N' (non-compressed); LS OpenAPI does not support compressed responses for t8453.",
        examples=["N"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합)."
        ),
        examples=["K", "N", "U"],
    )


class T8453OutBlock(BaseModel):
    """t8453OutBlock — chart metadata block (previous-day / today snapshot, session timing, continuation keys)."""

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code echoed for the queried issue.",
        examples=["005930"],
    )
    jisiga: int = Field(
        default=0,
        title="전일시가 (Previous-day open)",
        description="Previous trading day's opening price. Decimal scale not declared in available source.",
        examples=[78000],
    )
    jihigh: int = Field(
        default=0,
        title="전일고가 (Previous-day high)",
        description="Previous trading day's high price.",
        examples=[79500],
    )
    jilow: int = Field(
        default=0,
        title="전일저가 (Previous-day low)",
        description="Previous trading day's low price.",
        examples=[77800],
    )
    jiclose: int = Field(
        default=0,
        title="전일종가 (Previous-day close)",
        description="Previous trading day's closing price.",
        examples=[79000],
    )
    jivolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's traded volume in shares.",
        examples=[15000000],
    )
    disiga: int = Field(
        default=0,
        title="당일시가 (Today open)",
        description="Today's opening price.",
        examples=[79100],
    )
    dihigh: int = Field(
        default=0,
        title="당일고가 (Today high)",
        description="Today's high price as of the response time.",
        examples=[80000],
    )
    dilow: int = Field(
        default=0,
        title="당일저가 (Today low)",
        description="Today's low price as of the response time.",
        examples=[78900],
    )
    diclose: int = Field(
        default=0,
        title="당일종가 (Today close)",
        description="Today's last price (close once the session ends).",
        examples=[79800],
    )
    highend: int = Field(
        default=0,
        title="상한가 (Upper limit price)",
        description="Daily upper price limit (상한가) for the issue.",
        examples=[102700],
    )
    lowend: int = Field(
        default=0,
        title="하한가 (Lower limit price)",
        description="Daily lower price limit (하한가) for the issue.",
        examples=[55300],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor (date component) for the next paged "
            "request. Empty when no further history is available. Treat as "
            "opaque LS-defined token."
        ),
        examples=[""],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description="Continuation cursor (time component) for the next paged request.",
        examples=[""],
    )
    s_time: str = Field(
        default="",
        title="장시작시간 (Session start time)",
        description="Regular session start time in 'HHMMSS' format.",
        examples=["090000"],
    )
    e_time: str = Field(
        default="",
        title="장종료시간 (Session end time)",
        description="Regular session end time in 'HHMMSS' format.",
        examples=["153000"],
    )
    dshmin: str = Field(
        default="",
        title="동시호가처리시간 (Single-price auction window length)",
        description="Length of the single-price auction window in 'MM' (minutes), per LS source label '분'.",
        examples=["10"],
    )
    rec_count: int = Field(
        default=0,
        title="레코드카운트 (Record count)",
        description="Number of rows in ``OutBlock1`` for this response.",
        examples=[50, 500],
    )
    nxt_fm_s_time: str = Field(
        default="",
        title="NXT프리마켓장시작시간 (NXT premarket start time)",
        description="NXT premarket session start time in 'HHMMSS' format. Empty when not applicable.",
        examples=[""],
    )
    nxt_fm_e_time: str = Field(
        default="",
        title="NXT프리마켓장종료시간 (NXT premarket end time)",
        description="NXT premarket session end time in 'HHMMSS' format.",
        examples=[""],
    )
    nxt_fm_dshmin: str = Field(
        default="",
        title="NXT프리마켓동시호가처리시간 (NXT premarket single-price auction window length)",
        description="NXT premarket single-price auction window length in minutes ('MM').",
        examples=[""],
    )
    nxt_am_s_time: str = Field(
        default="",
        title="NXT에프터마켓장시작시간 (NXT aftermarket start time)",
        description="NXT aftermarket session start time in 'HHMMSS' format.",
        examples=[""],
    )
    nxt_am_e_time: str = Field(
        default="",
        title="NXT에프터마켓장종료시간 (NXT aftermarket end time)",
        description="NXT aftermarket session end time in 'HHMMSS' format.",
        examples=[""],
    )
    nxt_am_dshmin: str = Field(
        default="",
        title="NXT에프터마켓동시호가처리시간 (NXT aftermarket single-price auction window length)",
        description="NXT aftermarket single-price auction window length in minutes ('MM').",
        examples=[""],
    )


class T8453OutBlock1(BaseModel):
    """t8453OutBlock1 — per-bar OHLC row (occurs).

    Decimal scale and time ordering of rows are NOT declared in the source
    available to this codebase; consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="날짜 (Date)",
        description="Bar date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    time: str = Field(
        default="",
        title="시간 (Time)",
        description="Bar time in 'HHMMSS' format.",
        examples=["093001"],
    )
    open: int = Field(
        default=0,
        title="시가 (Open)",
        description="Bar opening price.",
        examples=[78000],
    )
    high: int = Field(
        default=0,
        title="고가 (High)",
        description="Bar high price.",
        examples=[78100],
    )
    low: int = Field(
        default=0,
        title="저가 (Low)",
        description="Bar low price.",
        examples=[77950],
    )
    close: int = Field(
        default=0,
        title="종가 (Close)",
        description="Bar closing price.",
        examples=[78050],
    )
    jdiff_vol: int = Field(
        default=0,
        title="거래량 (Volume)",
        description="Traded volume in shares for the bar.",
        examples=[1000],
    )
    jongchk: int = Field(
        default=0,
        title="수정구분 (Adjustment flag)",
        description=(
            "Adjustment flag indicating whether a corporate-action "
            "adjustment was applied for this bar. Code values not declared "
            "in available source; consume as returned by LS."
        ),
        examples=[0, 1],
    )
    rate: float = Field(
        default=0.0,
        title="수정비율 (Adjustment ratio)",
        description="Adjustment ratio applied to this bar. Scale not declared in available source.",
        examples=[0.0, 1.0],
    )
    pricechk: int = Field(
        default=0,
        title="수정주가반영항목 (Adjusted-price reflection flag)",
        description=(
            "Flag indicating which OHLC fields had the adjustment applied. "
            "Code values not declared in available source."
        ),
        examples=[0, 1],
    )


class T8453Request(BaseModel):
    """t8453 request envelope."""

    header: T8453RequestHeader = T8453RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8453",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8453",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8453Response(BaseModel):
    """t8453 response envelope."""

    header: Optional[T8453ResponseHeader] = None
    cont_block: Optional[T8453OutBlock] = None
    block: list[T8453OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8453RequestHeader",
    "T8453ResponseHeader",
    "T8453InBlock",
    "T8453OutBlock",
    "T8453OutBlock1",
    "T8453Request",
    "T8453Response",
]
