"""Pydantic models for LS Securities OpenAPI g3202 (Overseas Stock N-tick chart).

g3202 returns N-tick aggregated chart bars for a given overseas-stock symbol
across a date range. The response carries:

    - ``OutBlock`` — input echo + previous/current-day open/high/low/close,
      volume, session times.
    - ``OutBlock1`` — list of N-tick bars (date, local time, OHLC, exec
      volume, adjustment flags, sign).

The TR supports server-side continuation via ``cts_seq``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase. Where the
      Korean spec ends with "등" (etc.), the description states "consume as
      returned by LS" rather than inventing additional enum values.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3202.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3202RequestHeader(BlockRequestHeader):
    """g3202 request header. Inherits the standard LS request header schema."""
    pass


class G3202ResponseHeader(BlockResponseHeader):
    """g3202 response header. Inherits the standard LS response header schema."""
    pass


class G3202InBlock(BaseModel):
    """g3202InBlock — input block for the N-tick chart query."""

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Delay flag. Always 'R' (real-time / 실시간) per LS source.",
        examples=["R"],
    )
    comp_yn: Literal["N"] = Field(
        default="N",
        title="압축여부 (Compression flag)",
        description="Compression flag. Always 'N' (uncompressed) per LS source.",
        examples=["N"],
    )
    keysymbol: str = Field(
        ...,
        title="KEY종목코드 (Key symbol code)",
        description=(
            "LS-internal key symbol code combining exchange code and ticker "
            "(e.g., '82TSLA' = NASDAQ + TSLA)."
        ),
        examples=["82TSLA", "82AAPL"],
    )
    exchcd: str = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description=(
            "Exchange code. '82' = NASDAQ. Other LS-defined codes may "
            "appear; consume as returned by LS."
        ),
        examples=["82"],
    )
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA', 'AAPL').",
        examples=["TSLA", "AAPL"],
    )
    ncnt: int = Field(
        ...,
        title="단위 (N ticks per bar)",
        description="Aggregation unit in number of ticks per bar.",
        examples=[1, 100],
    )
    qrycnt: int = Field(
        ...,
        le=500,
        title="요청건수 (Row count requested)",
        description="Maximum number of rows to return. LS-imposed cap is 500.",
        examples=[100, 500],
    )
    sdate: str = Field(
        ...,
        title="시작일자 (Start date)",
        description="Range start date in YYYYMMDD format.",
        examples=["20231001", "20250414"],
    )
    edate: str = Field(
        ...,
        title="종료일자 (End date)",
        description=(
            "Range end date in YYYYMMDD format. Empty string requests an "
            "open-ended range as defined by LS."
        ),
        examples=["", "20250414"],
    )
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스 (Continuation sequence)",
        description="Continuation cursor for paginated requests. Use 0 for the first call.",
        examples=[0],
    )


class G3202Request(BaseModel):
    """g3202 full request envelope (header + body + setup options)."""

    header: G3202RequestHeader = Field(
        G3202RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3202",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["g3202InBlock"], G3202InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3202InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3202"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3202OutBlock(BaseModel):
    """g3202OutBlock — input echo + range-summary block.

    Carries the input fields LS echoes back together with previous-day and
    current-day OHLCV anchors and the trading-session boundaries. Decimal
    scale and currency unit are not declared in the source available to this
    codebase — consume as returned by LS.
    """

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Echoed delay flag. Always 'R'.",
        examples=["R"],
    )
    keysymbol: str = Field(
        default="",
        title="KEY종목코드 (Key symbol code)",
        description="Echoed LS-internal key symbol code (e.g., '82TSLA').",
        examples=["82TSLA"],
    )
    exchcd: str = Field(
        default="",
        title="거래소코드 (Exchange code)",
        description="Echoed exchange code. '82' = NASDAQ.",
        examples=["82"],
    )
    symbol: str = Field(
        default="",
        title="종목코드 (Symbol / ticker)",
        description="Echoed ticker symbol.",
        examples=["TSLA"],
    )
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스 (Continuation sequence)",
        description="Continuation cursor to feed back on the next paginated call.",
        examples=[0, 12345],
    )
    rec_count: int = Field(
        default=0,
        title="레코드카운트 (Record count)",
        description="Number of rows returned in OutBlock1 for this call.",
        examples=[0, 500],
    )
    preopen: float = Field(
        default=0.0,
        title="전일시가 (Previous day open)",
        description="Previous-day open price.",
        examples=[0.0, 150.25],
    )
    prehigh: float = Field(
        default=0.0,
        title="전일고가 (Previous day high)",
        description="Previous-day high price.",
        examples=[0.0, 152.50],
    )
    prelow: float = Field(
        default=0.0,
        title="전일저가 (Previous day low)",
        description="Previous-day low price.",
        examples=[0.0, 148.00],
    )
    preclose: str = Field(
        default="",
        title="전일종가 (Previous day close)",
        description=(
            "Previous-day close price as a string. Decimal scale not "
            "declared in available source."
        ),
        examples=["150.00", "148.50"],
    )
    prevolume: int = Field(
        default=0,
        title="전일거래량 (Previous day volume)",
        description="Previous-day total trading volume.",
        examples=[0, 1000000],
    )
    open: float = Field(
        default=0.0,
        title="당일시가 (Current day open)",
        description="Current-day open price.",
        examples=[0.0, 151.00],
    )
    high: float = Field(
        default=0.0,
        title="당일고가 (Current day high)",
        description="Current-day high price.",
        examples=[0.0, 153.00],
    )
    low: float = Field(
        default=0.0,
        title="당일저가 (Current day low)",
        description="Current-day low price.",
        examples=[0.0, 149.50],
    )
    close: str = Field(
        default="",
        title="당일종가 (Current day close)",
        description=(
            "Current-day close price as a string. Decimal scale not declared "
            "in available source."
        ),
        examples=["152.00", "150.25"],
    )
    s_time: str = Field(
        default="",
        title="장시작시간 (Session start time)",
        description="Trading session start time in HHMMSS format.",
        examples=["093000", "100000"],
    )
    e_time: str = Field(
        default="",
        title="장종료시간 (Session end time)",
        description="Trading session end time in HHMMSS format.",
        examples=["160000", "150000"],
    )
    last_count: str = Field(
        default="",
        title="마지막Tick건수 (Last-tick count)",
        description=(
            "Number of ticks aggregated into the last bar. Exact semantics "
            "not declared in available source."
        ),
        examples=["", "100"],
    )
    timediff: str = Field(
        default="",
        title="시차 (Time-zone difference)",
        description="Time-zone difference indicator. '0' indicates same time zone as KST.",
        examples=["0"],
    )


class G3202OutBlock1(BaseModel):
    """g3202OutBlock1 — N-tick chart row.

    Decimal scale and time ordering of consecutive rows are not declared in
    the source available to this codebase — consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="날짜 (Date)",
        description="Date of the bar in YYYYMMDD format.",
        examples=["20231001", "20250414"],
    )
    loctime: str = Field(
        default="",
        title="현지시간 (Local time)",
        description="Bar's local exchange time in HHMMSS format.",
        examples=["093015", "150000"],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Open)",
        description="Open price of the bar.",
        examples=[0.0, 150.25],
    )
    high: float = Field(
        default=0.0,
        title="고가 (High)",
        description="High price of the bar.",
        examples=[0.0, 151.00],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low)",
        description="Low price of the bar.",
        examples=[0.0, 149.75],
    )
    close: str = Field(
        default="",
        title="종가 (Close)",
        description=(
            "Close price of the bar as a string. Decimal scale not declared "
            "in available source."
        ),
        examples=["150.50", "151.00"],
    )
    exevol: int = Field(
        default=0,
        title="체결량 (Executed volume)",
        description="Aggregate executed volume in the bar (shares).",
        examples=[0, 12345],
    )
    jongchk: int = Field(
        default=0,
        title="수정구분 (Adjustment flag)",
        description=(
            "Price-adjustment flag for the bar. Enum mapping not fully "
            "declared in available source — consume as returned by LS."
        ),
        examples=[0, 1],
    )
    prtt_rate: float = Field(
        default=0.0,
        title="수정비율 (Adjustment ratio)",
        description="Adjustment ratio applied to the bar (1.0 = no adjustment).",
        examples=[0.0, 1.0],
    )
    pricechk: int = Field(
        default=0,
        title="수정주가반영항목 (Adjusted-price item)",
        description=(
            "Indicator for whether the bar reflects adjusted prices. Enum "
            "mapping not fully declared in available source — consume as "
            "returned by LS."
        ),
        examples=[0, 1],
    )
    sign: str = Field(
        default="",
        title="종가등락구분 (Close-vs-previous sign)",
        description=(
            "Sign indicator for the bar's close vs. the previous bar. "
            "'+' = up, '-' = down. Other LS-defined codes may appear; "
            "consume as returned by LS."
        ),
        examples=["+", "-"],
    )


class G3202Response(BaseModel):
    """g3202 full response envelope."""

    header: Optional[G3202ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3202OutBlock] = Field(
        None,
        title="기본 응답 블록 (Input-echo + range summary)",
        description="Echoed inputs plus prev/current-day OHLCV anchors and session bounds.",
    )
    block1: List[G3202OutBlock1] = Field(
        ...,
        title="상세 리스트 (N-tick chart rows)",
        description="List of N-tick chart rows. Time ordering: consume as returned by LS.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (LS response message)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
