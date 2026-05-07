"""Pydantic models for LS Securities OpenAPI o3107 (Overseas futures watchlist quote query).

o3107 returns a list of current price and 1-level orderbook snapshots for
one or more overseas futures contracts — the "watchlist" (관심종목) style
query.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit: NOT declared in source; documented accordingly.
    - ``sign`` enum codes: consume as returned by LS.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3107.py``
      (symbol='CUSU25') plus neutral placeholder values.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3107RequestHeader(BlockRequestHeader):
    """o3107 request header. Inherits the standard LS request header schema."""
    pass


class O3107ResponseHeader(BlockResponseHeader):
    """o3107 response header. Inherits the standard LS response header schema."""
    pass


class O3107InBlock(BaseModel):
    """o3107InBlock — input block for the overseas futures watchlist quote query."""

    symbol: str = Field(
        ...,
        title="Symbol (종목심볼)",
        description="LS instrument symbol code for the contract (e.g., 'CUSU25', 'ESM26').",
        examples=["CUSU25", "ESM26"],
    )


class O3107Request(BaseModel):
    """o3107 full request envelope (header + body + setup options)."""

    header: O3107RequestHeader = Field(
        O3107RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3107",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3107InBlock"], O3107InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3107InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3107"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3107OutBlock(BaseModel):
    """o3107OutBlock — one watchlist quote entry with current price and 1-level orderbook.

    Decimal scale and currency unit are not declared in the source available
    to this codebase.
    """

    symbol: str = Field(
        default="",
        title="Symbol code (종목코드)",
        description="LS instrument symbol code for the contract.",
        examples=["CUSU25", "ESM26"],
    )
    symbolname: str = Field(
        default="",
        title="Symbol name (종목명)",
        description="Human-readable instrument name.",
        examples=["COPPER SEP25"],
    )
    price: float = Field(
        default=0.0,
        title="Current price (현재가)",
        description=(
            "Latest traded price. Decimal scale not declared in available source."
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
            "Absolute change vs. previous session. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.025, -5.0],
    )
    diff: float = Field(
        default=0.0,
        title="Change rate (등락율)",
        description=(
            "Percent change vs. previous session. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.59, -0.09],
    )
    volume: int = Field(
        default=0,
        title="Cumulative volume (누적거래량)",
        description="Cumulative trading volume for the session (contracts).",
        examples=[80000, 150000],
    )
    jnilclose: float = Field(
        default=0.0,
        title="Previous close price (전일종가)",
        description=(
            "Previous session's closing price. "
            "Decimal scale not declared in available source."
        ),
        examples=[4.21, 5795.25],
    )
    open: float = Field(
        default=0.0,
        title="Open price (시가)",
        description="Opening price of the session.",
        examples=[4.22, 5790.0],
    )
    high: float = Field(
        default=0.0,
        title="High price (고가)",
        description="Highest traded price of the session.",
        examples=[4.25, 5810.0],
    )
    low: float = Field(
        default=0.0,
        title="Low price (저가)",
        description="Lowest traded price of the session.",
        examples=[4.21, 5775.0],
    )
    offerho1: float = Field(
        default=0.0,
        title="Ask price level 1 (매도호가1)",
        description="Best ask (sell) price — level 1.",
        examples=[4.24, 5801.0],
    )
    bidho1: float = Field(
        default=0.0,
        title="Bid price level 1 (매수호가1)",
        description="Best bid (buy) price — level 1.",
        examples=[4.235, 5800.25],
    )
    offercnt1: int = Field(
        default=0,
        title="Ask order count level 1 (매도호가건수1)",
        description="Number of ask orders at level 1.",
        examples=[5, 10],
    )
    bidcnt1: int = Field(
        default=0,
        title="Bid order count level 1 (매수호가건수1)",
        description="Number of bid orders at level 1.",
        examples=[3, 8],
    )
    offerrem1: int = Field(
        default=0,
        title="Ask quantity level 1 (매도호가수량1)",
        description="Total ask quantity at level 1 (contracts).",
        examples=[20, 50],
    )
    bidrem1: int = Field(
        default=0,
        title="Bid quantity level 1 (매수호가수량1)",
        description="Total bid quantity at level 1 (contracts).",
        examples=[15, 40],
    )
    offercnt: int = Field(
        default=0,
        title="Total ask order count (매도호가건수합)",
        description="Sum of ask order counts across all levels.",
        examples=[5, 10],
    )
    bidcnt: int = Field(
        default=0,
        title="Total bid order count (매수호가건수합)",
        description="Sum of bid order counts across all levels.",
        examples=[3, 8],
    )
    offer: int = Field(
        default=0,
        title="Total ask quantity (매도호가수량합)",
        description="Sum of ask quantities across all levels (contracts).",
        examples=[20, 50],
    )
    bid: int = Field(
        default=0,
        title="Total bid quantity (매수호가수량합)",
        description="Sum of bid quantities across all levels (contracts).",
        examples=[15, 40],
    )


class O3107Response(BaseModel):
    """o3107 full response envelope."""

    header: Optional[O3107ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: List[O3107OutBlock] = Field(
        ...,
        title="Watchlist quote list (출력 블록 리스트)",
        description=(
            "List of current price and orderbook snapshots per queried contract. "
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
