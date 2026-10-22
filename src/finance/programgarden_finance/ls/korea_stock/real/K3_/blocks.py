"""Pydantic models for LS Securities OpenAPI K3_ (KOSDAQ per-trade tick stream).

K3_ is a Real-time WebSocket TR that pushes per-trade tick data for
KOSDAQ-listed stocks.  Field structure is identical to S3_ (KOSPI
per-trade tick) — only the listing market differs.

The ``K3_RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — 6-digit short symbol code); the
``K3_RealResponseBody`` carries the per-tick push payload.

Field source policy: identical to S3_ (see that module's docstring for
the full policy).  ``examples`` for ``tr_key`` and ``shcode`` mirror the
example script (``src/finance/example/korea_stock/real_K3_.py`` uses
``"293490"``).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class K3_RealRequestHeader(BlockRealRequestHeader):
    """K3_ real-time request header. Inherits the standard LS WS request header schema."""
    pass


class K3_RealResponseHeader(BlockRealResponseHeader):
    """K3_ real-time response header. Inherits the standard LS WS response header schema."""
    pass


class K3_RealRequestBody(BaseModel):
    """K3_RealRequestBody — WebSocket subscription envelope for KOSDAQ per-trade tick push."""

    tr_cd: str = Field(
        default="K3_",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'K3_'.",
        examples=["K3_"],
    )
    tr_key: str = Field(
        ...,
        max_length=8,
        title="단축코드 (Short symbol code)",
        description="6-digit (or 8-character) KOSDAQ short symbol code.",
        examples=["293490", "086520"],
    )


class K3_RealRequest(BaseModel):
    """KOSDAQ 체결(K3_) 실시간 시세 등록/해제 요청."""
    header: K3_RealRequestHeader = Field(
        K3_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="K3_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: K3_RealRequestBody = Field(
        K3_RealRequestBody(tr_cd="K3_", tr_key=""),
        title="요청 바디 (Request body)",
        description="KOSDAQ 체결 실시간 등록에 필요한 종목코드 정보"
    )


class K3_RealResponseBody(BaseModel):
    """K3_RealResponseBody — KOSDAQ per-trade tick push payload (27 fields)."""

    chetime: str = Field(
        ...,
        title="체결시간 (Trade time)",
        description="Trade execution time in HHMMSS format.",
        examples=["104904", "153000"],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Prior-day change sign)",
        description=(
            "Prior-day change sign code. LS-source-declared values: "
            "'1'=upper limit, '2'=up, '3'=unchanged, '4'=lower limit, '5'=down."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: str = Field(
        ...,
        title="전일대비 (Prior-day change)",
        description=(
            "Magnitude of prior-day change in price (always non-negative; "
            "direction encoded in ``sign``). Decimal scale not declared."
        ),
        examples=["3500", "0"],
    )
    drate: str = Field(
        ...,
        title="등락율 (Change rate)",
        description="Prior-day change rate in percent (sign carried by ``sign``).",
        examples=["29.68", "0.00"],
    )
    price: str = Field(
        ...,
        title="현재가 (Current price)",
        description="Current trade price.",
        examples=["28000"],
    )
    opentime: str = Field(
        ...,
        title="시가시간 (Open time)",
        description="Time at which the open price was formed (HHMMSS).",
        examples=["090000"],
    )
    open: str = Field(
        ...,
        title="시가 (Open)",
        description="Session open price.",
        examples=["27000"],
    )
    hightime: str = Field(
        ...,
        title="고가시간 (High time)",
        description="Time at which the session high was formed (HHMMSS).",
        examples=["100515"],
    )
    high: str = Field(
        ...,
        title="고가 (High)",
        description="Session high price.",
        examples=["29000"],
    )
    lowtime: str = Field(
        ...,
        title="저가시간 (Low time)",
        description="Time at which the session low was formed (HHMMSS).",
        examples=["093015"],
    )
    low: str = Field(
        ...,
        title="저가 (Low)",
        description="Session low price.",
        examples=["26500"],
    )
    cgubun: str = Field(
        ...,
        title="체결구분 (Trade side)",
        description=(
            "Trade side code. LS-source-declared values: '+'=buy-side fill, "
            "'-'=sell-side fill."
        ),
        examples=["+", "-"],
    )
    cvolume: str = Field(
        ...,
        title="체결량 (Trade volume)",
        description="Volume of this individual trade.",
        examples=["100", "1234"],
    )
    volume: str = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative session volume up to this trade.",
        examples=["1234567"],
    )
    value: str = Field(
        ...,
        title="누적거래대금 (Cumulative trade value)",
        description=(
            "Cumulative session trade value. Korean source labels the unit "
            "as '백만원' (million KRW) — preserved verbatim."
        ),
        examples=["12345"],
    )
    mdvolume: str = Field(
        ...,
        title="매도누적체결량 (Cumulative sell-side volume)",
        description="Cumulative sell-side fill volume for the session.",
        examples=["654321"],
    )
    mdchecnt: str = Field(
        ...,
        title="매도누적체결건수 (Cumulative sell-side fill count)",
        description="Cumulative sell-side fill count for the session.",
        examples=["1234"],
    )
    msvolume: str = Field(
        ...,
        title="매수누적체결량 (Cumulative buy-side volume)",
        description="Cumulative buy-side fill volume for the session.",
        examples=["580246"],
    )
    mschecnt: str = Field(
        ...,
        title="매수누적체결건수 (Cumulative buy-side fill count)",
        description="Cumulative buy-side fill count for the session.",
        examples=["1120"],
    )
    cpower: str = Field(
        ...,
        title="체결강도 (Trade strength)",
        description=(
            "Trade strength. LS-source-declared formula: "
            "cpower = msvolume / mdvolume * 100 (in percent)."
        ),
        examples=["44.30", "332.56"],
    )
    w_avrg: str = Field(
        ...,
        title="가중평균가 (Volume-weighted average price)",
        description="Volume-weighted average price (VWAP).",
        examples=["27800"],
    )
    offerho: str = Field(
        ...,
        title="매도호가 (Best ask price)",
        description="Current best ask (level-1 sell quote).",
        examples=["28000"],
    )
    bidho: str = Field(
        ...,
        title="매수호가 (Best bid price)",
        description="Current best bid (level-1 buy quote).",
        examples=["27950"],
    )
    status: str = Field(
        ...,
        title="장정보 (Session phase code)",
        description=(
            "Session phase code. LS-source-declared value: '00'=intraday. "
            "Other LS-defined codes may appear — consume as returned by LS."
        ),
        examples=["00"],
    )
    jnilvolume: str = Field(
        ...,
        title="전일동시간대거래량 (Prior-day same-time cumulative volume)",
        description="Prior trading day's cumulative volume up to the same time-of-day.",
        examples=["1023456"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="6-digit short symbol code matching the subscribed ``tr_key``.",
        examples=["293490", "086520"],
    )
    exchname: str = Field(
        ...,
        title="거래소명 (Exchange name)",
        description="Exchange name string. Typically 'KRX' for this TR.",
        examples=["KRX"],
    )


class K3_RealResponse(BaseModel):
    """KOSDAQ 체결(K3_) 실시간 응답.

    Complete response model for K3_ real-time KOSDAQ per-trade tick data.
    """
    header: Optional[K3_RealResponseHeader]
    body: Optional[K3_RealResponseBody]

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
