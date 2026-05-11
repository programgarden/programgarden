"""Pydantic models for LS Securities OpenAPI t1310 (주식당일전일분틱조회 / Stock today/yesterday minute or tick query).

t1310 returns today's or previous day's minute or tick rows for a Korean
stock symbol — current price, previous-day direction code (LS-mapped
**not** declared for t1310 — see policy below), magnitude of change and
percent change, trade quantity, trade strength, cumulative volume,
cumulative + per-row sell/buy trade volume and count, net trade volume
and count, and the exchange name. Pagination uses the ``cts_time``
cursor echoed back in ``T1310OutBlock``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping is **NOT** declared by LS for t1310 (unlike
      t1302 where 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락 is published).
      ``sign`` description carries a "not declared" disclaimer; consume
      as returned by LS without glyph translation.
    - Sign convention of ``change`` / ``revolume`` / ``rechecnt``
      (signed) magnitudes, time-window semantics of ``chetime`` (bucket
      start vs. bucket end, observed structure ``HHMMSS`` or ``HHMMSS``
      plus embedded null bytes such as ``"100800\\u0000000"``), relation-
      ship between ``volume`` (cumulative) and ``cvolume`` (per row),
      time ordering of ``OutBlock1`` rows, currency unit and decimal
      scale of price fields, and the precise structure of the
      ``cts_time`` cursor (observed to carry embedded null bytes) are
      NOT declared in the source available to this codebase; consume as
      returned by LS.
    - ``diff`` (LS scale 6.2) and ``chdegree`` (LS scale 8.2) are
      serialized as JSON strings by LS in example responses
      (e.g., ``"000.68"``, ``"00163.65"``); Pydantic coerces to float.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1310RequestHeader(BlockRequestHeader):
    """t1310 request header. Inherits the standard LS request header schema."""
    pass


class T1310ResponseHeader(BlockResponseHeader):
    """t1310 response header. Inherits the standard LS response header schema."""
    pass


class T1310InBlock(BaseModel):
    """t1310InBlock — input block for the today/yesterday minute-or-tick query."""

    daygb: Literal["0", "1"] = Field(
        ...,
        title="당일전일구분 (Today/previous-day selector)",
        description=(
            "Day selector. Length 1. "
            "'0' = today (당일), "
            "'1' = previous day (전일). Required."
        ),
        examples=["0", "1"],
    )
    timegb: Literal["0", "1"] = Field(
        ...,
        title="분틱구분 (Minute/tick selector)",
        description=(
            "Bucket type. Length 1. "
            "'0' = minute (분), "
            "'1' = tick (틱). Required."
        ),
        examples=["0", "1"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6. Required.",
        examples=["005930", "000660", "001200"],
    )
    endtime: str = Field(
        default="",
        title="종료시간 (End time)",
        description=(
            "First-request end time as HHMM (length 4). Only rows whose "
            "``T1310OutBlock1.chetime <= endtime`` are returned. Empty "
            "string is accepted on the first request (per LS example "
            "request). Required by LS spec."
        ),
        examples=["", "1500", "0930"],
    )
    cts_time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Continuation cursor — empty string on the first request "
            "(per LS example request; LS spec text says 'Space'). On "
            "subsequent requests, echo back "
            "``T1310OutBlock.cts_time`` from the previous response. "
            "Treat as opaque LS-defined token — observed values may "
            "contain embedded null bytes. Length 10."
        ),
        examples=["", "100700", "100700\x00000"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange code)",
        description=(
            "Exchange selector. Length 1. "
            "'K' = KRX, "
            "'N' = NXT (next-trade), "
            "'U' = unified (통합). "
            "Any other input is treated as KRX by LS."
        ),
        examples=["K", "N", "U"],
    )


class T1310Request(BaseModel):
    """t1310 request envelope."""

    header: T1310RequestHeader = T1310RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1310",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1310InBlock"], T1310InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1310"
    )


class T1310OutBlock(BaseModel):
    """t1310OutBlock — continuation block carrying the ``cts_time`` cursor."""

    cts_time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Continuation cursor for the next paged request. Pass back "
            "as ``T1310InBlock.cts_time``. Empty when no further rows "
            "are available. Treat as opaque LS-defined token — observed "
            "values may contain embedded null bytes. Length 10."
        ),
        examples=["", "100700", "100700\x00000"],
    )


class T1310OutBlock1(BaseModel):
    """t1310OutBlock1 — one minute-or-tick row.

    Time ordering of rows is NOT declared in the source available to
    this codebase; consume as returned by LS.
    """

    chetime: str = Field(
        default="",
        title="시간 (Trade time)",
        description=(
            "Trade time as reported by LS. Observed structure varies — "
            "values such as ``\"102700\"`` (6 chars) and "
            "``\"100800\\u0000000\"`` (HHMMSS plus embedded null bytes, "
            "10 chars total) both appear in the LS official example "
            "response. Whether the value marks the bucket start or end "
            "is not declared in available LS source. Consume as "
            "returned by LS. Length 10."
        ),
        examples=["102700", "100800\x00000"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price for this row. Decimal scale and currency unit "
            "are not declared in available LS source — consume as "
            "returned by LS. Length 8."
        ),
        examples=[3685, 3690, 3675],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Previous-day direction code. Length 1. **Enum mapping is "
            "NOT declared by LS for t1310** (unlike t1302). Consume as "
            "returned by LS without glyph translation."
        ),
        examples=["2", "5", "3"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign convention "
            "is not declared in available LS source — consume as "
            "returned by LS. Length 8."
        ),
        examples=[0, 25, -15],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string "
            "(e.g., ``\"000.68\"``); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -1.20],
    )
    cvolume: int = Field(
        default=0,
        title="체결수량 (Trade quantity)",
        description=(
            "Trade quantity for this row in shares. Relationship to "
            "``volume`` (per-row vs. cumulative) is not declared in "
            "available LS source. Length 12."
        ),
        examples=[5, 69, 1002],
    )
    chdegree: float = Field(
        default=0.0,
        title="체결강도 (Trade strength)",
        description=(
            "LS-defined trade strength indicator in % (LS scale 8.2). "
            "Formula is not declared in available LS source. LS may "
            "serialize this value as a string (e.g., ``\"00163.65\"``); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.0, 163.65, 156.00],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Cumulative volume)",
        description=(
            "Cumulative traded volume in shares as of this row. "
            "Relationship to ``cvolume`` is not declared in available "
            "LS source. Length 12."
        ),
        examples=[321201, 300647, 1000000],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결수량 (Cumulative sell trade quantity)",
        description=(
            "Cumulative sell trade quantity in shares as of this row. "
            "Length 12."
        ),
        examples=[119531, 115072, 250000],
    )
    mdchecnt: int = Field(
        default=0,
        title="매도체결건수 (Cumulative sell trade count)",
        description="Cumulative sell trade count as of this row. Length 8.",
        examples=[256, 237, 1000],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결수량 (Cumulative buy trade quantity)",
        description=(
            "Cumulative buy trade quantity in shares as of this row. "
            "Length 12."
        ),
        examples=[195607, 179512, 300000],
    )
    mschecnt: int = Field(
        default=0,
        title="매수체결건수 (Cumulative buy trade count)",
        description="Cumulative buy trade count as of this row. Length 8.",
        examples=[238, 217, 1000],
    )
    revolume: int = Field(
        default=0,
        title="순체결량 (Net trade quantity)",
        description=(
            "Net trade quantity. Sign convention is not declared in "
            "available LS source — consume as returned by LS. Length 12."
        ),
        examples=[76076, 64440, -50000],
    )
    rechecnt: int = Field(
        default=0,
        title="순체결건수 (Net trade count)",
        description=(
            "Net trade count. Sign convention is not declared in "
            "available LS source — consume as returned by LS. Length 8."
        ),
        examples=[-18, -20, 42],
    )
    exchname: str = Field(
        default="",
        title="거래소명 (Exchange name)",
        description="Exchange name as labeled by LS. Length 3.",
        examples=["KRX", "NXT", ""],
    )


class T1310Response(BaseModel):
    """t1310 response envelope."""

    header: Optional[T1310ResponseHeader]
    cont_block: Optional[T1310OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1310OutBlock1] = Field(
        default_factory=list,
        title="당일/전일 분틱 리스트 (Per-minute or per-tick rows)",
        description=(
            "List of minute-or-tick rows. Time ordering is not declared "
            "in available LS source."
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
