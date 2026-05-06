"""Pydantic models for LS Securities OpenAPI g3204 (Overseas Stock day/week/month/year chart).

g3204 returns aggregated daily / weekly / monthly / yearly chart bars for a
given overseas-stock symbol across a date range with optional adjusted-price
support. The response carries:

    - ``OutBlock`` — input echo + previous/current-day OHLCV anchors,
      up/down limits, session bounds, and same-time-quote handling time.
    - ``OutBlock1`` — list of bars (date, OHLC, volume, trading amount,
      adjustment flags, sign).

The TR supports server-side continuation via the ``cts_date`` /
``cts_info`` cursor pair.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase. Where the
      Korean spec ends with "등" (etc.), the description states "consume as
      returned by LS" rather than inventing additional enum values.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3204.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3204RequestHeader(BlockRequestHeader):
    """g3204 request header. Inherits the standard LS request header schema."""
    pass


class G3204ResponseHeader(BlockResponseHeader):
    """g3204 response header. Inherits the standard LS response header schema."""
    pass


class G3204InBlock(BaseModel):
    """g3204InBlock — input block for the day/week/month/year chart query."""

    sujung: Literal["Y", "N"] = Field(
        default="Y",
        title="수정주가여부 (Adjusted-price flag)",
        description="Adjusted-price flag. 'Y' = apply adjustments (적용), 'N' = raw prices (비적용).",
        examples=["Y", "N"],
    )
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
    gubun: Literal["2", "3", "4", "5"] = Field(
        ...,
        title="주기구분 (Period type)",
        description=(
            "Period type. '2' = daily (일), '3' = weekly (주), '4' = monthly "
            "(월), '5' = yearly (년)."
        ),
        examples=["2", "3", "4", "5"],
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
        examples=["20230203"],
    )
    edate: str = Field(
        ...,
        title="종료일자 (End date)",
        description="Range end date in YYYYMMDD format.",
        examples=["20250505"],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor — date in YYYYMMDD format. Empty string for "
            "the first call; subsequent paginated calls reuse the value LS "
            "returns in the OutBlock."
        ),
        examples=["", "20240101"],
    )
    cts_info: str = Field(
        default="",
        title="연속정보 (Continuation info)",
        description="Continuation cursor — opaque LS-returned string. Empty string for the first call.",
        examples=[""],
    )


class G3204Request(BaseModel):
    """g3204 full request envelope (header + body + setup options)."""

    header: G3204RequestHeader = Field(
        G3204RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3204",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["g3204InBlock"], G3204InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3204InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=3,
            on_rate_limit="wait",
            rate_limit_key="g3204"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3204OutBlock(BaseModel):
    """g3204OutBlock — input echo + range-summary block.

    Carries the input fields LS echoes back together with previous-day and
    current-day OHLCV anchors, daily up/down limits, session bounds, and the
    same-time-quote handling time. Decimal scale and currency unit are not
    declared in the source available to this codebase — consume as returned
    by LS.
    """

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Echoed delay flag. Always 'R'.",
        examples=["R"],
    )
    keysymbol: str = Field(
        ...,
        title="KEY종목코드 (Key symbol code)",
        description="Echoed LS-internal key symbol code (e.g., '82TSLA').",
        examples=["82TSLA"],
    )
    exchcd: str = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description="Echoed exchange code. '82' = NASDAQ.",
        examples=["82"],
    )
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Echoed ticker symbol.",
        examples=["TSLA"],
    )
    cts_date: str = Field(
        ...,
        title="연속일자 (Continuation date)",
        description="Continuation date in YYYYMMDD format to feed back on the next paginated call.",
        examples=["", "20240101"],
    )
    cts_info: str = Field(
        ...,
        title="연속정보 (Continuation info)",
        description="Continuation opaque string to feed back on the next paginated call.",
        examples=[""],
    )
    rec_count: int = Field(
        ...,
        title="레코드카운트 (Record count)",
        description="Number of rows returned in OutBlock1 for this call.",
        examples=[0, 500],
    )
    preopen: float = Field(
        ...,
        title="전일시가 (Previous day open)",
        description="Previous-day open price.",
        examples=[0.0, 150.25],
    )
    prehigh: float = Field(
        ...,
        title="전일고가 (Previous day high)",
        description="Previous-day high price.",
        examples=[0.0, 152.50],
    )
    prelow: float = Field(
        ...,
        title="전일저가 (Previous day low)",
        description="Previous-day low price.",
        examples=[0.0, 148.00],
    )
    preclose: str = Field(
        ...,
        title="전일종가 (Previous day close)",
        description=(
            "Previous-day close price as a string. Decimal scale not "
            "declared in available source."
        ),
        examples=["150.00"],
    )
    prevolume: int = Field(
        ...,
        title="전일거래량 (Previous day volume)",
        description="Previous-day total trading volume.",
        examples=[0, 1000000],
    )
    open: float = Field(
        ...,
        title="당일시가 (Current day open)",
        description="Current-day open price.",
        examples=[0.0, 151.00],
    )
    high: float = Field(
        ...,
        title="당일고가 (Current day high)",
        description="Current-day high price.",
        examples=[0.0, 153.00],
    )
    low: float = Field(
        ...,
        title="당일저가 (Current day low)",
        description="Current-day low price.",
        examples=[0.0, 149.50],
    )
    close: str = Field(
        ...,
        title="당일종가 (Current day close)",
        description=(
            "Current-day close price as a string. Decimal scale not declared "
            "in available source."
        ),
        examples=["152.00"],
    )
    uplimit: str = Field(
        ...,
        title="상한가 (Upper price limit)",
        description=(
            "Daily upper price limit (상한가) as a string. Decimal scale and "
            "applicability per market not declared in available source."
        ),
        examples=["", "200.00"],
    )
    dnlimit: str = Field(
        ...,
        title="하한가 (Lower price limit)",
        description=(
            "Daily lower price limit (하한가) as a string. Decimal scale and "
            "applicability per market not declared in available source."
        ),
        examples=["", "100.00"],
    )
    s_time: str = Field(
        ...,
        title="장시작시간 (Session start time)",
        description="Trading session start time in HHMMSS format.",
        examples=["093000"],
    )
    e_time: str = Field(
        ...,
        title="장종료시간 (Session end time)",
        description="Trading session end time in HHMMSS format.",
        examples=["160000"],
    )
    dshmin: str = Field(
        ...,
        title="동시호가처리시간 (Same-time-quote handling time)",
        description=(
            "Same-time-quote (동시호가) processing time in HHMMSS format. "
            "Applicability per market not declared in available source."
        ),
        examples=["", "093000"],
    )


class G3204OutBlock1(BaseModel):
    """g3204OutBlock1 — period chart row.

    Decimal scale and time ordering of consecutive rows are not declared in
    the source available to this codebase — consume as returned by LS.
    """

    date: str = Field(
        ...,
        title="날짜 (Date)",
        description="Date of the bar in YYYYMMDD format.",
        examples=["20230203", "20250505"],
    )
    open: float = Field(
        ...,
        title="시가 (Open)",
        description="Open price of the bar.",
        examples=[0.0, 150.25],
    )
    high: float = Field(
        ...,
        title="고가 (High)",
        description="High price of the bar.",
        examples=[0.0, 151.00],
    )
    low: float = Field(
        ...,
        title="저가 (Low)",
        description="Low price of the bar.",
        examples=[0.0, 149.75],
    )
    close: float = Field(
        ...,
        title="종가 (Close)",
        description="Close price of the bar.",
        examples=[0.0, 150.50],
    )
    volume: int = Field(
        ...,
        title="거래량 (Volume)",
        description="Trading volume aggregated for the bar (shares).",
        examples=[0, 12345],
    )
    amount: int = Field(
        ...,
        title="거래대금 (Trading amount)",
        description=(
            "Trading amount aggregated for the bar. Currency / scale not "
            "declared in available source."
        ),
        examples=[0, 1850000],
    )
    jongchk: int = Field(
        ...,
        title="수정구분 (Adjustment flag)",
        description=(
            "Price-adjustment flag for the bar. '0' = no adjustment, "
            "'1' = adjustment applied. Other LS-defined codes may appear; "
            "consume as returned by LS."
        ),
        examples=[0, 1],
    )
    prtt_rate: float = Field(
        ...,
        title="수정비율 (Adjustment ratio)",
        description="Adjustment ratio applied to the bar (1.0 = no adjustment).",
        examples=[0.0, 1.0],
    )
    pricechk: int = Field(
        ...,
        title="수정주가반영항목 (Adjusted-price item)",
        description=(
            "Indicator for whether the bar reflects adjusted prices. "
            "'0' = not applied, '1' = applied. Other LS-defined codes may "
            "appear; consume as returned by LS."
        ),
        examples=[0, 1],
    )
    ratevalue: int = Field(
        ...,
        title="수정비율반영거래대금 (Adjustment-applied trading amount)",
        description=(
            "Trading amount with the adjustment ratio applied. Currency / "
            "scale not declared in available source."
        ),
        examples=[0, 1850000],
    )
    sign: str = Field(
        ...,
        title="종가등락구분 (Close-vs-previous sign)",
        description=(
            "Sign indicator for the bar's close vs. the previous bar. "
            "'+' = up, '-' = down. Other LS-defined codes may appear; "
            "consume as returned by LS."
        ),
        examples=["+", "-"],
    )


class G3204Response(BaseModel):
    """g3204 full response envelope."""

    header: Optional[G3204ResponseHeader] = Field(
        default=None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3204OutBlock] = Field(
        default=None,
        title="기본 응답 블록 (Input-echo + range summary)",
        description="Echoed inputs plus prev/current-day OHLCV anchors, limits, and session bounds.",
    )
    block1: List[G3204OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Period chart rows)",
        description="List of period chart rows. Time ordering: consume as returned by LS.",
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
        default=None,
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
