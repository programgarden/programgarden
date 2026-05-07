"""Pydantic models for LS Securities OpenAPI o3136 (Overseas futures/options intraday tick query).

o3136 returns an intraday tick-by-tick list for one overseas futures or options
contract. Supports both today (당일) and previous day (전일) queries. The
response uses a two-block structure: OutBlock holds the continuation sequence
number; OutBlock1 holds the tick records.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit: NOT declared in source; documented accordingly.
    - ``sign`` enum codes: consume as returned by LS.
    - Time ordering of OutBlock1 list rows: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3136.py``
      (gubun='0', mktgb='F', shcode='', readcnt=20, cts_seq=0) plus neutral placeholders.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3136RequestHeader(BlockRequestHeader):
    """o3136 request header. Inherits the standard LS request header schema."""
    pass


class O3136ResponseHeader(BlockResponseHeader):
    """o3136 response header. Inherits the standard LS response header schema."""
    pass


class O3136InBlock(BaseModel):
    """o3136InBlock — input block for the overseas futures/options intraday tick query."""

    gubun: Literal["0", "1"] = Field(
        ...,
        title="Query date type (조회구분)",
        description="Query date type. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
    )
    mktgb: Literal["F", "O"] = Field(
        ...,
        title="Market type (시장구분)",
        description="Market type. 'F' = futures (선물), 'O' = options (옵션).",
        examples=["F", "O"],
    )
    shcode: str = Field(
        ...,
        title="Short code (단축코드)",
        description="LS short instrument code for the contract (e.g., 'CUSU25', 'ESM26').",
        examples=["CUSU25", "ESM26"],
    )
    readcnt: int = Field(
        ...,
        le=100,
        title="Query count (조회갯수)",
        description="Number of tick records to return. Maximum 100.",
        examples=[20, 100],
    )
    cts_seq: int = Field(
        0,
        title="Continuation sequence (순번CTS)",
        description=(
            "Continuation sequence number for paging. "
            "Use 0 for the first request; use the returned cts_seq for subsequent requests."
        ),
        examples=[0, 5000],
    )


class O3136Request(BaseModel):
    """o3136 full request envelope (header + body + setup options)."""

    header: O3136RequestHeader = Field(
        O3136RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3136",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3136InBlock"], O3136InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3136InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3136"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3136OutBlock(BaseModel):
    """o3136OutBlock — continuation control block."""

    cts_seq: int = Field(
        default=0,
        title="Continuation sequence (순번CTS)",
        description=(
            "Continuation sequence number for paging. Pass this value as "
            "``cts_seq`` in the next request to retrieve the following page."
        ),
        examples=[0, 5000],
    )


class O3136OutBlock1(BaseModel):
    """o3136OutBlock1 — one intraday tick record.

    Decimal scale and currency unit are not declared in the source available
    to this codebase. Time ordering: consume as returned by LS.
    """

    ovsdate: str = Field(
        default="",
        title="Local date YYYYMMDD (현지일자)",
        description="Trade date in local exchange time (YYYYMMDD).",
        examples=["20250808", "20260315"],
    )
    ovstime: str = Field(
        default="",
        title="Local time HHMMSS (현지시간)",
        description="Trade time in local exchange time (HHMMSS).",
        examples=["143025", "093000"],
    )
    price: float = Field(
        default=0.0,
        title="Current price (현재가)",
        description=(
            "Price at the time of this tick. "
            "Decimal scale not declared in available source."
        ),
        examples=[4.235, 5800.25],
    )
    sign: str = Field(
        default="",
        title="Change-vs-previous sign (전일대비구분)",
        description=(
            "Sign indicator vs. previous session. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["2", "5"],
    )
    change: float = Field(
        default=0.0,
        title="Change vs. previous (전일대비)",
        description=(
            "Absolute change vs. previous session at this tick. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.025, -5.0],
    )
    diff: float = Field(
        default=0.0,
        title="Change rate (등락율)",
        description=(
            "Percent change vs. previous session at this tick. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.59, -0.09],
    )
    cvolume: int = Field(
        default=0,
        title="Execution quantity (체결수량)",
        description="Trade quantity for this tick (contracts).",
        examples=[1, 5],
    )
    volume: int = Field(
        default=0,
        title="Cumulative volume (누적거래량)",
        description="Cumulative volume up to and including this tick (contracts).",
        examples=[80000, 150000],
    )


class O3136Response(BaseModel):
    """o3136 full response envelope."""

    header: Optional[O3136ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3136OutBlock] = Field(
        None,
        title="Continuation block (기본 응답 블록)",
        description="Continuation control block.",
    )
    block1: List[O3136OutBlock1] = Field(
        ...,
        title="Tick list (상세 리스트)",
        description=(
            "List of intraday tick records. "
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
