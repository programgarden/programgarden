"""Pydantic models for LS Securities OpenAPI NVI (NXT VI trigger / release).

NVI is a Real-time WebSocket TR that pushes Volatility Interruption (VI)
trigger / release events for NXT (Next Trading System)-listed stocks.
The ``NVIRealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key``); the ``NVIRealResponseBody`` carries the
per-event push payload — VI type, reference prices (int), trigger price
(int), short code, time, exchange name and the exchange-prefixed short
code.

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
    - ``tr_key`` is padded to 10 characters: ``'N'`` + 6-digit code +
      3 trailing spaces.  Use ``'0000000000'`` (10 zeros) to subscribe
      to events for all NXT stocks.  ``examples`` mirror the example
      script (``src/finance/example/korea_stock/real_NVI.py``).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class NVIRealRequestHeader(BlockRealRequestHeader):
    """NVI real-time request header. Inherits the standard LS WS request header schema."""
    pass


class NVIRealResponseHeader(BlockRealResponseHeader):
    """NVI real-time response header. Inherits the standard LS WS response header schema."""
    pass


class NVIRealRequestBody(BaseModel):
    """NVIRealRequestBody — WebSocket subscription envelope for NXT VI push."""

    tr_cd: str = Field(
        default="NVI",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'NVI'.",
        examples=["NVI"],
    )
    tr_key: str = Field(
        ...,
        max_length=10,
        title="단축코드 + padding ('N' + 6-digit code + 3 spaces)",
        description=(
            "Exchange-prefixed key combining 'N' + 6-digit short code, "
            "right-padded with spaces to 10 characters. Use the LS-documented "
            "all-stocks special key '0000000000' (10 zeros) to receive VI "
            "events for all NXT stocks."
        ),
        examples=["N000880   ", "N115450   ", "0000000000"],
    )

    @field_validator("tr_key", mode="before")
    def ensure_10_char_padding(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 10:
            return s.ljust(10)
        return s

    model_config = ConfigDict(validate_assignment=True)


class NVIRealRequest(BaseModel):
    """(NXT) VI발동해제(NVI) 실시간 등록/해제 요청.

    Use ``tr_type='3'`` to subscribe, ``'4'`` to unsubscribe.  Set
    ``tr_key='0000000000'`` to receive VI events for all NXT stocks.
    """
    header: NVIRealRequestHeader = Field(
        NVIRealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="NVI 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: NVIRealRequestBody = Field(
        NVIRealRequestBody(tr_cd="NVI", tr_key=""),
        title="요청 바디 (Request body)",
        description="NXT VI발동해제 실시간 등록에 필요한 종목코드 정보"
    )


class NVIRealResponseBody(BaseModel):
    """NVIRealResponseBody — NXT VI trigger / release push payload (9 fields)."""

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
    svi_recprice: int = Field(
        ...,
        title="정적VI발동기준가격 (Static VI reference price)",
        description=(
            "Static VI reference (base) price. 0 indicates N/A — observed "
            "behaviour, preserved verbatim from the in-codebase Korean "
            "source. Decimal scale not declared in available source."
        ),
        examples=[0, 73500],
    )
    dvi_recprice: int = Field(
        ...,
        title="동적VI발동기준가격 (Dynamic VI reference price)",
        description=(
            "Dynamic VI reference (base) price. 0 indicates N/A — observed "
            "behaviour, preserved verbatim. Decimal scale not declared in "
            "available source."
        ),
        examples=[0, 73600],
    )
    vi_trgprice: int = Field(
        ...,
        title="VI발동가격 (VI trigger price)",
        description=(
            "Price that triggered the VI event. 0 indicates the event is a "
            "release rather than a trigger — observed behaviour, preserved "
            "verbatim. Decimal scale not declared in available source."
        ),
        examples=[0, 73450],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="NXT short symbol code (9 characters as returned by LS).",
        examples=["115450000", "000880000"],
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
        description="Exchange name string. Typically 'NXT' for this TR.",
        examples=["NXT"],
    )
    ex_shcode: str = Field(
        ...,
        title="거래소별단축코드 (Exchange-prefixed short symbol code)",
        description="Exchange-prefixed short symbol code (e.g. 'N115450').",
        examples=["N115450", "N000880"],
    )


class NVIRealResponse(BaseModel):
    """(NXT) VI발동해제(NVI) 실시간 응답.

    Complete response model for NVI real-time NXT VI event data.
    """
    header: Optional[NVIRealResponseHeader]
    body: Optional[NVIRealResponseBody]

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
