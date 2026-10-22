"""Pydantic models for LS Securities OpenAPI WOH (Overseas Options Real-time Orderbook).

WOH is a Real-time WebSocket TR that pushes the 5-level bid / ask
orderbook for an overseas-options contract. The ``WOHRealRequestBody``
carries the WebSocket subscription envelope (``tr_cd`` + ``tr_key`` —
short option symbol padded to 8 characters); the ``WOHRealResponseBody``
carries the per-update push payload (5 ask + 5 bid levels with prices,
remaining quantities, and order counts; plus totals). The response
schema mirrors OVH's overseas-futures schema — LS does not declare any
options-specific extensions in the available source for the orderbook
stream.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Decimal scale, currency unit, contract multiplier, strike, and tick
      value are NOT declared in the available source — examples are
      illustrative shapes only and must not be treated as authoritative
      scale references.
    - The LS WSS short-symbol encoding for overseas options is NOT
      declared in the available source and **no example script exists for
      WOH** (unlike OVH which has ``real_OVH.py``). ``tr_key`` and
      ``symbol`` examples therefore use neutral 8-character placeholders
      and explicitly disclaim the format — consume as accepted / returned
      by LS.
    - All numeric fields are typed ``str`` in source — preserved verbatim.
      Stringified-numeric semantics not declared.
    - The 5 orderbook levels are documented as standard 1..5 best-bid /
      best-ask depth. No source-level constraint marker is declared for WOH.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class WOHRealRequestHeader(BlockRealRequestHeader):
    """WOH real-time request header. Inherits the standard LS WS request header schema."""
    pass


class WOHRealResponseHeader(BlockRealResponseHeader):
    """WOH real-time response header. Inherits the standard LS WS response header schema."""
    pass


class WOHRealRequestBody(BaseModel):
    """WOHRealRequestBody — WebSocket subscription envelope for option orderbook push.

    ``tr_key`` carries the short overseas-options contract symbol whose
    LS WSS encoding is **not declared in the available source**. The
    ``ensure_trailing_8_spaces`` validator right-pads to 8 characters for
    the LS WSS framing requirement.
    """

    tr_cd: str = Field(
        default="WOH",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'WOH'.",
        examples=["WOH"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short option symbol, 8-char space-padded)",
        description=(
            "Short overseas-options contract symbol used as the WS "
            "subscription key. The LS-internal symbol encoding for "
            "overseas options is not declared in the available source "
            "(no ``real_WOH.py`` example script exists, unlike OVH). "
            "Right-padded with spaces to 8 characters by the validator. "
            "Pass the symbol exactly as accepted by LS — do not assume "
            "futures-style root+expiry encoding."
        ),
        examples=[""],
    )

    @field_validator("tr_key", mode="before")
    def ensure_trailing_8_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)[:8]
        return s.ljust(8)

    model_config = ConfigDict(validate_assignment=True)


class WOHRealRequest(BaseModel):
    header: WOHRealRequestHeader = Field(
        WOHRealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="WOH WebSocket subscription header block (token + tr_type)."
    )
    body: WOHRealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description="WOH (overseas-options orderbook) input body — TR code and 8-char space-padded option symbol.",
    )


class WOHRealResponseBody(BaseModel):
    """WOHRealResponseBody — per-update orderbook push payload for an overseas-options contract.

    Schema mirrors OVH's overseas-futures orderbook schema verbatim per
    source. Contains symbol identification, an LS-side timestamp, and 5
    ask / 5 bid levels (price + remaining quantity + order count per
    level), plus totals across all levels.
    """

    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / contract code)",
        description=(
            "Overseas-options contract code as returned by LS. The "
            "LS-internal symbol encoding for overseas options is not "
            "declared in the available source — consume as returned."
        ),
        examples=[""],
    )
    hotime: str = Field(
        ...,
        title="호가시간 (Orderbook timestamp)",
        description=(
            "Orderbook update timestamp. Format / time zone not declared "
            "in available source; consume as returned by LS."
        ),
        examples=["093015"],
    )

    offerho1: str = Field(
        ...,
        title="매도호가 1 (Ask price level 1)",
        description="Best ask price (level 1), as a string. Scale not declared.",
        examples=["0"],
    )
    bidho1: str = Field(
        ...,
        title="매수호가 1 (Bid price level 1)",
        description="Best bid price (level 1), as a string. Scale not declared.",
        examples=["0"],
    )
    offerrem1: str = Field(
        ...,
        title="매도호가 잔량 1 (Ask remaining quantity level 1)",
        description="Remaining ask quantity at level 1 (contracts), as a string.",
        examples=["0"],
    )
    bidrem1: str = Field(
        ...,
        title="매수호가 잔량 1 (Bid remaining quantity level 1)",
        description="Remaining bid quantity at level 1 (contracts), as a string.",
        examples=["0"],
    )
    offerno1: str = Field(
        ...,
        title="매도호가 건수 1 (Ask order count level 1)",
        description="Number of ask orders at level 1, as a string.",
        examples=["0"],
    )
    bidno1: str = Field(
        ...,
        title="매수호가 건수 1 (Bid order count level 1)",
        description="Number of bid orders at level 1, as a string.",
        examples=["0"],
    )

    offerho2: str = Field(
        ...,
        title="매도호가 2 (Ask price level 2)",
        description="Ask price level 2, as a string. Scale not declared.",
        examples=["0"],
    )
    bidho2: str = Field(
        ...,
        title="매수호가 2 (Bid price level 2)",
        description="Bid price level 2, as a string. Scale not declared.",
        examples=["0"],
    )
    offerrem2: str = Field(
        ...,
        title="매도호가 잔량 2 (Ask remaining quantity level 2)",
        description="Remaining ask quantity at level 2 (contracts), as a string.",
        examples=["0"],
    )
    bidrem2: str = Field(
        ...,
        title="매수호가 잔량 2 (Bid remaining quantity level 2)",
        description="Remaining bid quantity at level 2 (contracts), as a string.",
        examples=["0"],
    )
    offerno2: str = Field(
        ...,
        title="매도호가 건수 2 (Ask order count level 2)",
        description="Number of ask orders at level 2, as a string.",
        examples=["0"],
    )
    bidno2: str = Field(
        ...,
        title="매수호가 건수 2 (Bid order count level 2)",
        description="Number of bid orders at level 2, as a string.",
        examples=["0"],
    )

    offerho3: str = Field(
        ...,
        title="매도호가 3 (Ask price level 3)",
        description="Ask price level 3, as a string. Scale not declared.",
        examples=["0"],
    )
    bidho3: str = Field(
        ...,
        title="매수호가 3 (Bid price level 3)",
        description="Bid price level 3, as a string. Scale not declared.",
        examples=["0"],
    )
    offerrem3: str = Field(
        ...,
        title="매도호가 잔량 3 (Ask remaining quantity level 3)",
        description="Remaining ask quantity at level 3 (contracts), as a string.",
        examples=["0"],
    )
    bidrem3: str = Field(
        ...,
        title="매수호가 잔량 3 (Bid remaining quantity level 3)",
        description="Remaining bid quantity at level 3 (contracts), as a string.",
        examples=["0"],
    )
    offerno3: str = Field(
        ...,
        title="매도호가 건수 3 (Ask order count level 3)",
        description="Number of ask orders at level 3, as a string.",
        examples=["0"],
    )
    bidno3: str = Field(
        ...,
        title="매수호가 건수 3 (Bid order count level 3)",
        description="Number of bid orders at level 3, as a string.",
        examples=["0"],
    )

    offerho4: str = Field(
        ...,
        title="매도호가 4 (Ask price level 4)",
        description="Ask price level 4, as a string. Scale not declared.",
        examples=["0"],
    )
    bidho4: str = Field(
        ...,
        title="매수호가 4 (Bid price level 4)",
        description="Bid price level 4, as a string. Scale not declared.",
        examples=["0"],
    )
    offerrem4: str = Field(
        ...,
        title="매도호가 잔량 4 (Ask remaining quantity level 4)",
        description="Remaining ask quantity at level 4 (contracts), as a string.",
        examples=["0"],
    )
    bidrem4: str = Field(
        ...,
        title="매수호가 잔량 4 (Bid remaining quantity level 4)",
        description="Remaining bid quantity at level 4 (contracts), as a string.",
        examples=["0"],
    )
    offerno4: str = Field(
        ...,
        title="매도호가 건수 4 (Ask order count level 4)",
        description="Number of ask orders at level 4, as a string.",
        examples=["0"],
    )
    bidno4: str = Field(
        ...,
        title="매수호가 건수 4 (Bid order count level 4)",
        description="Number of bid orders at level 4, as a string.",
        examples=["0"],
    )

    offerho5: str = Field(
        ...,
        title="매도호가 5 (Ask price level 5)",
        description="Ask price level 5, as a string. Scale not declared.",
        examples=["0"],
    )
    bidho5: str = Field(
        ...,
        title="매수호가 5 (Bid price level 5)",
        description="Bid price level 5, as a string. Scale not declared.",
        examples=["0"],
    )
    offerrem5: str = Field(
        ...,
        title="매도호가 잔량 5 (Ask remaining quantity level 5)",
        description="Remaining ask quantity at level 5 (contracts), as a string.",
        examples=["0"],
    )
    bidrem5: str = Field(
        ...,
        title="매수호가 잔량 5 (Bid remaining quantity level 5)",
        description="Remaining bid quantity at level 5 (contracts), as a string.",
        examples=["0"],
    )
    offerno5: str = Field(
        ...,
        title="매도호가 건수 5 (Ask order count level 5)",
        description="Number of ask orders at level 5, as a string.",
        examples=["0"],
    )
    bidno5: str = Field(
        ...,
        title="매수호가 건수 5 (Bid order count level 5)",
        description="Number of bid orders at level 5, as a string.",
        examples=["0"],
    )

    totoffercnt: str = Field(
        ...,
        title="매도호가총건수 (Total ask order count)",
        description="Total number of ask orders across all 5 levels, as a string.",
        examples=["0"],
    )
    totbidcnt: str = Field(
        ...,
        title="매수호가총건수 (Total bid order count)",
        description="Total number of bid orders across all 5 levels, as a string.",
        examples=["0"],
    )
    totofferrem: str = Field(
        ...,
        title="매도호가총수량 (Total ask remaining quantity)",
        description="Total remaining ask quantity across all 5 levels (contracts), as a string.",
        examples=["0"],
    )
    totbidrem: str = Field(
        ...,
        title="매수호가총수량 (Total bid remaining quantity)",
        description="Total remaining bid quantity across all 5 levels (contracts), as a string.",
        examples=["0"],
    )


class WOHRealResponse(BaseModel):
    header: Optional[WOHRealResponseHeader]
    body: Optional[WOHRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
