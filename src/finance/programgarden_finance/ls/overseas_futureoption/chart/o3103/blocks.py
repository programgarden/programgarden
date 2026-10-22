"""Pydantic models for LS Securities OpenAPI o3103 (Overseas futures/options intraday minute-bar chart).

o3103 retrieves intraday minute-bar (or 30-second bar) chart data for a
given overseas futures/options symbol. The response carries:

    - ``OutBlock`` — echoed request parameters plus server-side metadata
      (symbol, time-difference, record count, continuation keys).
    - ``OutBlock1`` — list of intraday bar rows (date, local time, OHLCV).

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
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3103.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3103RequestHeader(BlockRequestHeader):
    """o3103 request header. Inherits the standard LS request header schema."""
    pass


class O3103ResponseHeader(BlockResponseHeader):
    """o3103 response header. Inherits the standard LS response header schema."""
    pass


class O3103InBlock(BaseModel):
    """o3103InBlock — input block for the intraday minute-bar chart query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code / symbol)",
        description=(
            "Overseas futures/options short code identifying the instrument "
            "(e.g., 'ADZ25'). Format and length not declared in available source."
        ),
        examples=["ADZ25"],
    )
    ncnt: int = Field(
        ...,
        title="N분주기 (Bar interval in minutes)",
        description=(
            "Bar interval in minutes. '0' = 30-second bar (30초), '1' = 1-minute "
            "bar (1분), '30' = 30-minute bar (30분). Other LS-defined values may "
            "appear; consume as returned by LS."
        ),
        examples=[1, 0, 30],
    )
    readcnt: int = Field(
        ...,
        title="조회건수 (Query record count)",
        description="Number of bar rows to retrieve per request.",
        examples=[20],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation date for paged retrieval in YYYYMMDD format. "
            "Pass empty string for the initial request."
        ),
        examples=["", "20251031"],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description=(
            "Continuation time for paged retrieval in HHMMSS format. "
            "Pass empty string for the initial request."
        ),
        examples=["", "143000"],
    )


class O3103Request(BaseModel):
    """o3103 full request envelope (header + body + setup options)."""

    header: O3103RequestHeader = Field(
        O3103RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3103",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["o3103InBlock"], O3103InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'o3103InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3103"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3103OutBlock(BaseModel):
    """o3103OutBlock — echoed request parameters and server-side metadata.

    LS echoes the request inputs back in OutBlock along with server-side
    metadata such as the time difference and record count. Use this for
    verification and continuation handling — the actual bar rows live in
    ``OutBlock1``.
    """

    shcode: str = Field(
        default="",
        title="단축코드 (Short code / symbol)",
        description="Echoed overseas futures/options short code (e.g., 'ADZ25').",
        examples=["ADZ25"],
    )
    timediff: int = Field(
        default=0,
        title="시차 (Time difference)",
        description=(
            "Time difference reported by LS. Unit and reference not declared "
            "in available source; consume as returned by LS."
        ),
        examples=[0, -9],
    )
    readcnt: int = Field(
        default=0,
        title="조회건수 (Query record count)",
        description="Echoed number of bar rows requested.",
        examples=[20],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description="Continuation date for the next paged request in YYYYMMDD format.",
        examples=["", "20251031"],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description="Continuation time for the next paged request in HHMMSS format.",
        examples=["", "143000"],
    )


class O3103OutBlock1(BaseModel):
    """o3103OutBlock1 — intraday bar row.

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
    time: str = Field(
        default="",
        title="현지시간 (Local time)",
        description=(
            "Local time of the bar in HHMMSS format. Time zone not declared "
            "in available source; consume as returned by LS."
        ),
        examples=["143000", "090000"],
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
        examples=[0.0, 1.2550],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low price)",
        description="Lowest traded price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 1.2480],
    )
    close: float = Field(
        default=0.0,
        title="종가 (Close price)",
        description="Closing price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 1.2510],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description="Trading volume for the bar period.",
        examples=[0, 1500],
    )


class O3103Response(BaseModel):
    """o3103 full response envelope."""

    header: Optional[O3103ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3103OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echoed metadata block)",
        description="Echoed request parameters and server-side metadata.",
    )
    block1: List[O3103OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Intraday bar rows)",
        description="List of intraday bar rows. Time ordering: consume as returned by LS.",
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
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
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
