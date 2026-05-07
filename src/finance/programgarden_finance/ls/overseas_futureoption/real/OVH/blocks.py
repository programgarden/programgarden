"""Pydantic models for LS Securities OpenAPI OVH (Overseas Futures Real-time Orderbook).

OVH is a Real-time WebSocket TR that pushes the 5-level bid / ask
orderbook for an overseas-futures contract. The ``OVHRealRequestBody``
carries the WebSocket subscription envelope (``tr_cd`` + ``tr_key`` —
short symbol such as ``"ESZ25"`` padded to 8 characters); the
``OVHRealResponseBody`` carries the per-update push payload (5 ask + 5
bid levels with prices, remaining quantities, and order counts; plus
totals).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Decimal scale, currency unit, contract multiplier, and tick value are
      NOT declared in the source available to this codebase — examples are
      illustrative shapes (LS WS sample payload style) and must not be
      treated as authoritative scale references.
    - All numeric fields are typed ``str`` in the source — preserved
      verbatim. Stringified-numeric semantics (leading zeros, sign, scale)
      are not declared and must be consumed as returned by LS.
    - The 5 orderbook levels are documented as standard 1..5 best-bid /
      best-ask depth. No source-level constraint marker (e.g. "levels 2..5
      always 0" as seen on some equity TRs) is declared for OVH.
    - ``examples`` for ``tr_key`` come from
      ``src/finance/example/overseas_futureoption/real_OVH.py`` ("ESZ25"
      padded to 8 characters); response examples mirror typical LS WS
      futures-orderbook payload shapes.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class OVHRealRequestHeader(BlockRealRequestHeader):
    """OVH real-time request header. Inherits the standard LS WS request header schema."""
    pass


class OVHRealResponseHeader(BlockRealResponseHeader):
    """OVH real-time response header. Inherits the standard LS WS response header schema."""
    pass


class OVHRealRequestBody(BaseModel):
    """OVHRealRequestBody — WebSocket subscription envelope for futures orderbook push.

    ``tr_key`` is the short overseas-futures contract symbol (e.g. ``"ESZ25"``);
    the ``ensure_trailing_8_spaces`` validator right-pads to 8 characters
    for the LS WSS framing requirement.
    """

    tr_cd: str = Field(
        default="OVH",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'OVH'.",
        examples=["OVH"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short futures symbol, 8-char space-padded)",
        description=(
            "Short overseas-futures contract symbol used as the WS "
            "subscription key (typically root + expiry, e.g. 'ESZ25', "
            "'NQU26'). Right-padded with spaces to 8 characters by the "
            "validator."
        ),
        examples=["ESZ25   ", "NQU26   "],
    )

    @field_validator("tr_key", mode="before")
    def ensure_trailing_8_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)[:8]
        return s.ljust(8)

    model_config = ConfigDict(validate_assignment=True)


class OVHRealRequest(BaseModel):
    """
    해외선물 호가 실시간 요청 (Overseas Futures Real-time Orderbook — request envelope).
    """
    header: OVHRealRequestHeader = Field(
        OVHRealRequestHeader(
            token="",
            tr_type="1",
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="OVH WebSocket subscription header block (token + tr_type)."
    )
    body: OVHRealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description="해외선물 호가 input body — TR code and 8-char space-padded futures symbol.",
    )


class OVHRealResponseBody(BaseModel):
    """OVHRealResponseBody — per-update orderbook push payload for an overseas-futures contract.

    Contains symbol identification, an LS-side timestamp, and 5 ask / 5
    bid levels (price + remaining quantity + order count per level), plus
    totals across all levels.
    """

    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / contract code)",
        description=(
            "Overseas-futures contract code (root + expiry, e.g. 'ESZ25')."
        ),
        examples=["ESZ25", "NQU26"],
    )
    hotime: str = Field(
        ...,
        title="호가시간 (Orderbook timestamp)",
        description=(
            "Orderbook update timestamp. Format / time zone not declared in "
            "available source; consume as returned by LS."
        ),
        examples=["093015"],
    )

    offerho1: str = Field(
        ...,
        title="매도호가 1 (Ask price level 1)",
        description="Best ask price (level 1). Returned as a string.",
        examples=["5025.50"],
    )
    bidho1: str = Field(
        ...,
        title="매수호가 1 (Bid price level 1)",
        description="Best bid price (level 1). Returned as a string.",
        examples=["5025.25"],
    )
    offerrem1: str = Field(
        ...,
        title="매도호가 잔량 1 (Ask remaining quantity level 1)",
        description="Remaining ask quantity at level 1 (contracts), as a string.",
        examples=["20"],
    )
    bidrem1: str = Field(
        ...,
        title="매수호가 잔량 1 (Bid remaining quantity level 1)",
        description="Remaining bid quantity at level 1 (contracts), as a string.",
        examples=["18"],
    )
    offerno1: str = Field(
        ...,
        title="매도호가 건수 1 (Ask order count level 1)",
        description="Number of ask orders at level 1, as a string.",
        examples=["5"],
    )
    bidno1: str = Field(
        ...,
        title="매수호가 건수 1 (Bid order count level 1)",
        description="Number of bid orders at level 1, as a string.",
        examples=["4"],
    )

    offerho2: str = Field(
        ...,
        title="매도호가 2 (Ask price level 2)",
        description="Ask price level 2. Returned as a string.",
        examples=["5025.75"],
    )
    bidho2: str = Field(
        ...,
        title="매수호가 2 (Bid price level 2)",
        description="Bid price level 2. Returned as a string.",
        examples=["5025.00"],
    )
    offerrem2: str = Field(
        ...,
        title="매도호가 잔량 2 (Ask remaining quantity level 2)",
        description="Remaining ask quantity at level 2 (contracts), as a string.",
        examples=["15"],
    )
    bidrem2: str = Field(
        ...,
        title="매수호가 잔량 2 (Bid remaining quantity level 2)",
        description="Remaining bid quantity at level 2 (contracts), as a string.",
        examples=["12"],
    )
    offerno2: str = Field(
        ...,
        title="매도호가 건수 2 (Ask order count level 2)",
        description="Number of ask orders at level 2, as a string.",
        examples=["3"],
    )
    bidno2: str = Field(
        ...,
        title="매수호가 건수 2 (Bid order count level 2)",
        description="Number of bid orders at level 2, as a string.",
        examples=["3"],
    )

    offerho3: str = Field(
        ...,
        title="매도호가 3 (Ask price level 3)",
        description="Ask price level 3. Returned as a string.",
        examples=["5026.00"],
    )
    bidho3: str = Field(
        ...,
        title="매수호가 3 (Bid price level 3)",
        description="Bid price level 3. Returned as a string.",
        examples=["5024.75"],
    )
    offerrem3: str = Field(
        ...,
        title="매도호가 잔량 3 (Ask remaining quantity level 3)",
        description="Remaining ask quantity at level 3 (contracts), as a string.",
        examples=["10"],
    )
    bidrem3: str = Field(
        ...,
        title="매수호가 잔량 3 (Bid remaining quantity level 3)",
        description="Remaining bid quantity at level 3 (contracts), as a string.",
        examples=["8"],
    )
    offerno3: str = Field(
        ...,
        title="매도호가 건수 3 (Ask order count level 3)",
        description="Number of ask orders at level 3, as a string.",
        examples=["2"],
    )
    bidno3: str = Field(
        ...,
        title="매수호가 건수 3 (Bid order count level 3)",
        description="Number of bid orders at level 3, as a string.",
        examples=["2"],
    )

    offerho4: str = Field(
        ...,
        title="매도호가 4 (Ask price level 4)",
        description="Ask price level 4. Returned as a string.",
        examples=["5026.25"],
    )
    bidho4: str = Field(
        ...,
        title="매수호가 4 (Bid price level 4)",
        description="Bid price level 4. Returned as a string.",
        examples=["5024.50"],
    )
    offerrem4: str = Field(
        ...,
        title="매도호가 잔량 4 (Ask remaining quantity level 4)",
        description="Remaining ask quantity at level 4 (contracts), as a string.",
        examples=["7"],
    )
    bidrem4: str = Field(
        ...,
        title="매수호가 잔량 4 (Bid remaining quantity level 4)",
        description="Remaining bid quantity at level 4 (contracts), as a string.",
        examples=["6"],
    )
    offerno4: str = Field(
        ...,
        title="매도호가 건수 4 (Ask order count level 4)",
        description="Number of ask orders at level 4, as a string.",
        examples=["2"],
    )
    bidno4: str = Field(
        ...,
        title="매수호가 건수 4 (Bid order count level 4)",
        description="Number of bid orders at level 4, as a string.",
        examples=["1"],
    )

    offerho5: str = Field(
        ...,
        title="매도호가 5 (Ask price level 5)",
        description="Ask price level 5. Returned as a string.",
        examples=["5026.50"],
    )
    bidho5: str = Field(
        ...,
        title="매수호가 5 (Bid price level 5)",
        description="Bid price level 5. Returned as a string.",
        examples=["5024.25"],
    )
    offerrem5: str = Field(
        ...,
        title="매도호가 잔량 5 (Ask remaining quantity level 5)",
        description="Remaining ask quantity at level 5 (contracts), as a string.",
        examples=["5"],
    )
    bidrem5: str = Field(
        ...,
        title="매수호가 잔량 5 (Bid remaining quantity level 5)",
        description="Remaining bid quantity at level 5 (contracts), as a string.",
        examples=["4"],
    )
    offerno5: str = Field(
        ...,
        title="매도호가 건수 5 (Ask order count level 5)",
        description="Number of ask orders at level 5, as a string.",
        examples=["1"],
    )
    bidno5: str = Field(
        ...,
        title="매수호가 건수 5 (Bid order count level 5)",
        description="Number of bid orders at level 5, as a string.",
        examples=["1"],
    )

    totoffercnt: str = Field(
        ...,
        title="매도호가총건수 (Total ask order count)",
        description="Total number of ask orders across all 5 levels, as a string.",
        examples=["13"],
    )
    totbidcnt: str = Field(
        ...,
        title="매수호가총건수 (Total bid order count)",
        description="Total number of bid orders across all 5 levels, as a string.",
        examples=["11"],
    )
    totofferrem: str = Field(
        ...,
        title="매도호가총수량 (Total ask remaining quantity)",
        description="Total remaining ask quantity across all 5 levels (contracts), as a string.",
        examples=["57"],
    )
    totbidrem: str = Field(
        ...,
        title="매수호가총수량 (Total bid remaining quantity)",
        description="Total remaining bid quantity across all 5 levels (contracts), as a string.",
        examples=["48"],
    )


class OVHRealResponse(BaseModel):
    header: Optional[OVHRealResponseHeader]
    body: Optional[OVHRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    """응답 코드"""
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
