"""Pydantic models for LS Securities OpenAPI o3116 (Overseas futures intraday tick query — futures only).

o3116 returns an intraday tick-by-tick list for one overseas futures contract.
The response uses a two-block structure: OutBlock holds the continuation
sequence number; OutBlock1 holds the tick records.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit: NOT declared in source; documented accordingly.
    - ``sign`` enum codes: consume as returned by LS.
    - Time ordering of OutBlock1 list rows: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3116.py``
      (gubun='0', shcode='CUSU25', readcnt=100, cts_seq=12426) plus neutral placeholders.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3116RequestHeader(BlockRequestHeader):
    """o3116 request header. Inherits the standard LS request header schema."""
    pass


class O3116ResponseHeader(BlockResponseHeader):
    """o3116 response header. Inherits the standard LS response header schema."""
    pass


class O3116InBlock(BaseModel):
    """o3116InBlock — input block for the overseas futures intraday tick query."""

    gubun: str = Field(
        ...,
        title="Query date type (조회구분)",
        description="Query date type. '0' = today only (당일만 사용가능).",
        examples=["0"],
    )
    shcode: str = Field(
        ...,
        title="Short code (단축코드)",
        description="LS short instrument code for the contract (e.g., 'CUSU25').",
        examples=["CUSU25", "ESM26"],
    )
    readcnt: int = Field(
        ...,
        le=100,
        title="Query count (조회갯수)",
        description="Number of tick records to return. Maximum 100.",
        examples=[100, 20],
    )
    cts_seq: int = Field(
        0,
        title="Continuation sequence (순번CTS)",
        description=(
            "Continuation sequence number for paging. "
            "Use 0 for the first request; use the returned cts_seq value for subsequent requests."
        ),
        examples=[0, 12426],
    )


class O3116Request(BaseModel):
    """o3116 full request envelope (header + body + setup options)."""

    header: O3116RequestHeader = Field(
        O3116RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3116",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3116InBlock"], O3116InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3116InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3116"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3116OutBlock(BaseModel):
    """o3116OutBlock — continuation control block."""

    cts_seq: int = Field(
        default=0,
        title="Continuation sequence (순번CTS)",
        description=(
            "Continuation sequence number for paging. Pass this value as "
            "``cts_seq`` in the next request to retrieve the following page."
        ),
        examples=[0, 12426],
    )


class O3116OutBlock1(BaseModel):
    """o3116OutBlock1 — one intraday tick record.

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


class O3116Response(BaseModel):
    """o3116 full response envelope."""

    header: Optional[O3116ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3116OutBlock] = Field(
        None,
        title="Continuation block (기본 응답 블록)",
        description="Continuation control block.",
    )
    block1: List[O3116OutBlock1] = Field(
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
