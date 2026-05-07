"""Pydantic models for LS Securities OpenAPI IJ_ (Korea sector / industry index).

IJ_ is a Real-time WebSocket TR that pushes per-tick sector / industry
index updates for KOSPI / KOSDAQ sector codes.  The
``IJ_RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — 3-digit sector code, e.g. ``'001'`` for the
KOSPI composite); the ``IJ_RealResponseBody`` carries the per-tick
push payload — index value, prior-day change / sign / rate, advancing /
declining counts, OHLC index values with their formation times, and
foreign / institutional net trading volume / value.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - ``sign`` enum (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) is preserved
      verbatim — same convention as Phase 4b/c/d/e/g chart and ranking TRs.
    - Decimal scale of index values, currency unit of trading values, and
      the time-series / aggregation window of cumulative volume / value
      are NOT declared in the available source — examples use illustrative
      values only.  ``value``, ``frgsvalue``, ``orgsvalue`` are labelled
      "백만원" (million KRW) in the in-codebase Korean source — preserved
      verbatim.
    - ``frgsvolume`` / ``orgsvolume`` and ``frgsvalue`` / ``orgsvalue``
      net-trading sign convention (positive = net buy, negative = net sell)
      mirrors LS-typical convention but is not source-declared — examples
      show both polarities + zero, no sign assertion.
    - ``upcode`` 3-digit sector codes (``'001'`` KOSPI composite,
      ``'301'`` KOSDAQ composite) are LS-documented; other sector codes
      may appear — consume as returned.  ``examples`` mirror the example
      script (``src/finance/example/korea_stock/real_IJ_.py``).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class IJ_RealRequestHeader(BlockRealRequestHeader):
    """IJ_ real-time request header. Inherits the standard LS WS request header schema."""
    pass


class IJ_RealResponseHeader(BlockRealResponseHeader):
    """IJ_ real-time response header. Inherits the standard LS WS response header schema."""
    pass


class IJ_RealRequestBody(BaseModel):
    """IJ_RealRequestBody — WebSocket subscription envelope for sector index push."""

    tr_cd: str = Field(
        default="IJ_",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'IJ_'.",
        examples=["IJ_"],
    )
    tr_key: str = Field(
        ...,
        max_length=8,
        title="업종코드 (Sector code)",
        description=(
            "3-digit sector code. LS-documented examples: '001' = KOSPI "
            "composite, '301' = KOSDAQ composite. Other LS-defined sector "
            "codes may appear — consume as returned by LS."
        ),
        examples=["001", "301"],
    )


class IJ_RealRequest(BaseModel):
    """업종지수(IJ_) 실시간 시세 등록/해제 요청.

    Use ``tr_type='3'`` to subscribe, ``'4'`` to unsubscribe.
    """
    header: IJ_RealRequestHeader = Field(
        IJ_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="IJ_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: IJ_RealRequestBody = Field(
        IJ_RealRequestBody(tr_cd="IJ_", tr_key=""),
        title="요청 바디 (Request body)",
        description="업종지수 실시간 등록에 필요한 업종코드 정보"
    )


class IJ_RealResponseBody(BaseModel):
    """IJ_RealResponseBody — sector index push payload (25 fields)."""

    time: str = Field(
        ...,
        title="시간 (Time)",
        description="Index calculation time in HHMMSS format.",
        examples=["090510", "153000"],
    )
    jisu: str = Field(
        ...,
        title="지수 (Index value)",
        description="Current sector index value. Decimal scale not declared in available source.",
        examples=["2638.79", "850.42"],
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
        title="전일비 (Prior-day change)",
        description=(
            "Magnitude of prior-day change in index value (always non-negative; "
            "direction encoded in ``sign``). Decimal scale not declared."
        ),
        examples=["0.84", "12.35"],
    )
    drate: str = Field(
        ...,
        title="등락율 (Change rate)",
        description="Prior-day change rate in percent (sign carried by ``sign``).",
        examples=["0.03", "1.25"],
    )
    cvolume: str = Field(
        ...,
        title="체결량 (Tick volume)",
        description="Volume of this tick (delta).",
        examples=["1234"],
    )
    volume: str = Field(
        ...,
        title="거래량 (Cumulative volume)",
        description="Cumulative session volume up to this tick.",
        examples=["12345678"],
    )
    value: str = Field(
        ...,
        title="거래대금 (Cumulative trade value)",
        description=(
            "Cumulative session trade value. Korean source labels the unit "
            "as '백만원' (million KRW) — preserved verbatim."
        ),
        examples=["123456"],
    )
    upjo: str = Field(
        ...,
        title="상한종목수 (Upper-limit stock count)",
        description="Count of stocks that hit the upper price limit today.",
        examples=["0", "3"],
    )
    highjo: str = Field(
        ...,
        title="상승종목수 (Advancing stock count)",
        description="Count of stocks up versus prior day's close.",
        examples=["432"],
    )
    unchgjo: str = Field(
        ...,
        title="보합종목수 (Unchanged stock count)",
        description="Count of stocks unchanged versus prior day's close.",
        examples=["120"],
    )
    lowjo: str = Field(
        ...,
        title="하락종목수 (Declining stock count)",
        description="Count of stocks down versus prior day's close.",
        examples=["278"],
    )
    downjo: str = Field(
        ...,
        title="하한종목수 (Lower-limit stock count)",
        description="Count of stocks that hit the lower price limit today.",
        examples=["0", "1"],
    )
    upjrate: str = Field(
        ...,
        title="상승종목비율 (Advancing stock ratio)",
        description="Advancing stocks as a percentage of the index constituent universe.",
        examples=["42.11"],
    )
    openjisu: str = Field(
        ...,
        title="시가지수 (Open index)",
        description="Session opening index value.",
        examples=["2630.00"],
    )
    opentime: str = Field(
        ...,
        title="시가시간 (Open time)",
        description="Time at which the open index was formed (HHMMSS).",
        examples=["090000"],
    )
    highjisu: str = Field(
        ...,
        title="고가지수 (High index)",
        description="Session high index value.",
        examples=["2645.50"],
    )
    hightime: str = Field(
        ...,
        title="고가시간 (High time)",
        description="Time at which the high index was formed (HHMMSS).",
        examples=["100515"],
    )
    lowjisu: str = Field(
        ...,
        title="저가지수 (Low index)",
        description="Session low index value.",
        examples=["2625.10"],
    )
    lowtime: str = Field(
        ...,
        title="저가시간 (Low time)",
        description="Time at which the low index was formed (HHMMSS).",
        examples=["093015"],
    )
    frgsvolume: str = Field(
        ...,
        title="외인순매수수량 (Foreign net buy volume)",
        description=(
            "Foreign net buy volume. Sign convention (positive = net buy, "
            "negative = net sell) is not declared in the available source — "
            "consume as returned by LS."
        ),
        examples=["12345", "-5678", "0"],
    )
    orgsvolume: str = Field(
        ...,
        title="기관순매수수량 (Institutional net buy volume)",
        description=(
            "Institutional net buy volume. Sign convention not declared in "
            "the available source — consume as returned by LS."
        ),
        examples=["6789", "-1234", "0"],
    )
    frgsvalue: str = Field(
        ...,
        title="외인순매수금액 (Foreign net buy value)",
        description=(
            "Foreign net buy value. Korean source labels the unit as '백만원' "
            "(million KRW) — preserved verbatim. Sign convention not declared."
        ),
        examples=["1234", "-567", "0"],
    )
    orgsvalue: str = Field(
        ...,
        title="기관순매수금액 (Institutional net buy value)",
        description=(
            "Institutional net buy value. Unit '백만원' (million KRW) per "
            "Korean source. Sign convention not declared."
        ),
        examples=["890", "-234", "0"],
    )
    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description="3-digit sector code matching the subscribed ``tr_key``.",
        examples=["001", "301"],
    )


class IJ_RealResponse(BaseModel):
    """업종지수(IJ_) 실시간 응답.

    Complete response model for IJ_ real-time sector index data.
    """
    header: Optional[IJ_RealResponseHeader]
    body: Optional[IJ_RealResponseBody]

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
