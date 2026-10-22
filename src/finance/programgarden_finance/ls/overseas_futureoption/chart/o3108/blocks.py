"""Pydantic models for LS Securities OpenAPI o3108 (Overseas futures/options daily/weekly/monthly chart).

o3108 retrieves daily, weekly, or monthly OHLCV bar data for a given overseas
futures/options symbol within a date range. The response carries:

    - ``OutBlock`` — echoed request parameters plus prior-session / current-session
      OHLCV reference prices, market open/close times, continuation key, and
      record count.
    - ``OutBlock1`` — list of bar rows (date, OHLCV, volume).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase. Where the
      Korean spec ends with "등" (etc.), the description states "consume as
      returned by LS" rather than inventing additional enum values.
    - Multiplier, tick value, and PnL math are not declared — never inferred.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3108.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3108RequestHeader(BlockRequestHeader):
    """o3108 request header. Inherits the standard LS request header schema."""
    pass


class O3108ResponseHeader(BlockResponseHeader):
    """o3108 response header. Inherits the standard LS response header schema."""
    pass


class O3108InBlock(BaseModel):
    """o3108InBlock — input block for the daily/weekly/monthly chart query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code / symbol)",
        description=(
            "Overseas futures/options short code identifying the instrument "
            "(e.g., 'ADZ25'). Format and length not declared in available source."
        ),
        examples=["ADZ25"],
    )
    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="주기구분 (Period type)",
        description=(
            "Period type. '0' = daily (일), '1' = weekly (주), '2' = monthly (월)."
        ),
        examples=["0", "1", "2"],
    )
    qrycnt: int = Field(
        ...,
        title="요청건수 (Query record count)",
        description="Number of bar rows to retrieve per request.",
        examples=[20],
    )
    sdate: str = Field(
        ...,
        title="시작일자 (Start date)",
        description="Start date of the query range in YYYYMMDD format.",
        examples=["20251031"],
    )
    edate: str = Field(
        ...,
        title="종료일자 (End date)",
        description="End date of the query range in YYYYMMDD format.",
        examples=["20251102"],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation date for paged retrieval in YYYYMMDD format. "
            "Pass empty string for the initial request."
        ),
        examples=["", "20251030"],
    )


class O3108Request(BaseModel):
    """o3108 full request envelope (header + body + setup options)."""

    header: O3108RequestHeader = Field(
        O3108RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3108",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["o3108InBlock"], O3108InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'o3108InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3108"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3108OutBlock(BaseModel):
    """o3108OutBlock — echoed parameters and prior/current session reference prices.

    LS echoes the request inputs and returns prior-session and current-session
    OHLCV reference prices along with market open/close times, continuation key,
    and record count. The actual bar rows live in ``OutBlock1``.
    Decimal scale not declared in available source.
    """

    shcode: str = Field(
        default="",
        title="단축코드 (Short code / symbol)",
        description="Echoed overseas futures/options short code (e.g., 'ADZ25').",
        examples=["ADZ25"],
    )
    jisiga: float = Field(
        default=0.0,
        title="전일시가 (Prior-session open price)",
        description=(
            "Prior-session open price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0.0, 1.2500],
    )
    jihigh: float = Field(
        default=0.0,
        title="전일고가 (Prior-session high price)",
        description=(
            "Prior-session high price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0.0, 1.2600],
    )
    jilow: float = Field(
        default=0.0,
        title="전일저가 (Prior-session low price)",
        description=(
            "Prior-session low price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0.0, 1.2400],
    )
    jiclose: float = Field(
        default=0.0,
        title="전일종가 (Prior-session close price)",
        description=(
            "Prior-session close price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0.0, 1.2490],
    )
    jivolume: Optional[int] = Field(
        default=None,
        title="전일거래량 (Prior-session volume)",
        description="Prior-session trading volume.",
        examples=[None, 50000],
    )
    disiga: Optional[float] = Field(
        default=None,
        title="당일시가 (Current-session open price)",
        description=(
            "Current-session open price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, 1.2510],
    )
    dihigh: Optional[float] = Field(
        default=None,
        title="당일고가 (Current-session high price)",
        description=(
            "Current-session high price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, 1.2600],
    )
    dilow: Optional[float] = Field(
        default=None,
        title="당일저가 (Current-session low price)",
        description=(
            "Current-session low price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, 1.2480],
    )
    diclose: Optional[float] = Field(
        default=None,
        title="당일종가 (Current-session close price)",
        description=(
            "Current-session close price. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, 1.2520],
    )
    mk_stime: Optional[str] = Field(
        default=None,
        title="장시작시간 (Market open time)",
        description=(
            "Market open time in HHMMSS format. Time zone not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, "170000"],
    )
    mk_etime: Optional[str] = Field(
        default=None,
        title="장마감시간 (Market close time)",
        description=(
            "Market close time in HHMMSS format. Time zone not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[None, "160000"],
    )
    cts_date: Optional[str] = Field(
        default=None,
        title="연속일자 (Continuation date)",
        description="Continuation date for the next paged request in YYYYMMDD format.",
        examples=[None, "20251030"],
    )
    rec_count: Optional[int] = Field(
        default=None,
        title="레코드카운트 (Record count)",
        description="Number of bar rows returned in this response.",
        examples=[None, 20],
    )


class O3108OutBlock1(BaseModel):
    """o3108OutBlock1 — daily/weekly/monthly bar row.

    Decimal scale, currency unit, and time ordering of consecutive rows are
    not declared in the source available to this codebase — consume as
    returned by LS. Multiplier and tick value are not declared — never inferred.
    """

    date: str = Field(
        default="",
        title="날짜 (Date)",
        description="Date of the bar in YYYYMMDD format.",
        examples=["20251031", "20251101"],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Open price)",
        description=(
            "Opening price of the bar. Decimal scale not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0.0, 1.2500],
    )
    high: float = Field(
        default=0.0,
        title="고가 (High price)",
        description="Highest traded price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 1.2600],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low price)",
        description="Lowest traded price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 1.2400],
    )
    close: float = Field(
        default=0.0,
        title="종가 (Close price)",
        description="Closing price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 1.2490],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description="Trading volume for the bar period.",
        examples=[0, 50000],
    )


class O3108Response(BaseModel):
    """o3108 full response envelope."""

    header: Optional[O3108ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3108OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echoed metadata block)",
        description="Echoed request parameters and prior/current session reference prices.",
    )
    block1: List[O3108OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Bar rows)",
        description="List of bar rows. Time ordering: consume as returned by LS.",
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
