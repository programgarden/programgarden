"""Pydantic models for LS Securities OpenAPI GSC (Overseas Stock Real-time Trade).

GSC is a Real-time WebSocket TR that pushes per-trade market-data ticks for
overseas-stock symbols (US markets — NYSE / NASDAQ / AMEX). The
``GSCRealRequestBody`` carries the WebSocket subscription envelope (``tr_cd``
+ ``tr_key`` — exchange-prefixed symbol such as ``"81SOXL"`` padded to 18
characters); the ``GSCRealResponseBody`` carries the per-tick push payload
(price / volume / change / 52-week range).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.
    - ``sign`` and ``cgubun`` enums are not exhaustively listed in the
      Korean source's in-line comments — described as "consume as returned
      by LS." rather than inferred from cross-TR knowledge.
    - ``examples`` for ``tr_key`` come from
      ``src/finance/example/overseas_stock/real_GSC.py`` ("81SOXL"); response
      examples mirror typical LS WS quote-push payload shapes.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class GSCRealRequestHeader(BlockRealRequestHeader):
    """GSC real-time request header. Inherits the standard LS WS request header schema."""
    pass


class GSCRealResponseHeader(BlockRealResponseHeader):
    """GSC real-time response header. Inherits the standard LS WS response header schema."""
    pass


class GSCRealRequestBody(BaseModel):
    """GSCRealRequestBody — WebSocket subscription envelope for trade-tick push.

    ``tr_key`` is the LS-internal 18-character key combining exchange code
    and ticker; if shorter, it is right-padded with spaces by the validator
    below.
    """

    tr_cd: str = Field(
        default="GSC",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'GSC'.",
        examples=["GSC"],
    )
    tr_key: str = Field(
        ...,
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


class GSCRealRequest(BaseModel):
    """
    해외주식 실시간 시세 요청 (Overseas Stock Real-time Trade — request envelope).
    """
    header: GSCRealRequestHeader = Field(
        GSCRealRequestHeader(
            token="",
            tr_type="3"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="GSC WebSocket subscription header block (token + tr_type)."
    )
    body: GSCRealRequestBody = Field(
        GSCRealRequestBody(
            tr_cd="GSC",
            tr_key=""
        ),
        title="입력 데이터 블록 (Input body block)",
        description="해외주식 실시간 시세 input body — TR code and 18-char exchange-prefixed key.",
    )


class GSCRealResponseBody(BaseModel):
    """GSCRealResponseBody — per-tick trade push payload for a US overseas stock.

    Field labels are sourced from the LS WSS GSC response specification.
    Decimal scale and currency unit are not declared in the available
    source.
    """

    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'SOXL', 'AAPL').",
        examples=["SOXL", "AAPL"],
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
        description="Execution date in Korea local time, YYYYMMDD.",
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
        description="Execution time in Korea local time, HHMMSS.",
        examples=["223015"],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Change-vs-previous sign code)",
        description=(
            "Sign / change-direction code vs. previous trading day. Complete "
            "enum mapping not declared in available source; consume as "
            "returned by LS."
        ),
        examples=["2", "5", "3"],
    )
    price: float = Field(
        ...,
        title="체결가격 (Trade price)",
        description=(
            "Trade price for this tick. Decimal scale not declared in "
            "available source — consume as returned by LS."
        ),
        examples=[12.24, 250.55],
    )
    diff: float = Field(
        ...,
        title="전일대비 (Change vs. previous)",
        description="Absolute change vs. previous trading day's close.",
        examples=[-0.08, 1.25],
    )
    rate: float = Field(
        ...,
        title="등락율 (Change rate)",
        description="Percent change vs. previous trading day's close.",
        examples=[-0.65, 0.50],
    )
    open: float = Field(
        ...,
        title="시가 (Open price)",
        description="Day's open price.",
        examples=[12.30, 248.00],
    )
    high: float = Field(
        ...,
        title="고가 (High price)",
        description="Day's high price.",
        examples=[12.45, 252.00],
    )
    low: float = Field(
        ...,
        title="저가 (Low price)",
        description="Day's low price.",
        examples=[12.10, 247.00],
    )
    trdq: int = Field(
        ...,
        title="건별체결수량 (Trade-tick quantity)",
        description="Quantity for this individual trade tick (shares).",
        examples=[100, 1],
    )
    totq: int = Field(
        ...,
        title="누적체결수량 (Cumulative trade quantity)",
        description="Cumulative trade quantity for the day (shares).",
        examples=[1000000],
    )
    cgubun: str = Field(
        ...,
        title="체결구분 (Trade-side classifier)",
        description=(
            "Trade-side classifier (typically '+' = buy-side, '-' = sell-side). "
            "Complete enum not declared in available source; consume as returned by LS."
        ),
        examples=["+", "-"],
    )
    lSeq: int = Field(
        ...,
        title="초당시퀀스 (Per-second sequence number)",
        description="Per-second sequence number assigned by LS for tick ordering.",
        examples=[1, 2, 99],
    )
    amount: int = Field(
        ...,
        title="누적거래대금 (Cumulative trade value)",
        description=(
            "Cumulative trade value for the day. Currency unit not declared "
            "in available source."
        ),
        examples=[12500000],
    )
    high52p: float = Field(
        ...,
        title="52주고가 (52-week high)",
        description="52-week high price.",
        examples=[15.50, 300.00],
    )
    low52p: float = Field(
        ...,
        title="52주저가 (52-week low)",
        description="52-week low price.",
        examples=[8.25, 150.00],
    )


class GSCRealResponse(BaseModel):
    header: Optional[GSCRealResponseHeader]
    body: Optional[GSCRealResponseBody]

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
