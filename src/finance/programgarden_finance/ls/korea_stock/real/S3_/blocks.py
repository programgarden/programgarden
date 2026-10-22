"""Pydantic models for LS Securities OpenAPI S3_ (KOSPI per-trade tick stream).

S3_ is a Real-time WebSocket TR that pushes per-trade tick data for
KOSPI-listed stocks during the regular session (09:00–15:30 KST).  The
``S3_RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — 6-digit short symbol code); the
``S3_RealResponseBody`` carries the per-tick push payload — execution
time, price, volume, prior-day change, OHLC, cumulative buy / sell
volume and counts, trade strength and the best bid / ask snapshot.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - ``sign`` enum (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) is preserved
      verbatim — same convention as Phase 4b chart and 4f market TRs.
    - ``cgubun`` enum ('+' = buy fill, '-' = sell fill) is preserved
      verbatim.
    - ``status`` enum ('00'=장중 / '21'=장전예상체결 / '31'=장후예상체결, plus
      "etc.") is preserved verbatim with the in-codebase 'etc.' fallback —
      other LS-defined codes may appear; consume as returned by LS.
    - Trade-strength formula ``cpower = msvolume / mdvolume * 100`` is
      preserved verbatim from the in-codebase Korean source.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.  ``value`` is
      labelled "백만원" (million KRW) per Korean source — preserved
      verbatim.
    - ``examples`` for ``tr_key`` and ``shcode`` mirror the example script
      (``src/finance/example/korea_stock/real_S3_.py`` uses ``"005930"``).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class S3_RealRequestHeader(BlockRealRequestHeader):
    """S3_ real-time request header. Inherits the standard LS WS request header schema."""
    pass


class S3_RealResponseHeader(BlockRealResponseHeader):
    """S3_ real-time response header. Inherits the standard LS WS response header schema."""
    pass


class S3_RealRequestBody(BaseModel):
    """S3_RealRequestBody — WebSocket subscription envelope for KOSPI per-trade tick push."""

    tr_cd: str = Field(
        default="S3_",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'S3_'.",
        examples=["S3_"],
    )
    tr_key: str = Field(
        ...,
        max_length=8,
        title="단축코드 (Short symbol code)",
        description="6-digit (or 8-character) KOSPI short symbol code.",
        examples=["005930", "035420"],
    )


class S3_RealRequest(BaseModel):
    """KOSPI 체결(S3_) 실시간 시세 등록/해제 요청."""
    header: S3_RealRequestHeader = Field(
        S3_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="S3_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: S3_RealRequestBody = Field(
        S3_RealRequestBody(tr_cd="S3_", tr_key=""),
        title="요청 바디 (Request body)",
        description="KOSPI 체결 실시간 등록에 필요한 종목코드 정보"
    )


class S3_RealResponseBody(BaseModel):
    """S3_RealResponseBody — KOSPI per-trade tick push payload (27 fields)."""

    chetime: str = Field(
        ...,
        title="체결시간 (Trade time)",
        description="Trade execution time in HHMMSS format.",
        examples=["090851", "153000"],
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
        examples=["1500", "0"],
    )
    drate: str = Field(
        ...,
        title="등락율 (Change rate)",
        description="Prior-day change rate in percent (sign carried by ``sign``).",
        examples=["1.93", "0.00"],
    )
    price: str = Field(
        ...,
        title="현재가 (Current price)",
        description="Current trade price.",
        examples=["73500"],
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
        examples=["73000"],
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
        examples=["74100"],
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
        examples=["72800"],
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
        examples=["12345678"],
    )
    value: str = Field(
        ...,
        title="누적거래대금 (Cumulative trade value)",
        description=(
            "Cumulative session trade value. Korean source labels the unit "
            "as '백만원' (million KRW) — preserved verbatim."
        ),
        examples=["123456"],
    )
    mdvolume: str = Field(
        ...,
        title="매도누적체결량 (Cumulative sell-side volume)",
        description="Cumulative sell-side fill volume for the session.",
        examples=["6543210"],
    )
    mdchecnt: str = Field(
        ...,
        title="매도누적체결건수 (Cumulative sell-side fill count)",
        description="Cumulative sell-side fill count for the session.",
        examples=["12345"],
    )
    msvolume: str = Field(
        ...,
        title="매수누적체결량 (Cumulative buy-side volume)",
        description="Cumulative buy-side fill volume for the session.",
        examples=["5802468"],
    )
    mschecnt: str = Field(
        ...,
        title="매수누적체결건수 (Cumulative buy-side fill count)",
        description="Cumulative buy-side fill count for the session.",
        examples=["11200"],
    )
    cpower: str = Field(
        ...,
        title="체결강도 (Trade strength)",
        description=(
            "Trade strength. LS-source-declared formula: "
            "cpower = msvolume / mdvolume * 100 (in percent)."
        ),
        examples=["332.56", "44.30"],
    )
    w_avrg: str = Field(
        ...,
        title="가중평균가 (Volume-weighted average price)",
        description="Volume-weighted average price (VWAP).",
        examples=["73250"],
    )
    offerho: str = Field(
        ...,
        title="매도호가 (Best ask price)",
        description="Current best ask (level-1 sell quote).",
        examples=["73500"],
    )
    bidho: str = Field(
        ...,
        title="매수호가 (Best bid price)",
        description="Current best bid (level-1 buy quote).",
        examples=["73400"],
    )
    status: str = Field(
        ...,
        title="장정보 (Session phase code)",
        description=(
            "Session phase code. LS-source-declared values: '00'=intraday, "
            "'21'=pre-open expected fill, '31'=post-close expected fill, etc. "
            "Other LS-defined codes may appear — consume as returned by LS."
        ),
        examples=["00", "21", "31"],
    )
    jnilvolume: str = Field(
        ...,
        title="전일동시간대거래량 (Prior-day same-time cumulative volume)",
        description="Prior trading day's cumulative volume up to the same time-of-day.",
        examples=["10234567"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="6-digit short symbol code matching the subscribed ``tr_key``.",
        examples=["005930", "035420"],
    )
    exchname: str = Field(
        ...,
        title="거래소명 (Exchange name)",
        description="Exchange name string. Typically 'KRX' for this TR.",
        examples=["KRX"],
    )


class S3_RealResponse(BaseModel):
    """KOSPI 체결(S3_) 실시간 응답.

    Complete response model for S3_ real-time KOSPI per-trade tick data.
    """
    header: Optional[S3_RealResponseHeader]
    body: Optional[S3_RealResponseBody]

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
