"""Pydantic models for LS Securities OpenAPI t8451 (Domestic Stock day/week/month/year chart).

t8451 returns OHLCV chart data for a domestic stock symbol at one of four
period types (daily / weekly / monthly / yearly). The response carries:

    - ``OutBlock`` (``block``) — chart metadata: previous-day OHLCV,
      today's OHLCV, daily limits, session timing constants, NXT premarket /
      aftermarket session timing, and the continuation key (``cts_date``).
    - ``OutBlock1`` (``block1``) — list of period rows (date, OHLC, volume,
      value, adjustment-related fields, sign).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS. Domestic stock prices in LS feeds are typically
      integer KRW per share, but this is not asserted as a contract.
    - ``cts_date`` is the LS continuation cursor; pass back verbatim on
      follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t8451.py``.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8451RequestHeader(BlockRequestHeader):
    """t8451 request header. Inherits the standard LS request header schema."""
    pass


class T8451ResponseHeader(BlockResponseHeader):
    """t8451 response header. Inherits the standard LS response header schema."""
    pass


class T8451InBlock(BaseModel):
    """t8451InBlock — input block for the day/week/month/year chart query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code (e.g., '005930' for Samsung Electronics).",
        examples=["005930", "010950"],
    )
    gubun: Literal["2", "3", "4", "5"] = Field(
        default="2",
        title="주기구분 (Period type)",
        description="Period type. '2' = daily (일), '3' = weekly (주), '4' = monthly (월), '5' = yearly (년).",
        examples=["2", "3", "4", "5"],
    )
    qrycnt: int = Field(
        default=500,
        title="요청건수 (Requested row count)",
        description="Number of rows to request. Maximum 500 per LS source.",
        examples=[10, 500],
    )
    sdate: str = Field(
        default="",
        title="시작일자 (Start date)",
        description=(
            "Start date in 'YYYYMMDD' format. Empty string means LS treats "
            "the request as 'fetch ``qrycnt`` rows ending at ``edate``'."
        ),
        examples=["", "20260101"],
    )
    edate: str = Field(
        default="99999999",
        title="종료일자 (End date)",
        description=(
            "End date in 'YYYYMMDD' format. Use '99999999' or today's date "
            "for the initial request (most recent rows)."
        ),
        examples=["99999999", "20260228"],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor for paged queries. Empty on the first "
            "request; on follow-ups, pass back the ``cts_date`` returned in "
            "the previous response. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    comp_yn: Literal["N"] = Field(
        default="N",
        title="압축여부 (Compression flag)",
        description="Compression flag. Always 'N' (non-compressed); LS OpenAPI does not support compressed responses for t8451.",
        examples=["N"],
    )
    sujung: Literal["Y", "N"] = Field(
        default="N",
        title="수정주가여부 (Adjusted-price flag)",
        description="Adjusted-price flag. 'Y' = apply corporate-action adjustments (수정주가 적용), 'N' = raw prices (비적용).",
        examples=["N", "Y"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX (한국거래소), 'N' = NXT "
            "(넥스트레이드), 'U' = unified (통합). Other values are treated "
            "as KRX per LS source."
        ),
        examples=["K", "N", "U"],
    )


class T8451Request(BaseModel):
    """t8451 request envelope."""

    header: T8451RequestHeader = T8451RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8451",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t8451InBlock"], T8451InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8451"
    )


class T8451OutBlock(BaseModel):
    """t8451OutBlock — chart metadata block (previous-day / today snapshot, session timing, continuation key)."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code echoed for the queried issue.",
        examples=["005930"],
    )
    jisiga: int = Field(
        ...,
        title="전일시가 (Previous-day open)",
        description="Previous trading day's opening price. Decimal scale not declared in available source.",
        examples=[78000],
    )
    jihigh: int = Field(
        ...,
        title="전일고가 (Previous-day high)",
        description="Previous trading day's high price.",
        examples=[79500],
    )
    jilow: int = Field(
        ...,
        title="전일저가 (Previous-day low)",
        description="Previous trading day's low price.",
        examples=[77800],
    )
    jiclose: int = Field(
        ...,
        title="전일종가 (Previous-day close)",
        description="Previous trading day's closing price.",
        examples=[79000],
    )
    jivolume: int = Field(
        ...,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's traded volume in shares.",
        examples=[15000000],
    )
    disiga: int = Field(
        ...,
        title="당일시가 (Today open)",
        description="Today's opening price.",
        examples=[79100],
    )
    dihigh: int = Field(
        ...,
        title="당일고가 (Today high)",
        description="Today's high price as of the response time.",
        examples=[80000],
    )
    dilow: int = Field(
        ...,
        title="당일저가 (Today low)",
        description="Today's low price as of the response time.",
        examples=[78900],
    )
    diclose: int = Field(
        ...,
        title="당일종가 (Today close)",
        description="Today's last price (close once the session ends).",
        examples=[79800],
    )
    highend: int = Field(
        ...,
        title="상한가 (Upper limit price)",
        description="Daily upper price limit (상한가) for the issue.",
        examples=[102700],
    )
    lowend: int = Field(
        ...,
        title="하한가 (Lower limit price)",
        description="Daily lower price limit (하한가) for the issue.",
        examples=[55300],
    )
    cts_date: str = Field(
        ...,
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor for the next paged request. Empty when no "
            "further history is available. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    s_time: str = Field(
        ...,
        title="장시작시간 (Session start time)",
        description="Regular session start time in 'HHMMSS' format.",
        examples=["090000"],
    )
    e_time: str = Field(
        ...,
        title="장종료시간 (Session end time)",
        description="Regular session end time in 'HHMMSS' format.",
        examples=["153000"],
    )
    dshmin: str = Field(
        ...,
        title="동시호가처리시간 (Single-price auction window length)",
        description="Length of the single-price auction window in 'MM' (minutes), per LS source label '분'.",
        examples=["10"],
    )
    rec_count: int = Field(
        ...,
        title="레코드카운트 (Record count)",
        description="Number of rows in ``OutBlock1`` for this response.",
        examples=[10, 500],
    )
    svi_uplmtprice: int = Field(
        ...,
        title="정적VI상한가 (Static VI upper-limit price)",
        description="Static volatility-interruption upper-limit price for the issue.",
        examples=[87000],
    )
    svi_dnlmtprice: int = Field(
        ...,
        title="정적VI하한가 (Static VI lower-limit price)",
        description="Static volatility-interruption lower-limit price for the issue.",
        examples=[71000],
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


class T8451OutBlock1(BaseModel):
    """t8451OutBlock1 — per-period OHLCV row (occurs).

    Decimal scale and time ordering of rows are NOT declared in the source
    available to this codebase; consume as returned by LS.
    """

    date: str = Field(
        ...,
        title="날짜 (Date)",
        description="Period date in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    open: int = Field(
        ...,
        title="시가 (Open)",
        description="Period opening price.",
        examples=[78000],
    )
    high: int = Field(
        ...,
        title="고가 (High)",
        description="Period high price.",
        examples=[79500],
    )
    low: int = Field(
        ...,
        title="저가 (Low)",
        description="Period low price.",
        examples=[77800],
    )
    close: int = Field(
        ...,
        title="종가 (Close)",
        description="Period closing price.",
        examples=[79000],
    )
    jdiff_vol: int = Field(
        ...,
        title="거래량 (Volume)",
        description="Traded volume in shares for the period.",
        examples=[15000000],
    )
    value: int = Field(
        ...,
        title="거래대금 (Trade value)",
        description=(
            "Traded value (price × volume) for the period. Decimal scale "
            "not declared in available source; consume as returned by LS."
        ),
        examples=[1185000000000],
    )
    jongchk: int = Field(
        ...,
        title="수정구분 (Adjustment flag)",
        description=(
            "Adjustment flag indicating whether a corporate-action "
            "adjustment was applied for this row. Code values not declared "
            "in available source; consume as returned by LS."
        ),
        examples=[0, 1],
    )
    rate: float = Field(
        ...,
        title="수정비율 (Adjustment ratio)",
        description="Adjustment ratio applied to this row. Scale not declared in available source.",
        examples=[0.0, 1.0],
    )
    pricechk: int = Field(
        ...,
        title="수정주가반영항목 (Adjusted-price reflection flag)",
        description=(
            "Flag indicating which OHLC fields had the adjustment applied. "
            "Code values not declared in available source."
        ),
        examples=[0, 1],
    )
    ratevalue: int = Field(
        ...,
        title="수정비율반영거래대금 (Adjustment-applied trade value)",
        description="Trade value with the adjustment ratio applied.",
        examples=[1185000000000],
    )
    sign: str = Field(
        ...,
        title="종가등락구분 (Close direction)",
        description=(
            "Close direction code. '1' = upper limit (상한), '2' = up (상승), "
            "'3' = unchanged (보합), '4' = lower limit (하한), '5' = down "
            "(하락). Stock-only field per LS source."
        ),
        examples=["2", "3", "5"],
    )


class T8451Response(BaseModel):
    """t8451 response envelope."""

    header: Optional[T8451ResponseHeader]
    block: Optional[T8451OutBlock] = Field(
        None,
        title="차트 기본 정보 (Chart metadata block)",
        description="Chart metadata block (previous-day / today snapshot, session timing, continuation key).",
    )
    block1: List[T8451OutBlock1] = Field(
        default_factory=list,
        title="차트 OHLCV 데이터 (Chart OHLCV rows)",
        description="List of per-period OHLCV rows. Time ordering not declared in available source.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
