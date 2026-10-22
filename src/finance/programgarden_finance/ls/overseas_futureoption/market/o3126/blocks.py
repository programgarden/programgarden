"""Pydantic models for LS Securities OpenAPI o3126 (Overseas futures/options current price + 5-level orderbook).

o3126 returns a single-block snapshot combining the latest market data and a
5-level bid/ask orderbook for one overseas futures or options contract,
identified by market type and symbol.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale, currency unit: NOT declared in source; documented accordingly.
    - ``sign`` enum codes: consume as returned by LS.
    - Per-level quantity notes: no special constraint is declared for
      overseas-futures/options o3126 in the available source. Each level is
      documented as standard orderbook semantics.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_o3126.py``
      (mktgb='F', symbol='CUSU25') plus neutral placeholder values.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3126RequestHeader(BlockRequestHeader):
    """o3126 request header. Inherits the standard LS request header schema."""
    pass


class O3126ResponseHeader(BlockResponseHeader):
    """o3126 response header. Inherits the standard LS response header schema."""
    pass


class O3126InBlock(BaseModel):
    """o3126InBlock — input block for the overseas futures/options current price + orderbook query."""

    mktgb: Literal["F", "O"] = Field(
        ...,
        title="Market type (시장구분)",
        description="Market type. 'F' = futures (선물), 'O' = options (옵션).",
        examples=["F", "O"],
    )
    symbol: str = Field(
        ...,
        title="Symbol (종목심볼)",
        description="LS instrument symbol code for the contract (e.g., 'CUSU25', 'ESM26').",
        examples=["CUSU25", "ESM26"],
    )


class O3126Request(BaseModel):
    """o3126 full request envelope (header + body + setup options)."""

    header: O3126RequestHeader = Field(
        O3126RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="o3126",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["o3126InBlock"], O3126InBlock] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'o3126InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=2,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3126"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class O3126OutBlock(BaseModel):
    """o3126OutBlock — current price and 5-level bid/ask orderbook snapshot.

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
    hotime: str = Field(
        default="",
        title="Orderbook receive time (호가수신시간)",
        description=(
            "Time the orderbook snapshot was received by LS. "
            "Format and time zone not declared in available source; consume as returned by LS."
        ),
        examples=["143025"],
    )

    # --- Level 1 ---
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

    # --- Level 2 ---
    offerho2: float = Field(
        default=0.0,
        title="Ask price level 2 (매도호가2)",
        description="Ask price — level 2.",
        examples=[4.245, 5801.5],
    )
    bidho2: float = Field(
        default=0.0,
        title="Bid price level 2 (매수호가2)",
        description="Bid price — level 2.",
        examples=[4.23, 5799.75],
    )
    offercnt2: int = Field(
        default=0,
        title="Ask order count level 2 (매도호가건수2)",
        description="Number of ask orders at level 2.",
        examples=[4, 8],
    )
    bidcnt2: int = Field(
        default=0,
        title="Bid order count level 2 (매수호가건수2)",
        description="Number of bid orders at level 2.",
        examples=[2, 6],
    )
    offerrem2: int = Field(
        default=0,
        title="Ask quantity level 2 (매도호가수량2)",
        description="Total ask quantity at level 2 (contracts).",
        examples=[18, 45],
    )
    bidrem2: int = Field(
        default=0,
        title="Bid quantity level 2 (매수호가수량2)",
        description="Total bid quantity at level 2 (contracts).",
        examples=[12, 35],
    )

    # --- Level 3 ---
    offerho3: float = Field(
        default=0.0,
        title="Ask price level 3 (매도호가3)",
        description="Ask price — level 3.",
        examples=[4.25, 5802.0],
    )
    bidho3: float = Field(
        default=0.0,
        title="Bid price level 3 (매수호가3)",
        description="Bid price — level 3.",
        examples=[4.225, 5799.5],
    )
    offercnt3: int = Field(
        default=0,
        title="Ask order count level 3 (매도호가건수3)",
        description="Number of ask orders at level 3.",
        examples=[3, 6],
    )
    bidcnt3: int = Field(
        default=0,
        title="Bid order count level 3 (매수호가건수3)",
        description="Number of bid orders at level 3.",
        examples=[2, 5],
    )
    offerrem3: int = Field(
        default=0,
        title="Ask quantity level 3 (매도호가수량3)",
        description="Total ask quantity at level 3 (contracts).",
        examples=[15, 30],
    )
    bidrem3: int = Field(
        default=0,
        title="Bid quantity level 3 (매수호가수량3)",
        description="Total bid quantity at level 3 (contracts).",
        examples=[10, 25],
    )

    # --- Level 4 ---
    offerho4: float = Field(
        default=0.0,
        title="Ask price level 4 (매도호가4)",
        description="Ask price — level 4.",
        examples=[4.255, 5802.5],
    )
    bidho4: float = Field(
        default=0.0,
        title="Bid price level 4 (매수호가4)",
        description="Bid price — level 4.",
        examples=[4.22, 5799.25],
    )
    offercnt4: int = Field(
        default=0,
        title="Ask order count level 4 (매도호가건수4)",
        description="Number of ask orders at level 4.",
        examples=[2, 5],
    )
    bidcnt4: int = Field(
        default=0,
        title="Bid order count level 4 (매수호가건수4)",
        description="Number of bid orders at level 4.",
        examples=[1, 4],
    )
    offerrem4: int = Field(
        default=0,
        title="Ask quantity level 4 (매도호가수량4)",
        description="Total ask quantity at level 4 (contracts).",
        examples=[10, 20],
    )
    bidrem4: int = Field(
        default=0,
        title="Bid quantity level 4 (매수호가수량4)",
        description="Total bid quantity at level 4 (contracts).",
        examples=[8, 18],
    )

    # --- Level 5 ---
    offerho5: float = Field(
        default=0.0,
        title="Ask price level 5 (매도호가5)",
        description="Ask price — level 5.",
        examples=[4.26, 5803.0],
    )
    bidho5: float = Field(
        default=0.0,
        title="Bid price level 5 (매수호가5)",
        description="Bid price — level 5.",
        examples=[4.215, 5799.0],
    )
    offercnt5: int = Field(
        default=0,
        title="Ask order count level 5 (매도호가건수5)",
        description="Number of ask orders at level 5.",
        examples=[2, 4],
    )
    bidcnt5: int = Field(
        default=0,
        title="Bid order count level 5 (매수호가건수5)",
        description="Number of bid orders at level 5.",
        examples=[1, 3],
    )
    offerrem5: int = Field(
        default=0,
        title="Ask quantity level 5 (매도호가수량5)",
        description="Total ask quantity at level 5 (contracts).",
        examples=[8, 15],
    )
    bidrem5: int = Field(
        default=0,
        title="Bid quantity level 5 (매수호가수량5)",
        description="Total bid quantity at level 5 (contracts).",
        examples=[6, 12],
    )

    # --- Totals ---
    offercnt: int = Field(
        default=0,
        title="Total ask order count (매도호가건수합)",
        description="Sum of ask order counts across all levels.",
        examples=[16, 33],
    )
    bidcnt: int = Field(
        default=0,
        title="Total bid order count (매수호가건수합)",
        description="Sum of bid order counts across all levels.",
        examples=[9, 26],
    )
    offer: int = Field(
        default=0,
        title="Total ask quantity (매도호가수량합)",
        description="Sum of ask quantities across all levels (contracts).",
        examples=[71, 160],
    )
    bid: int = Field(
        default=0,
        title="Total bid quantity (매수호가수량합)",
        description="Sum of bid quantities across all levels (contracts).",
        examples=[51, 130],
    )


class O3126Response(BaseModel):
    """o3126 full response envelope."""

    header: Optional[O3126ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[O3126OutBlock] = Field(
        None,
        title="Snapshot block (출력 블록)",
        description="Current price and 5-level orderbook snapshot.",
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
