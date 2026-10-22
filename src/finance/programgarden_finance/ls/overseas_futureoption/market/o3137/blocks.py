"""Pydantic models for LS Securities OpenAPI o3137 (Overseas futures/options N-tick bar query).

o3137 returns N-tick OHLCV bars for one overseas futures or options contract.
The response uses a two-block structure: OutBlock holds summary and continuation
fields; OutBlock1 holds the bar list.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale: NOT declared in source; documented accordingly.
    - Time zone of bar timestamps: NOT declared in source; consume as returned by LS.
    - Time ordering of OutBlock1 list rows: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3137.py``
      (mktgb='F', shcode='ADM23', ncnt=1, qrycnt=20) plus neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3137RequestHeader(BlockRequestHeader):
    """o3137 request header. Inherits the standard LS request header schema."""
    pass


class O3137ResponseHeader(BlockResponseHeader):
    """o3137 response header. Inherits the standard LS response header schema."""
    pass


class O3137InBlock(BaseModel):
    """o3137InBlock — input block for the overseas futures/options N-tick bar query."""

    mktgb: Literal["F", "O"] = Field(
        ...,
        title="Market type (시장구분)",
        description="Market type. 'F' = futures (선물), 'O' = options (옵션).",
        examples=["F", "O"],
    )
    shcode: str = Field(
        ...,
        title="Short code (단축코드)",
        description="LS short instrument code (e.g., 'ADM23', 'ESM26').",
        examples=["ADM23", "ESM26"],
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
    qrycnt: int = Field(
        ...,
        le=500,
        title="Query count (조회갯수)",
        description="Number of bar records to return. Maximum 500.",
        examples=[20, 100],
    )
    cts_seq: str = Field(
        "",
        title="Continuation sequence (연속시간)",
        description=(
            "Continuation sequence/time value for paging. "
            "Use empty string for the first request; use the returned cts_seq for subsequent requests."
        ),
        examples=["", "14300500001"],
    )
    cts_daygb: str = Field(
        "",
        title="Continuation day classification (연속당일구분)",
        description=(
            "Day classification for continuation paging. "
            "Use empty string for the first request."
        ),
        examples=["", "0"],
    )


class O3137Request(BaseModel):
    """o3137 full request envelope (header + body + setup options)."""

    header: O3137RequestHeader = Field(
        O3137RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3137",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3137InBlock"], O3137InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3137InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3137"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3137OutBlock(BaseModel):
    """o3137OutBlock — summary and continuation control block."""

    shcode: str = Field(
        default="",
        title="Short code (단축코드)",
        description="Echoed short instrument code.",
        examples=["ADM23", "ESM26"],
    )
    rec_count: int = Field(
        default=0,
        title="Record count (레코드카운트)",
        description="Number of bar records returned in OutBlock1.",
        examples=[20, 100],
    )
    cts_seq: str = Field(
        default="",
        title="Continuation sequence (연속시간)",
        description=(
            "Continuation sequence/time value for the next page request. "
            "Empty when no more data is available."
        ),
        examples=["", "14300500001"],
    )
    cts_daygb: str = Field(
        default="",
        title="Continuation day classification (연속당일구분)",
        description=(
            "Day classification for the next page request. "
            "Empty when no more data is available."
        ),
        examples=["", "0"],
    )


class O3137OutBlock1(BaseModel):
    """o3137OutBlock1 — one N-tick bar record.

    Decimal scale is not declared in the source available to this codebase.
    Time ordering: consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="Date YYYYMMDD (날짜)",
        description="Bar date in YYYYMMDD format.",
        examples=["20230601", "20260315"],
    )
    time: str = Field(
        default="",
        title="Time HHMMSS (시간)",
        description=(
            "Bar end time in HHMMSS format. "
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
        examples=[5775.0, 4.20],
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


class O3137Response(BaseModel):
    """o3137 full response envelope."""

    header: Optional[O3137ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3137OutBlock] = Field(
        None,
        title="Summary block (기본 응답 블록)",
        description="Summary and continuation control block.",
    )
    block1: List[O3137OutBlock1] = Field(
        ...,
        title="Bar list (상세 리스트)",
        description=(
            "List of N-tick OHLCV bar records. "
            "Time ordering: consume as returned by LS."
        ),
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
