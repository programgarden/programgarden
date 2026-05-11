"""Pydantic models for LS Securities OpenAPI t1302 (주식분별주가조회 / Stock per-minute price query).

t1302 returns minute-bucket price aggregates for a Korean stock symbol —
30-second, 1/3/5/10/30/60-minute buckets. Each row carries the close,
previous-day direction code (LS-mapped enum), percent change, trade
strength, buy/sell trade volume + count, time-window quantities, and the
remaining ask/bid quantities. Pagination uses the ``cts_time`` cursor
echoed back in ``T1302OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping IS declared by LS for t1302
      (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락) and is documented inline.
    - Time ordering of ``OutBlock1`` rows, sign convention of
      ``change`` / ``revolume`` / ``rechecnt`` (signed) magnitudes,
      relationship between ``volume`` and ``cvolume``, currency unit of
      price fields, and the precise structure of the ``cts_time`` cursor
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``diff`` (LS scale 6.2) and ``chdegree`` (LS scale 8.2) are
      serialized as JSON strings by LS in example responses
      (e.g., ``"000.68"``, ``"163.65"``); Pydantic coerces to float.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1302RequestHeader(BlockRequestHeader):
    """t1302 request header. Inherits the standard LS request header schema."""
    pass


class T1302ResponseHeader(BlockResponseHeader):
    """t1302 response header. Inherits the standard LS response header schema."""
    pass


class T1302InBlock(BaseModel):
    """t1302InBlock — input block for the per-minute stock price query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6.",
        examples=["005930", "000660", "001200"],
    )
    gubun: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        ...,
        title="작업구분 (Bucket size)",
        description=(
            "Minute-bucket size selector. Length 1. "
            "'0' = 30 seconds (30초), "
            "'1' = 1 minute (1분), "
            "'2' = 3 minutes (3분), "
            "'3' = 5 minutes (5분), "
            "'4' = 10 minutes (10분), "
            "'5' = 30 minutes (30분), "
            "'6' = 60 minutes (60분). Required."
        ),
        examples=["0", "1", "5"],
    )
    time: str = Field(
        default="",
        title="시간 (Time continuation cursor)",
        description=(
            "Continuation cursor — empty (or a single space) on the first "
            "request, then echo back ``T1302OutBlock.cts_time`` from the "
            "previous response. Treat as opaque LS-defined token. Length 6."
        ),
        examples=["", "101700", "102700"],
    )
    cnt: int = Field(
        ...,
        title="건수 (Row count)",
        description=(
            "Number of rows to fetch per request. LS spec: 1 to 900 "
            "inclusive (Number, length 3). Required."
        ),
        examples=[1, 50, 900],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        ...,
        title="거래소구분코드 (Exchange code)",
        description=(
            "Exchange selector. Length 1. "
            "'K' = KRX, "
            "'N' = NXT (next-trade), "
            "'U' = unified (통합). "
            "Any other input is treated as KRX by LS. Required."
        ),
        examples=["K", "N", "U"],
    )


class T1302Request(BaseModel):
    """t1302 request envelope."""

    header: T1302RequestHeader = T1302RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1302",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1302InBlock"], T1302InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1302"
    )


class T1302OutBlock(BaseModel):
    """t1302OutBlock — continuation block carrying the ``cts_time`` cursor."""

    cts_time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Pass back as "
            "``T1302InBlock.time``. Empty when no further rows are available. "
            "Treat as opaque LS-defined token. Length 6."
        ),
        examples=["", "101700", "102700"],
    )


class T1302OutBlock1(BaseModel):
    """t1302OutBlock1 — one minute-bucket row.

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    chetime: str = Field(
        default="",
        title="시간 (Bucket time)",
        description=(
            "Bucket boundary time as reported by LS, observed structure "
            "``HHMMSS`` (6 digits). Whether the value marks the bucket start "
            "or end is not formally declared in available LS source — "
            "consume as returned by LS. Length 6."
        ),
        examples=["102700", "101700", "100700"],
    )
    close: int = Field(
        default=0,
        title="종가 (Close price)",
        description=(
            "Close price for the bucket. Decimal scale and currency unit "
            "not declared in available source — consume as returned by LS. "
            "Length 8."
        ),
        examples=[3685, 3690, 3675],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. Length 1. "
            "'1' = upper limit (상한), "
            "'2' = up (상승), "
            "'3' = unchanged (보합), "
            "'4' = lower limit (하한), "
            "'5' = down (하락). Enum mapping is declared by LS for t1302."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention is "
            "not declared in available LS source — consume as returned by "
            "LS. Length 8."
        ),
        examples=[0, 25, -15],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '000.68' or "
            "'-00.41'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -1.20],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description=(
            "LS-defined trade strength indicator in % (LS scale 8.2). "
            "Formula not declared in available source. LS may serialize "
            "this value as a string (e.g., '163.65'); Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 163.65, 98.74],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결수량 (Cumulative sell trade quantity)",
        description=(
            "Cumulative sell trade quantity in shares as of this row. "
            "Length 12."
        ),
        examples=[0, 119531, 250000],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결수량 (Cumulative buy trade quantity)",
        description=(
            "Cumulative buy trade quantity in shares as of this row. "
            "Length 12."
        ),
        examples=[0, 195607, 300000],
    )
    revolume: int = Field(
        default=0,
        title="순매수체결량 (Net buy trade quantity)",
        description=(
            "Net buy trade quantity in shares. Sign convention not declared "
            "in available LS source; consume as returned by LS. Length 12."
        ),
        examples=[0, 76076, -50000],
    )
    mdchecnt: int = Field(
        default=0,
        title="매도체결건수 (Cumulative sell trade count)",
        description="Cumulative sell trade count as of this row. Length 8.",
        examples=[0, 256, 1000],
    )
    mschecnt: int = Field(
        default=0,
        title="매수체결건수 (Cumulative buy trade count)",
        description="Cumulative buy trade count as of this row. Length 8.",
        examples=[0, 238, 1000],
    )
    rechecnt: int = Field(
        default=0,
        title="순체결건수 (Net trade count)",
        description=(
            "Net trade count (sell count minus buy count, or vice versa — "
            "sign convention not declared in available LS source). Length 8."
        ),
        examples=[0, -18, 42],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Cumulative volume)",
        description=(
            "Cumulative traded volume in shares as of this row. "
            "Relationship between ``volume`` and ``cvolume`` not declared "
            "in available LS source. Length 12."
        ),
        examples=[0, 321201, 1000000],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description=(
            "Open price for the bucket. Decimal scale and currency unit "
            "not declared in available source. Length 8."
        ),
        examples=[3685, 3690, 3680],
    )
    high: int = Field(
        default=0,
        title="고가 (High price)",
        description=(
            "High price for the bucket. Decimal scale and currency unit "
            "not declared in available source. Length 8."
        ),
        examples=[3685, 3700, 3680],
    )
    low: int = Field(
        default=0,
        title="저가 (Low price)",
        description=(
            "Low price for the bucket. Decimal scale and currency unit "
            "not declared in available source. Length 8."
        ),
        examples=[3685, 3680, 3670],
    )
    cvolume: int = Field(
        default=0,
        title="체결량 (Trade quantity)",
        description=(
            "Trade quantity for this bucket in shares. Relationship between "
            "``cvolume`` and ``volume`` (per-bucket vs cumulative) not "
            "declared in available LS source. Length 12."
        ),
        examples=[0, 500, 1002],
    )
    mdchecnttm: int = Field(
        default=0,
        title="매도체결건수(시간) (Sell trade count in window)",
        description=(
            "Sell trade count within this time bucket. Length 8."
        ),
        examples=[0, 25, 100],
    )
    mschecnttm: int = Field(
        default=0,
        title="매수체결건수(시간) (Buy trade count in window)",
        description=(
            "Buy trade count within this time bucket. Length 8."
        ),
        examples=[0, 30, 100],
    )
    totofferrem: int = Field(
        default=0,
        title="매도잔량 (Total ask remaining quantity)",
        description=(
            "Total remaining ask (sell) quantity in shares at the bucket "
            "boundary. Length 12."
        ),
        examples=[0, 18352, 50000],
    )
    totbidrem: int = Field(
        default=0,
        title="매수잔량 (Total bid remaining quantity)",
        description=(
            "Total remaining bid (buy) quantity in shares at the bucket "
            "boundary. Length 12."
        ),
        examples=[0, 35195, 50000],
    )
    mdvolumetm: int = Field(
        default=0,
        title="시간별매도체결량 (Sell trade quantity in window)",
        description=(
            "Sell trade quantity within this time bucket in shares. "
            "Length 12."
        ),
        examples=[0, 5000, 25000],
    )
    msvolumetm: int = Field(
        default=0,
        title="시간별매수체결량 (Buy trade quantity in window)",
        description=(
            "Buy trade quantity within this time bucket in shares. "
            "Length 12."
        ),
        examples=[0, 6000, 25000],
    )


class T1302Response(BaseModel):
    """t1302 response envelope."""

    header: Optional[T1302ResponseHeader]
    cont_block: Optional[T1302OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1302OutBlock1] = Field(
        default_factory=list,
        title="분별 시세 리스트 (Per-minute bucket rows)",
        description=(
            "List of minute-bucket rows. Time ordering not declared in "
            "available source."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지 (Error message)",
        description="Error message when the request failed; ``None`` on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
