"""Pydantic models for LS Securities OpenAPI WOC (Overseas Options Real-time Trade).

WOC is a Real-time WebSocket TR that pushes per-trade ticks for
overseas-options contracts. The ``WOCRealRequestBody`` carries the
WebSocket subscription envelope (``tr_cd`` + ``tr_key`` — short option
symbol padded to 8 characters); the ``WOCRealResponseBody`` carries the
per-tick push payload (price / volume / change / cumulative buy-sell
volumes). The response schema mirrors OVC's overseas-futures schema —
LS does not declare any options-specific extensions in the available
source for the trade-tick stream.

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
      WOC** (unlike OVC which has ``real_OVC.py``). ``tr_key`` and
      ``symbol`` examples therefore use neutral 8-character placeholders
      and explicitly disclaim the format — consume as accepted / returned
      by LS.
    - Options-specific instrument metadata (strike, expiry, call/put,
      moneyness) is NOT carried by the WOC trade-tick stream — those
      attributes are surfaced via the o3121 / o3125 master / detail TRs.
      This module preserves WOC's source schema verbatim and does not
      inject options-specific fields by inference.
    - All numeric fields are typed ``str`` in source — preserved verbatim.
      Stringified-numeric semantics not declared.
    - ``ydiffSign`` and ``cgubun`` enums are not declared in the available
      source — described as "consume as returned by LS".
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class WOCRealRequestHeader(BlockRealRequestHeader):
    """WOC real-time request header. Inherits the standard LS WS request header schema."""
    pass


class WOCRealResponseHeader(BlockRealResponseHeader):
    """WOC real-time response header. Inherits the standard LS WS response header schema."""
    pass


class WOCRealRequestBody(BaseModel):
    """WOCRealRequestBody — WebSocket subscription envelope for option trade-tick push.

    ``tr_key`` carries the short overseas-options contract symbol whose
    LS WSS encoding is **not declared in the available source**. The
    ``ensure_trailing_8_spaces`` validator right-pads to 8 characters for
    the LS WSS framing requirement.
    """

    tr_cd: str = Field(
        default="WOC",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'WOC'.",
        examples=["WOC"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short option symbol, 8-char space-padded)",
        description=(
            "Short overseas-options contract symbol used as the WS "
            "subscription key. The LS-internal symbol encoding for "
            "overseas options is not declared in the available source "
            "(no ``real_WOC.py`` example script exists, unlike OVC). "
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


class WOCRealRequest(BaseModel):
    """
    해외옵션 체결 WOC 실시간 요청 (Overseas Options Real-time Trade — request envelope).
    """
    header: WOCRealRequestHeader = Field(
        WOCRealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="WOC WebSocket subscription header block (token + tr_type)."
    )
    body: WOCRealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description="WOC (overseas-options trade tape) input body — TR code and 8-char space-padded option symbol.",
    )


class WOCRealResponseBody(BaseModel):
    """WOCRealResponseBody — per-tick trade push payload for an overseas-options contract.

    Schema mirrors OVC's overseas-futures trade-tick schema verbatim per
    source. Combines instrument identification, local- and Korea-time
    execution timestamps, last-trade price + change-vs-previous, daily
    OHLC, per-tick and cumulative volumes (split by buy / sell side),
    and a market-close flag.
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
            "Trade price for this tick in the contract's quote currency. "
            "Returned as a string — decimal scale, currency unit, and "
            "tick-size semantics not declared in available source."
        ),
        examples=["0"],
    )
    ydiffpr: str = Field(
        ...,
        title="전일대비 (Change vs. previous)",
        description=(
            "Absolute price change vs. previous trading day's settle / "
            "close. Returned as a string. Sign convention not declared."
        ),
        examples=["0"],
    )
    ydiffSign: str = Field(
        ...,
        title="전일대비기호 (Change-vs-previous sign code)",
        description=(
            "Sign / change-direction code vs. previous trading day. "
            "Complete enum mapping not declared in available source; "
            "consume as returned by LS."
        ),
        examples=["3"],
    )
    open: str = Field(
        ...,
        title="시가 (Open price)",
        description="Day's open price, as a string. Scale not declared.",
        examples=["0"],
    )
    high: str = Field(
        ...,
        title="고가 (High price)",
        description="Day's high price, as a string. Scale not declared.",
        examples=["0"],
    )
    low: str = Field(
        ...,
        title="저가 (Low price)",
        description="Day's low price, as a string. Scale not declared.",
        examples=["0"],
    )
    chgrate: str = Field(
        ...,
        title="등락율 (Change rate)",
        description=(
            "Percent change vs. previous trading day's settle / close, "
            "returned as a string. Scale and sign convention not declared "
            "in available source."
        ),
        examples=["0"],
    )
    trdq: str = Field(
        ...,
        title="건별체결수량 (Trade-tick quantity)",
        description="Quantity for this individual trade tick (contracts), as a string.",
        examples=["0"],
    )
    totq: str = Field(
        ...,
        title="누적체결수량 (Cumulative trade quantity)",
        description="Cumulative trade quantity for the session (contracts), as a string.",
        examples=["0"],
    )
    cgubun: str = Field(
        ...,
        title="체결구분 (Trade-side classifier)",
        description=(
            "Trade-side classifier. Complete enum mapping not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[""],
    )
    mdvolume: str = Field(
        ...,
        title="매도누적체결수량 (Cumulative sell-side trade quantity)",
        description="Cumulative sell-side trade quantity for the session (contracts), as a string.",
        examples=["0"],
    )
    msvolume: str = Field(
        ...,
        title="매수누적체결수량 (Cumulative buy-side trade quantity)",
        description="Cumulative buy-side trade quantity for the session (contracts), as a string.",
        examples=["0"],
    )
    ovsmkend: str = Field(
        ...,
        title="장마감일 (Market-close day flag)",
        description=(
            "Market-close-day flag for the contract. Code semantics "
            "(Y/N or date / classifier) not declared in available source; "
            "consume as returned by LS."
        ),
        examples=[""],
    )


class WOCRealResponse(BaseModel):
    header: Optional[WOCRealResponseHeader]
    body: Optional[WOCRealResponseBody]

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
