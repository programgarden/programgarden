"""Pydantic models for LS Securities OpenAPI DVI (KRX after-hours single-price VI).

DVI is a Real-time WebSocket TR that pushes Volatility Interruption (VI)
trigger / release events for KRX-listed stocks during after-hours
single-price trading.  The ``DVIRealRequestBody`` carries the WebSocket
subscription envelope (``tr_cd`` + ``tr_key`` — short symbol code, or
``'000000'`` for all stocks); the ``DVIRealResponseBody`` carries the
per-event push payload (VI type, reference prices, trigger price,
short code, time, exchange name).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - ``vi_gubun`` enum (0=release, 1=static trigger, 2=dynamic trigger,
      3=static&dynamic) is preserved verbatim from the in-codebase Korean
      source.
    - Reference-price "0 means N/A" / trigger-price "0 means release"
      semantics mirror existing in-codebase observations and are
      preserved verbatim — observed behaviour, not inferred.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.
    - ``examples`` for ``tr_key`` mirror the example script
      (``src/finance/example/korea_stock/real_DVI.py`` uses ``"*"``) and
      the LS-documented all-stocks special key ``"000000"``.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class DVIRealRequestHeader(BlockRealRequestHeader):
    """DVI real-time request header. Inherits the standard LS WS request header schema."""
    pass


class DVIRealResponseHeader(BlockRealResponseHeader):
    """DVI real-time response header. Inherits the standard LS WS response header schema."""
    pass


class DVIRealRequestBody(BaseModel):
    """DVIRealRequestBody — WebSocket subscription envelope for KRX VI push."""

    tr_cd: str = Field(
        default="DVI",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'DVI'.",
        examples=["DVI"],
    )
    tr_key: str = Field(
        ...,
        max_length=6,
        title="단축코드 (Short symbol code)",
        description=(
            "6-digit short symbol code for the target stock. Use the "
            "LS-documented special key '000000' to receive VI events for "
            "all KRX-listed stocks."
        ),
        examples=["086520", "000000"],
    )


class DVIRealRequest(BaseModel):
    """KRX 시간외단일가 VI발동해제(DVI) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for KRX VI (Volatility Interruption) events.
        Use tr_type='3' to subscribe, '4' to unsubscribe.
        Set tr_key='000000' to receive VI events for all stocks.

    KO:
        KRX VI(변동성완화장치) 발동/해제 이벤트를 수신하기 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
        tr_key에 '000000'을 지정하면 전 종목 VI 이벤트를 수신합니다.
    """
    header: DVIRealRequestHeader = Field(
        DVIRealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="DVI 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: DVIRealRequestBody = Field(
        DVIRealRequestBody(tr_cd="DVI", tr_key=""),
        title="요청 바디 (Request body)",
        description="VI발동해제 실시간 등록에 필요한 종목코드 정보"
    )


class DVIRealResponseBody(BaseModel):
    """DVIRealResponseBody — KRX VI trigger / release push payload (8 fields)."""

    vi_gubun: str = Field(
        ...,
        title="구분 (VI type)",
        description=(
            "VI type code. LS-source-declared values: '0'=release, "
            "'1'=static trigger, '2'=dynamic trigger, '3'=static&dynamic. "
            "Other LS-defined codes may appear — consume as returned by LS."
        ),
        examples=["0", "1", "2", "3"],
    )
    svi_recprice: str = Field(
        ...,
        title="정적VI발동기준가격 (Static VI reference price)",
        description=(
            "Static VI reference (base) price. '0' indicates N/A — "
            "observed behaviour, preserved verbatim from the in-codebase "
            "Korean source. Decimal scale not declared in available source."
        ),
        examples=["0", "73500"],
    )
    dvi_recprice: str = Field(
        ...,
        title="동적VI발동기준가격 (Dynamic VI reference price)",
        description=(
            "Dynamic VI reference (base) price. '0' indicates N/A — "
            "observed behaviour, preserved verbatim. Decimal scale not "
            "declared in available source."
        ),
        examples=["0", "73600"],
    )
    vi_trgprice: str = Field(
        ...,
        title="VI발동가격 (VI trigger price)",
        description=(
            "Price that triggered the VI event. '0' indicates the event "
            "is a release rather than a trigger — observed behaviour, "
            "preserved verbatim. Decimal scale not declared in available "
            "source."
        ),
        examples=["0", "73450"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="Short symbol code (6 digits) of the stock for which VI was triggered or released.",
        examples=["086520", "005930"],
    )
    ref_shcode: str = Field(
        ...,
        title="참조코드 (Reference code)",
        description="Reference code. Reserved by LS — currently unused; consume as returned.",
        examples=[""],
    )
    time: str = Field(
        ...,
        title="시간 (Time)",
        description="VI trigger / release time in HHMMSS format.",
        examples=["092415", "153000"],
    )
    exchname: str = Field(
        ...,
        title="거래소명 (Exchange name)",
        description="Exchange name string. Typically 'KRX' for this TR.",
        examples=["KRX"],
    )


class DVIRealResponse(BaseModel):
    """KRX 시간외단일가 VI발동해제(DVI) 실시간 응답.

    Complete response model for DVI real-time VI event data.
    """
    header: Optional[DVIRealResponseHeader]
    body: Optional[DVIRealResponseBody]

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
