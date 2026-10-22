"""Pydantic models for LS Securities OpenAPI o3104 (Overseas futures daily tick query).

o3104 returns a list of daily (or weekly/monthly) trade records for one
overseas futures contract — price, OHLC, volume, and change-vs-previous
per bar.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit, and ``sign``/``cgubun`` enum codes are
      NOT enumerated in the source available to this codebase.
    - Time ordering of OutBlock1 list rows is not declared in the source;
      consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3104.py``
      (gubun='1', shcode='CUSU25', date='20250808') plus neutral placeholders.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3104RequestHeader(BlockRequestHeader):
    """o3104 request header. Inherits the standard LS request header schema."""
    pass


class O3104ResponseHeader(BlockResponseHeader):
    """o3104 response header. Inherits the standard LS response header schema."""
    pass


class O3104InBlock(BaseModel):
    """o3104InBlock — input block for the overseas futures daily tick query."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="Query period type (조회구분)",
        description=(
            "Period type for the query. '0' = daily (일별), "
            "'1' = weekly (주별), '2' = monthly (월별)."
        ),
        examples=["1", "0", "2"],
    )
    shcode: str = Field(
        ...,
        title="Short code (단축코드)",
        description=(
            "LS 8-character short instrument code for the contract "
            "(e.g., 'CUSU25')."
        ),
        examples=["CUSU25", "ESM26"],
    )
    date: str = Field(
        ...,
        title="Query date YYYYMMDD (조회일자)",
        description="Reference date for the query in YYYYMMDD format.",
        examples=["20250808", "20260315"],
    )


class O3104Request(BaseModel):
    """o3104 full request envelope (header + body + setup options)."""

    header: O3104RequestHeader = Field(
        O3104RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3104",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3104InBlock"], O3104InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3104InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3104"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3104OutBlock1(BaseModel):
    """o3104OutBlock1 — one daily/weekly/monthly bar record.

    Decimal scale is not declared in the source available to this codebase.
    Time ordering of rows: consume as returned by LS.
    """

    chedate: str = Field(
        ...,
        title="Date YYYYMMDD (일자)",
        description="Bar date in YYYYMMDD format.",
        examples=["20250808", "20260315"],
    )
    price: float = Field(
        ...,
        title="Current price (현재가)",
        description=(
            "Closing / current price for the bar. "
            "Decimal scale not declared in available source."
        ),
        examples=[5780.25, 21300.0],
    )
    sign: str = Field(
        ...,
        title="Change-vs-previous sign (대비구분)",
        description=(
            "Sign indicator vs. previous bar. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["2", "5"],
    )
    change: float = Field(
        ...,
        title="Change vs. previous (대비)",
        description=(
            "Absolute change vs. previous bar. "
            "Decimal scale not declared in available source."
        ),
        examples=[10.25, -5.0],
    )
    diff: float = Field(
        ...,
        title="Change rate (등락율)",
        description=(
            "Percent change vs. previous bar. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.18, -0.02],
    )
    open: float = Field(
        ...,
        title="Open price (시가)",
        description=(
            "Opening price of the bar. "
            "Decimal scale not declared in available source."
        ),
        examples=[5770.0, 21280.0],
    )
    high: float = Field(
        ...,
        title="High price (고가)",
        description="Highest traded price of the bar.",
        examples=[5790.5, 21320.0],
    )
    low: float = Field(
        ...,
        title="Low price (저가)",
        description="Lowest traded price of the bar.",
        examples=[5760.0, 21260.0],
    )
    cgubun: str = Field(
        ...,
        title="Trade-side classification (체결구분)",
        description=(
            "Trade-side classification code. "
            "Specific values not declared in available source; consume as returned by LS."
        ),
        examples=["1", "2"],
    )
    volume: int = Field(
        ...,
        title="Cumulative volume (누적거래량)",
        description="Cumulative trading volume for the bar (contracts).",
        examples=[150000, 320000],
    )


class O3104Response(BaseModel):
    """o3104 full response envelope."""

    header: Optional[O3104ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: List[O3104OutBlock1] = Field(
        ...,
        title="Bar list (출력 블록 리스트)",
        description=(
            "List of daily/weekly/monthly bar records. "
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
        title="LS response code (응답 코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답 메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류 메시지)",
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
