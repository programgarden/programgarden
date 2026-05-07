"""Pydantic models for LS Securities OpenAPI GSH (Overseas Stock Real-time Orderbook).

GSH is a Real-time WebSocket TR that pushes 10-level bid/ask orderbook
updates for overseas-stock symbols (US markets — NYSE / NASDAQ / AMEX).
The ``GSHRealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — exchange-prefixed symbol such as ``"81SOXL"``
padded to 18 characters); the ``GSHRealResponseBody`` carries the per-update
orderbook push payload.

⚠️ LS API constraint observed in this codebase (overseas-stock only):
    - Per-level prices (``offerho1``..``offerho10`` / ``bidho1``..``bidho10``)
      are populated normally.
    - Level-1 remaining quantities (``offerrem1`` / ``bidrem1``) actually
      carry the *aggregate* total quantity (same as ``totofferrem`` /
      ``totbidrem``) — LS does not split level-1 separately.
    - Per-level remaining quantities for levels 2..10 (``offerrem2`` …
      ``offerrem10`` / ``bidrem2`` … ``bidrem10``) are always 0.
    - Per-level order-counts (``offerno1``..``offerno10`` /
      ``bidno1``..``bidno10``) and aggregate count totals (``totoffercnt``
      / ``totbidcnt``) are always 0.
    - Aggregate quantity totals (``totofferrem`` / ``totbidrem``) are the
      only reliably populated quantity values.
    - This constraint applies to overseas-stock only — overseas-futures
      (OVH / WOH) and Korea-stock (H1_ / HA_) populate per-level fields
      normally.
    - Use REST API ``g3106`` if per-level remaining quantities are needed.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - The "always 0" notes mirror existing in-codebase observations and
      are preserved verbatim — they are observed behaviour, not inferred.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.
    - ``examples`` for ``tr_key`` come from
      ``src/finance/example/overseas_stock/real_GSH.py`` ("81SOXL"); response
      examples mirror typical LS WS orderbook-push payload shapes (with
      level-2..10 quantities / counts forced to 0 per the API constraint).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class GSHRealRequestHeader(BlockRealRequestHeader):
    """GSH real-time request header. Inherits the standard LS WS request header schema."""
    pass


class GSHRealResponseHeader(BlockRealResponseHeader):
    """GSH real-time response header. Inherits the standard LS WS response header schema."""
    pass


class GSHRealRequestBody(BaseModel):
    """GSHRealRequestBody — WebSocket subscription envelope for orderbook push.

    ``tr_key`` is the LS-internal 18-character key combining exchange code
    and ticker; if shorter, it is right-padded with spaces by the validator
    below.
    """

    tr_cd: str = Field(
        default="GSH",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'GSH'.",
        examples=["GSH"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=18,
        title="단축코드 + padding (Exchange-prefixed key, 18-char space-padded)",
        description=(
            "Exchange-prefixed key combining exchange code (2 chars: '81' = "
            "NYSE / AMEX, '82' = NASDAQ) and short symbol code, then "
            "right-padded with spaces to 18 characters."
        ),
        examples=["81SOXL             ", "82TSLA             "],
    )

    @field_validator("tr_key", mode="before")
    def ensure_trailing_12_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 18:
            return s.ljust(18)
        return s

    model_config = ConfigDict(validate_assignment=True)


class GSHRealRequest(BaseModel):
    """
    해외주식 호가 실시간 요청 (Overseas Stock Real-time Orderbook — request envelope).
    """
    header: GSHRealRequestHeader = Field(
        GSHRealRequestHeader(
            token="",
            tr_type="3"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="GSH WebSocket subscription header block (token + tr_type)."
    )
    body: GSHRealRequestBody = Field(
        GSHRealRequestBody(
            tr_cd="GSH",
            tr_key=""
        ),
        title="입력 데이터 블록 (Input body block)",
        description="해외주식 호가 input body — TR code and 18-char exchange-prefixed key.",
    )


class GSHRealResponseBody(BaseModel):
    """GSHRealResponseBody — 10-level orderbook push payload for a US overseas stock.

    See module-level docstring for the LS API constraint that forces
    per-level quantities (levels 2..10) and all per-level / total order-counts
    to 0 for overseas stock.
    """

    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'SOXL', 'AAPL').",
        examples=["SOXL", "AAPL"],
    )
    loctime: str = Field(
        ...,
        title="현지호가시간 (Orderbook time — local exchange)",
        description="Orderbook update time at the local exchange in HHMMSS format.",
        examples=["093015"],
    )
    kortime: str = Field(
        ...,
        title="한국호가시간 (Orderbook time — Korea local time)",
        description="Orderbook update time in Korea local time, HHMMSS.",
        examples=["223015"],
    )

    # Level 1
    offerho1: float = Field(
        ...,
        title="매도호가1 (Ask price — level 1)",
        description=(
            "Ask price at level 1. Decimal scale not declared in available "
            "source — consume as returned by LS."
        ),
        examples=[12.24],
    )
    bidho1: float = Field(
        ...,
        title="매수호가1 (Bid price — level 1)",
        description="Bid price at level 1.",
        examples=[12.20],
    )
    offerrem1: int = Field(
        ...,
        title="매도호가잔량1 (Ask remaining quantity — level 1, aggregate)",
        description=(
            "Ask remaining quantity at level 1. ⚠️ For overseas stock LS "
            "does NOT split level 1 — this carries the aggregate total ask "
            "quantity (same as ``totofferrem``)."
        ),
        examples=[1000],
    )
    bidrem1: int = Field(
        ...,
        title="매수호가잔량1 (Bid remaining quantity — level 1, aggregate)",
        description=(
            "Bid remaining quantity at level 1. ⚠️ For overseas stock LS "
            "does NOT split level 1 — this carries the aggregate total bid "
            "quantity (same as ``totbidrem``)."
        ),
        examples=[1500],
    )
    offerno1: int = Field(
        ...,
        title="매도호가건수1 (Ask order-count — level 1)",
        description="Ask order count at level 1. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno1: int = Field(
        ...,
        title="매수호가건수1 (Bid order-count — level 1)",
        description="Bid order count at level 1. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 2
    offerho2: float = Field(
        ...,
        title="매도호가2 (Ask price — level 2)",
        description="Ask price at level 2.",
        examples=[12.25],
    )
    bidho2: float = Field(
        ...,
        title="매수호가2 (Bid price — level 2)",
        description="Bid price at level 2.",
        examples=[12.19],
    )
    offerrem2: int = Field(
        ...,
        title="매도호가잔량2 (Ask remaining quantity — level 2)",
        description="Ask remaining quantity at level 2. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem2: int = Field(
        ...,
        title="매수호가잔량2 (Bid remaining quantity — level 2)",
        description="Bid remaining quantity at level 2. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno2: int = Field(
        ...,
        title="매도호가건수2 (Ask order-count — level 2)",
        description="Ask order count at level 2. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno2: int = Field(
        ...,
        title="매수호가건수2 (Bid order-count — level 2)",
        description="Bid order count at level 2. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 3
    offerho3: float = Field(
        ...,
        title="매도호가3 (Ask price — level 3)",
        description="Ask price at level 3.",
        examples=[12.26],
    )
    bidho3: float = Field(
        ...,
        title="매수호가3 (Bid price — level 3)",
        description="Bid price at level 3.",
        examples=[12.18],
    )
    offerrem3: int = Field(
        ...,
        title="매도호가잔량3 (Ask remaining quantity — level 3)",
        description="Ask remaining quantity at level 3. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem3: int = Field(
        ...,
        title="매수호가잔량3 (Bid remaining quantity — level 3)",
        description="Bid remaining quantity at level 3. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno3: int = Field(
        ...,
        title="매도호가건수3 (Ask order-count — level 3)",
        description="Ask order count at level 3. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno3: int = Field(
        ...,
        title="매수호가건수3 (Bid order-count — level 3)",
        description="Bid order count at level 3. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 4
    offerho4: float = Field(
        ...,
        title="매도호가4 (Ask price — level 4)",
        description="Ask price at level 4.",
        examples=[12.27],
    )
    bidho4: float = Field(
        ...,
        title="매수호가4 (Bid price — level 4)",
        description="Bid price at level 4.",
        examples=[12.17],
    )
    offerrem4: int = Field(
        ...,
        title="매도호가잔량4 (Ask remaining quantity — level 4)",
        description="Ask remaining quantity at level 4. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem4: int = Field(
        ...,
        title="매수호가잔량4 (Bid remaining quantity — level 4)",
        description="Bid remaining quantity at level 4. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno4: int = Field(
        ...,
        title="매도호가건수4 (Ask order-count — level 4)",
        description="Ask order count at level 4. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno4: int = Field(
        ...,
        title="매수호가건수4 (Bid order-count — level 4)",
        description="Bid order count at level 4. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 5
    offerho5: float = Field(
        ...,
        title="매도호가5 (Ask price — level 5)",
        description="Ask price at level 5.",
        examples=[12.28],
    )
    bidho5: float = Field(
        ...,
        title="매수호가5 (Bid price — level 5)",
        description="Bid price at level 5.",
        examples=[12.16],
    )
    offerrem5: int = Field(
        ...,
        title="매도호가잔량5 (Ask remaining quantity — level 5)",
        description="Ask remaining quantity at level 5. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem5: int = Field(
        ...,
        title="매수호가잔량5 (Bid remaining quantity — level 5)",
        description="Bid remaining quantity at level 5. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno5: int = Field(
        ...,
        title="매도호가건수5 (Ask order-count — level 5)",
        description="Ask order count at level 5. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno5: int = Field(
        ...,
        title="매수호가건수5 (Bid order-count — level 5)",
        description="Bid order count at level 5. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 6
    offerho6: float = Field(
        ...,
        title="매도호가6 (Ask price — level 6)",
        description="Ask price at level 6.",
        examples=[12.29],
    )
    bidho6: float = Field(
        ...,
        title="매수호가6 (Bid price — level 6)",
        description="Bid price at level 6.",
        examples=[12.15],
    )
    offerrem6: int = Field(
        ...,
        title="매도호가잔량6 (Ask remaining quantity — level 6)",
        description="Ask remaining quantity at level 6. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem6: int = Field(
        ...,
        title="매수호가잔량6 (Bid remaining quantity — level 6)",
        description="Bid remaining quantity at level 6. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno6: int = Field(
        ...,
        title="매도호가건수6 (Ask order-count — level 6)",
        description="Ask order count at level 6. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno6: int = Field(
        ...,
        title="매수호가건수6 (Bid order-count — level 6)",
        description="Bid order count at level 6. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 7
    offerho7: float = Field(
        ...,
        title="매도호가7 (Ask price — level 7)",
        description="Ask price at level 7.",
        examples=[12.30],
    )
    bidho7: float = Field(
        ...,
        title="매수호가7 (Bid price — level 7)",
        description="Bid price at level 7.",
        examples=[12.14],
    )
    offerrem7: int = Field(
        ...,
        title="매도호가잔량7 (Ask remaining quantity — level 7)",
        description="Ask remaining quantity at level 7. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem7: int = Field(
        ...,
        title="매수호가잔량7 (Bid remaining quantity — level 7)",
        description="Bid remaining quantity at level 7. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno7: int = Field(
        ...,
        title="매도호가건수7 (Ask order-count — level 7)",
        description="Ask order count at level 7. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno7: int = Field(
        ...,
        title="매수호가건수7 (Bid order-count — level 7)",
        description="Bid order count at level 7. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 8
    offerho8: float = Field(
        ...,
        title="매도호가8 (Ask price — level 8)",
        description="Ask price at level 8.",
        examples=[12.31],
    )
    bidho8: float = Field(
        ...,
        title="매수호가8 (Bid price — level 8)",
        description="Bid price at level 8.",
        examples=[12.13],
    )
    offerrem8: int = Field(
        ...,
        title="매도호가잔량8 (Ask remaining quantity — level 8)",
        description="Ask remaining quantity at level 8. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem8: int = Field(
        ...,
        title="매수호가잔량8 (Bid remaining quantity — level 8)",
        description="Bid remaining quantity at level 8. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno8: int = Field(
        ...,
        title="매도호가건수8 (Ask order-count — level 8)",
        description="Ask order count at level 8. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno8: int = Field(
        ...,
        title="매수호가건수8 (Bid order-count — level 8)",
        description="Bid order count at level 8. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 9
    offerho9: float = Field(
        ...,
        title="매도호가9 (Ask price — level 9)",
        description="Ask price at level 9.",
        examples=[12.32],
    )
    bidho9: float = Field(
        ...,
        title="매수호가9 (Bid price — level 9)",
        description="Bid price at level 9.",
        examples=[12.12],
    )
    offerrem9: int = Field(
        ...,
        title="매도호가잔량9 (Ask remaining quantity — level 9)",
        description="Ask remaining quantity at level 9. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem9: int = Field(
        ...,
        title="매수호가잔량9 (Bid remaining quantity — level 9)",
        description="Bid remaining quantity at level 9. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno9: int = Field(
        ...,
        title="매도호가건수9 (Ask order-count — level 9)",
        description="Ask order count at level 9. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno9: int = Field(
        ...,
        title="매수호가건수9 (Bid order-count — level 9)",
        description="Bid order count at level 9. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Level 10
    offerho10: float = Field(
        ...,
        title="매도호가10 (Ask price — level 10)",
        description="Ask price at level 10.",
        examples=[12.33],
    )
    bidho10: float = Field(
        ...,
        title="매수호가10 (Bid price — level 10)",
        description="Bid price at level 10.",
        examples=[12.11],
    )
    offerrem10: int = Field(
        ...,
        title="매도호가잔량10 (Ask remaining quantity — level 10)",
        description="Ask remaining quantity at level 10. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidrem10: int = Field(
        ...,
        title="매수호가잔량10 (Bid remaining quantity — level 10)",
        description="Bid remaining quantity at level 10. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    offerno10: int = Field(
        ...,
        title="매도호가건수10 (Ask order-count — level 10)",
        description="Ask order count at level 10. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    bidno10: int = Field(
        ...,
        title="매수호가건수10 (Bid order-count — level 10)",
        description="Bid order count at level 10. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )

    # Aggregate totals
    totoffercnt: int = Field(
        ...,
        title="매도호가총건수 (Total ask order-count)",
        description="Total ask order count. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    totbidcnt: int = Field(
        ...,
        title="매수호가총건수 (Total bid order-count)",
        description="Total bid order count. ⚠️ LS API does not expose this for overseas stock — always 0.",
        examples=[0],
    )
    totofferrem: int = Field(
        ...,
        title="매도호가총수량 (Total ask remaining quantity)",
        description=(
            "Total ask remaining quantity. The only reliably populated ask "
            "quantity for overseas stock — same value also appears in "
            "``offerrem1``."
        ),
        examples=[1000],
    )
    totbidrem: int = Field(
        ...,
        title="매수호가총수량 (Total bid remaining quantity)",
        description=(
            "Total bid remaining quantity. The only reliably populated bid "
            "quantity for overseas stock — same value also appears in "
            "``bidrem1``."
        ),
        examples=[1500],
    )


class GSHRealResponse(BaseModel):
    header: Optional[GSHRealResponseHeader]
    body: Optional[GSHRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
