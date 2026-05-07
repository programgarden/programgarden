"""Pydantic models for LS Securities OpenAPI OVC (Overseas Futures Real-time Trade).

OVC is a Real-time WebSocket TR that pushes per-trade ticks for
overseas-futures contracts. The ``OVCRealRequestBody`` carries the
WebSocket subscription envelope (``tr_cd`` + ``tr_key`` — short symbol
such as ``"ESZ25"`` padded to 8 characters per the example script);
the ``OVCRealResponseBody`` carries the per-tick push payload (price /
volume / change / cumulative buy-sell volumes). The set of supported
exchanges and contract categories is not enumerated in the available
source.

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
      verbatim. Stringified-numeric semantics (leading zeros, sign prefix,
      trailing decimals) are not declared and must be consumed as returned
      by LS.
    - ``ydiffSign`` and ``cgubun`` enums are not declared in the available
      source — described as "consume as returned by LS." rather than
      inferred from cross-TR knowledge.
    - ``examples`` for ``tr_key`` come from
      ``src/finance/example/overseas_futureoption/real_OVC.py`` ("ESZ25"
      padded to 8 characters); response examples mirror typical LS WS
      futures-tick payload shapes.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class OVCRealRequestHeader(BlockRealRequestHeader):
    """OVC real-time request header. Inherits the standard LS WS request header schema."""
    pass


class OVCRealResponseHeader(BlockRealResponseHeader):
    """OVC real-time response header. Inherits the standard LS WS response header schema."""
    pass


class OVCRealRequestBody(BaseModel):
    """OVCRealRequestBody — WebSocket subscription envelope for futures trade-tick push.

    ``tr_key`` is the short overseas-futures contract symbol (e.g. ``"ESZ25"``
    for CME E-mini S&P 500 Dec 2025); the ``ensure_trailing_8_spaces``
    validator right-pads to 8 characters for the LS WSS framing requirement.
    """

    tr_cd: str = Field(
        default="OVC",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'OVC'.",
        examples=["OVC"],
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


class OVCRealRequest(BaseModel):
    """
    해외선물 체결 실시간 요청 (Overseas Futures Real-time Trade — request envelope).
    """
    header: OVCRealRequestHeader = Field(
        OVCRealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="OVC WebSocket subscription header block (token + tr_type)."
    )
    body: OVCRealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description="해외선물 체결 input body — TR code and 8-char space-padded futures symbol.",
    )


class OVCRealResponseBody(BaseModel):
    """OVCRealResponseBody — per-tick trade push payload for an overseas-futures contract.

    Combines instrument identification (``symbol``), local- and Korea-time
    execution timestamps, last-trade price + change-vs-previous, daily OHLC,
    per-tick and cumulative volumes (split by buy / sell side), and a
    market-close flag.
    """

    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / contract code)",
        description=(
            "Overseas-futures contract code (root + expiry, e.g. 'ESZ25', "
            "'NQU26')."
        ),
        examples=["ESZ25", "NQU26"],
    )
    ovsdate: str = Field(
        ...,
        title="체결일자(현지) (Execution date — local exchange)",
        description="Execution date at the local exchange in YYYYMMDD format.",
        examples=["20260505"],
    )
    kordate: str = Field(
        ...,
        title="체결일자(한국) (Execution date — Korea local time)",
        description="Execution date in Korea local time, YYYYMMDD format.",
        examples=["20260506"],
    )
    trdtm: str = Field(
        ...,
        title="체결시간(현지) (Execution time — local exchange)",
        description="Execution time at the local exchange in HHMMSS format.",
        examples=["093015"],
    )
    kortm: str = Field(
        ...,
        title="체결시간(한국) (Execution time — Korea local time)",
        description="Execution time in Korea local time, HHMMSS format.",
        examples=["223015"],
    )
    curpr: str = Field(
        ...,
        title="체결가격 (Trade price)",
        description=(
            "Trade price for this tick. Returned as a string — decimal "
            "scale and tick-size semantics not declared in available "
            "source; consume as returned by LS."
        ),
        examples=["5025.25", "17890.50"],
    )
    ydiffpr: str = Field(
        ...,
        title="전일대비 (Change vs. previous)",
        description=(
            "Absolute price change vs. previous trading day's settle / "
            "close. Returned as a string."
        ),
        examples=["12.50", "-3.25"],
    )
    ydiffSign: str = Field(
        ...,
        title="전일대비기호 (Change-vs-previous sign code)",
        description=(
            "Sign / change-direction code vs. previous trading day. "
            "Complete enum mapping not declared in available source; "
            "consume as returned by LS."
        ),
        examples=["2", "5", "3"],
    )
    open: str = Field(
        ...,
        title="시가 (Open price)",
        description="Day's open price (string).",
        examples=["5012.75"],
    )
    high: str = Field(
        ...,
        title="고가 (High price)",
        description="Day's high price (string).",
        examples=["5040.00"],
    )
    low: str = Field(
        ...,
        title="저가 (Low price)",
        description="Day's low price (string).",
        examples=["5008.25"],
    )
    chgrate: str = Field(
        ...,
        title="등락율 (Change rate)",
        description=(
            "Percent change vs. previous trading day's settle / close, "
            "returned as a string. Scale and sign convention not declared "
            "in available source."
        ),
        examples=["0.25", "-0.06"],
    )
    trdq: str = Field(
        ...,
        title="건별체결수량 (Trade-tick quantity)",
        description="Quantity for this individual trade tick (contracts), as a string.",
        examples=["1", "5"],
    )
    totq: str = Field(
        ...,
        title="누적체결수량 (Cumulative trade quantity)",
        description="Cumulative trade quantity for the session (contracts), as a string.",
        examples=["125000"],
    )
    cgubun: str = Field(
        ...,
        title="체결구분 (Trade-side classifier)",
        description=(
            "Trade-side classifier (typically '+' = buy-side, '-' = sell-"
            "side). Complete enum not declared in available source; consume "
            "as returned by LS."
        ),
        examples=["+", "-"],
    )
    mdvolume: str = Field(
        ...,
        title="매도누적체결수량 (Cumulative sell-side trade quantity)",
        description="Cumulative sell-side trade quantity for the session (contracts), as a string.",
        examples=["62000"],
    )
    msvolume: str = Field(
        ...,
        title="매수누적체결수량 (Cumulative buy-side trade quantity)",
        description="Cumulative buy-side trade quantity for the session (contracts), as a string.",
        examples=["63000"],
    )
    ovsmkend: str = Field(
        ...,
        title="장마감일 (Market-close day flag)",
        description=(
            "Market-close-day flag for the contract. Code semantics "
            "(Y/N or date / classifier) not declared in available "
            "source; consume as returned by LS."
        ),
        examples=["N", "Y"],
    )


class OVCRealResponse(BaseModel):
    header: Optional[OVCRealResponseHeader]
    body: Optional[OVCRealResponseBody]

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
