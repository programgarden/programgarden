"""Pydantic models for LS Securities OpenAPI o3117 (Overseas futures/options tick chart).

o3117 retrieves tick-based chart data for a given overseas futures/options symbol.
The response carries:

    - ``OutBlock`` — echoed request parameters plus server-side metadata
      (symbol, record count, continuation sequence, continuation day flag).
    - ``OutBlock1`` — list of tick-bar rows (date, time, OHLCV).

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
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3117.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3117RequestHeader(BlockRequestHeader):
    """o3117 request header. Inherits the standard LS request header schema."""
    pass


class O3117ResponseHeader(BlockResponseHeader):
    """o3117 response header. Inherits the standard LS response header schema."""
    pass


class O3117InBlock(BaseModel):
    """o3117InBlock — input block for the tick chart query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code / symbol)",
        description=(
            "Overseas futures/options short code identifying the instrument "
            "(e.g., 'CUSU25'). Format and length not declared in available source."
        ),
        examples=["CUSU25"],
    )
    ncnt: int = Field(
        ...,
        title="단위 (Tick unit)",
        description=(
            "Tick aggregation unit. '0' = NTick (N틱 등). Other LS-defined values "
            "may appear; consume as returned by LS."
        ),
        examples=[0, 1],
    )
    qrycnt: int = Field(
        ...,
        title="조회건수 (Query record count)",
        description="Number of tick-bar rows to retrieve per request.",
        examples=[20],
    )
    cts_seq: str = Field(
        default="",
        title="순번CTS (Continuation sequence)",
        description=(
            "Continuation sequence key for paged retrieval. "
            "Pass empty string for the initial request."
        ),
        examples=["", "00001234"],
    )
    cts_daygb: str = Field(
        default="",
        title="당일구분CTS (Continuation day flag)",
        description=(
            "Continuation day flag for paged retrieval. "
            "Pass empty string for the initial request."
        ),
        examples=["", "0"],
    )


class O3117Request(BaseModel):
    """o3117 full request envelope (header + body + setup options)."""

    header: O3117RequestHeader = Field(
        O3117RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3117",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["o3117InBlock"], O3117InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'o3117InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3117"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3117OutBlock(BaseModel):
    """o3117OutBlock — echoed request parameters and server-side metadata.

    LS echoes the request inputs back in OutBlock along with the record count
    and continuation keys for paged retrieval. The actual tick-bar rows live
    in ``OutBlock1``.
    """

    shcode: str = Field(
        default="",
        title="단축코드 (Short code / symbol)",
        description="Echoed overseas futures/options short code (e.g., 'CUSU25').",
        examples=["CUSU25"],
    )
    rec_count: int = Field(
        default=0,
        title="레코드카운트 (Record count)",
        description="Number of tick-bar rows returned in this response.",
        examples=[0, 20],
    )
    cts_seq: str = Field(
        default="",
        title="순번CTS (Continuation sequence)",
        description="Continuation sequence key for the next paged request.",
        examples=["", "00001234"],
    )
    cts_daygb: str = Field(
        default="",
        title="당일구분CTS (Continuation day flag)",
        description="Continuation day flag for the next paged request.",
        examples=["", "0"],
    )


class O3117OutBlock1(BaseModel):
    """o3117OutBlock1 — tick-bar row.

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
        title="시간 (Time)",
        description=(
            "Time of the bar in HHMMSS format. Time zone not declared in "
            "available source; consume as returned by LS."
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
        examples=[0.0, 3.2500],
    )
    high: float = Field(
        default=0.0,
        title="고가 (High price)",
        description="Highest traded price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 3.2550],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low price)",
        description="Lowest traded price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 3.2480],
    )
    close: float = Field(
        default=0.0,
        title="종가 (Close price)",
        description="Closing price of the bar. Decimal scale not declared in available source.",
        examples=[0.0, 3.2510],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description="Trading volume for the bar period.",
        examples=[0, 200],
    )


class O3117Response(BaseModel):
    """o3117 full response envelope."""

    header: Optional[O3117ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3117OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echoed metadata block)",
        description="Echoed request parameters and server-side metadata.",
    )
    block1: List[O3117OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Tick-bar rows)",
        description="List of tick-bar rows. Time ordering: consume as returned by LS.",
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
