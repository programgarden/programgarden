"""Pydantic models for LS Securities OpenAPI o3123 (Overseas futures/options intraday bar query).

o3123 returns intraday OHLCV bars (N-minute candles, or 30-second when ncnt=0)
for one overseas futures or options contract. The response uses a two-block
structure: OutBlock holds the continuation cursor; OutBlock1 holds the bar list.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale: NOT declared in source; documented accordingly.
    - Time zone of bar timestamps: NOT declared in source; documented as
      "local exchange time" per source field names (현지시간); consume as returned by LS.
    - Time ordering of OutBlock1 list rows: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3123.py``
      (mktgb='F', shcode='ADZ25', ncnt=1, readcnt=20) plus neutral placeholders.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3123RequestHeader(BlockRequestHeader):
    """o3123 request header. Inherits the standard LS request header schema."""
    pass


class O3123ResponseHeader(BlockResponseHeader):
    """o3123 response header. Inherits the standard LS response header schema."""
    pass


class O3123InBlock(BaseModel):
    """o3123InBlock — input block for the overseas futures/options intraday bar query."""

    mktgb: str = Field(
        ...,
        title="Market type (시장구분)",
        description="Market type. 'F' = futures (선물), 'O' = options (옵션).",
        examples=["F", "O"],
    )
    shcode: str = Field(
        ...,
        title="Short code (단축코드)",
        description="LS short instrument code (e.g., 'ADZ25', 'ESM26').",
        examples=["ADZ25", "ESM26"],
    )
    ncnt: int = Field(
        ...,
        title="Bar interval in minutes (N분주기)",
        description=(
            "Bar interval in minutes. 0 = 30-second bars, 1 = 1-minute bars, "
            "30 = 30-minute bars."
        ),
        examples=[1, 0, 30],
    )
    readcnt: int = Field(
        ...,
        le=500,
        title="Query count (조회갯수)",
        description="Number of bar records to return. Maximum 500.",
        examples=[20, 100],
    )
    cts_date: str = Field(
        "",
        title="Continuation date YYYYMMDD (연속일자)",
        description=(
            "Continuation date for paging in YYYYMMDD format. "
            "Use empty string for the first request."
        ),
        examples=["", "20260315"],
    )
    cts_time: str = Field(
        "",
        title="Continuation time HHMMSS (연속시간)",
        description=(
            "Continuation time for paging in HHMMSS format. "
            "Use empty string for the first request."
        ),
        examples=["", "143000"],
    )


class O3123Request(BaseModel):
    """o3123 full request envelope (header + body + setup options)."""

    header: O3123RequestHeader = Field(
        O3123RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3123",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3123InBlock"], O3123InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3123InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3123"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3123OutBlock(BaseModel):
    """o3123OutBlock — continuation control and metadata block."""

    shcode: str = Field(
        default="",
        title="Short code (단축코드)",
        description="Echoed short instrument code.",
        examples=["ADZ25", "ESM26"],
    )
    timediff: int = Field(
        default=0,
        title="Time difference (시차)",
        description=(
            "Time difference between local exchange time and Korean time. "
            "Unit not declared in available source; consume as returned by LS."
        ),
        examples=[-9, 0],
    )
    readcnt: int = Field(
        default=0,
        title="Actual record count (조회갯수)",
        description="Actual number of bar records returned.",
        examples=[20, 100],
    )
    cts_date: str = Field(
        default="",
        title="Continuation date YYYYMMDD (연속일자)",
        description=(
            "Continuation date for the next page request (YYYYMMDD). "
            "Empty when no more data is available."
        ),
        examples=["", "20260315"],
    )
    cts_time: str = Field(
        default="",
        title="Continuation time HHMMSS (연속시간)",
        description=(
            "Continuation time for the next page request (HHMMSS). "
            "Empty when no more data is available."
        ),
        examples=["", "143000"],
    )


class O3123OutBlock1(BaseModel):
    """o3123OutBlock1 — one intraday bar record.

    Decimal scale is not declared in the source available to this codebase.
    Time ordering: consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="Date YYYYMMDD (날짜)",
        description="Bar date in YYYYMMDD format.",
        examples=["20260315", "20250808"],
    )
    time: str = Field(
        default="",
        title="Local time HHMMSS (현지시간)",
        description=(
            "Bar time in local exchange time (HHMMSS). "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["143000", "093000"],
    )
    open: float = Field(
        default=0.0,
        title="Open price (시가)",
        description=(
            "Opening price of the bar. "
            "Decimal scale not declared in available source."
        ),
        examples=[5790.0, 4.22],
    )
    high: float = Field(
        default=0.0,
        title="High price (고가)",
        description="Highest traded price of the bar.",
        examples=[5810.0, 4.25],
    )
    low: float = Field(
        default=0.0,
        title="Low price (저가)",
        description="Lowest traded price of the bar.",
        examples=[5775.0, 4.21],
    )
    close: float = Field(
        default=0.0,
        title="Close price (종가)",
        description="Closing price of the bar.",
        examples=[5800.25, 4.235],
    )
    volume: int = Field(
        default=0,
        title="Volume (거래량)",
        description="Trading volume for the bar (contracts).",
        examples=[1500, 8000],
    )


class O3123Response(BaseModel):
    """o3123 full response envelope."""

    header: Optional[O3123ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3123OutBlock] = Field(
        None,
        title="Continuation block (기본 응답 블록)",
        description="Continuation control and metadata block.",
    )
    block1: List[O3123OutBlock1] = Field(
        ...,
        title="Bar list (상세 리스트)",
        description=(
            "List of intraday OHLCV bar records. "
            "Time ordering: consume as returned by LS."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류메시지)",
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
