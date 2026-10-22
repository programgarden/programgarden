"""Pydantic models for LS Securities OpenAPI o3128 (Overseas futures/options daily/weekly/monthly bar query).

o3128 returns OHLCV bars for one overseas futures or options contract over a
specified date range. The response uses a two-block structure: OutBlock holds
summary and continuation fields; OutBlock1 holds the bar list.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale: NOT declared in source; documented accordingly.
    - Time zone of session times: NOT declared in source; consume as returned by LS.
    - Time ordering of OutBlock1 list rows: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3128.py``
      (mktgb='F', shcode='ADM23', gubun='1', sdate='20230525', edate='20230609') plus
      neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3128RequestHeader(BlockRequestHeader):
    """o3128 request header. Inherits the standard LS request header schema."""
    pass


class O3128ResponseHeader(BlockResponseHeader):
    """o3128 response header. Inherits the standard LS response header schema."""
    pass


class O3128InBlock(BaseModel):
    """o3128InBlock — input block for the overseas futures/options daily/weekly/monthly bar query."""

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
    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="Period type (주기구분)",
        description="Bar period type. '0' = daily (일), '1' = weekly (주), '2' = monthly (월).",
        examples=["1", "0", "2"],
    )
    qrycnt: int = Field(
        ...,
        title="Request count (요청건수)",
        description="Number of bar records to return.",
        examples=[20, 100],
    )
    sdate: str = Field(
        ...,
        title="Start date YYYYMMDD (시작일자)",
        description="Query start date in YYYYMMDD format.",
        examples=["20230525", "20260101"],
    )
    edate: str = Field(
        ...,
        title="End date YYYYMMDD (종료일자)",
        description="Query end date in YYYYMMDD format.",
        examples=["20230609", "20260315"],
    )
    cts_date: str = Field(
        "",
        title="Continuation date YYYYMMDD (연속일자)",
        description=(
            "Continuation date for paging in YYYYMMDD format. "
            "Use empty string for the first request."
        ),
        examples=["", "20230601"],
    )


class O3128Request(BaseModel):
    """o3128 full request envelope (header + body + setup options)."""

    header: O3128RequestHeader = Field(
        O3128RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3128",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3128InBlock"], O3128InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3128InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3128"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3128OutBlock(BaseModel):
    """o3128OutBlock — summary and continuation control block.

    Decimal scale is not declared in the source available to this codebase.
    """

    shcode: str = Field(
        default="",
        title="Short code (단축코드)",
        description="Echoed short instrument code.",
        examples=["ADM23", "ESM26"],
    )
    jisiga: float = Field(
        default=0.0,
        title="Previous session open (전일시가)",
        description=(
            "Previous session's opening price. "
            "Decimal scale not declared in available source."
        ),
        examples=[5780.0, 4.20],
    )
    jihigh: float = Field(
        default=0.0,
        title="Previous session high (전일고가)",
        description="Previous session's highest traded price.",
        examples=[5800.0, 4.25],
    )
    jilow: float = Field(
        default=0.0,
        title="Previous session low (전일저가)",
        description="Previous session's lowest traded price.",
        examples=[5765.0, 4.18],
    )
    jiclose: float = Field(
        default=0.0,
        title="Previous session close (전일종가)",
        description="Previous session's closing price.",
        examples=[5795.25, 4.21],
    )
    jivolume: int = Field(
        default=0,
        title="Previous session volume (전일거래량)",
        description="Previous session's total trading volume (contracts).",
        examples=[150000, 80000],
    )
    disiga: float = Field(
        default=0.0,
        title="Current session open (당일시가)",
        description="Current session's opening price.",
        examples=[5790.0, 4.22],
    )
    dihigh: float = Field(
        default=0.0,
        title="Current session high (당일고가)",
        description="Current session's highest traded price.",
        examples=[5810.0, 4.25],
    )
    dilow: float = Field(
        default=0.0,
        title="Current session low (당일저가)",
        description="Current session's lowest traded price.",
        examples=[5775.0, 4.20],
    )
    diclose: float = Field(
        default=0.0,
        title="Current session close (당일종가)",
        description="Current session's closing price.",
        examples=[5800.25, 4.235],
    )
    mk_stime: str = Field(
        default="",
        title="Session start time HHMMSS (장시작시간)",
        description=(
            "Session start time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["170000", "090000"],
    )
    mk_etime: str = Field(
        default="",
        title="Session end time HHMMSS (장마감시간)",
        description=(
            "Session end time in HHMMSS format. "
            "Time zone not declared in available source; consume as returned by LS."
        ),
        examples=["160000", "153000"],
    )
    cts_date: str = Field(
        default="",
        title="Continuation date YYYYMMDD (연속일자)",
        description=(
            "Continuation date for the next page request (YYYYMMDD). "
            "Empty when no more data is available."
        ),
        examples=["", "20230601"],
    )
    rec_count: int = Field(
        default=0,
        title="Record count (레코드카운트)",
        description="Number of bar records returned in OutBlock1.",
        examples=[20, 5],
    )


class O3128OutBlock1(BaseModel):
    """o3128OutBlock1 — one daily/weekly/monthly bar record.

    Decimal scale is not declared in the source available to this codebase.
    Time ordering: consume as returned by LS.
    """

    date: str = Field(
        default="",
        title="Date YYYYMMDD (날짜)",
        description="Bar date in YYYYMMDD format.",
        examples=["20230601", "20260315"],
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
        examples=[150000, 80000],
    )


class O3128Response(BaseModel):
    """o3128 full response envelope."""

    header: Optional[O3128ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3128OutBlock] = Field(
        None,
        title="Summary block (기본 응답 블록)",
        description="Summary and continuation control block.",
    )
    block1: List[O3128OutBlock1] = Field(
        ...,
        title="Bar list (상세 리스트)",
        description=(
            "List of daily/weekly/monthly OHLCV bar records. "
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
