"""Pydantic models for LS Securities OpenAPI t1308 (주식시간대별체결조회챠트 /
Stock time-bucket trade chart query).

t1308 returns time-bucket trade rows for a Korean stock symbol — trade
time, current price, previous-day direction code (LS-mapped enum 1=상한 /
2=상승 / 3=보합 / 4=하한 / 5=하락 per xingAPI reference), magnitude of
change, percent change, per-row trade quantity, two trade-strength
indicators (volume-based ``chdegvol`` and count-based ``chdegcnt``),
volume, sell/buy trade volume and count, and open/high/low prices.
Unlike t1302 or t1310, this TR has no continuation cursor — the full
set is returned in one response.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas``
and ``feedback_tr_field_metadata``):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` enum mapping IS declared (1=상한 / 2=상승 / 3=보합 /
      4=하한 / 5=하락) per the LS xingAPI reference and is published
      verbatim in the field description.
    - ``exchgubun`` enum (K=KRX / N=NXT / U=통합) is declared by LS and
      published verbatim.
    - Sign convention of ``change`` (signed magnitude), the exact
      structure of ``chetime`` (observed in example response as
      ``'102700'`` / ``'090030'`` — 6 digits HHMMSS-like), the
      cumulative-vs-per-bucket semantics of ``volume`` / ``mdvolume`` /
      ``msvolume`` / ``mdchecnt`` / ``mschecnt`` relative to
      ``cvolume``, the bucket scope of OHLC fields (per row bucket vs
      daily aggregate), row time ordering of ``OutBlock1``, the
      currency unit and decimal scale of price fields, and the
      structure of ``ex_shcode`` are NOT declared in the LS source
      available to this codebase; consume as returned by LS.
    - ``diff`` (LS scale 6.2), ``chdegvol`` (LS scale 8.2), and
      ``chdegcnt`` (LS scale 8.2) are serialized as JSON strings by LS
      in example responses (e.g., ``"0.69"``, ``"163.65"``,
      ``"92.97"``); Pydantic coerces to float.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1308RequestHeader(BlockRequestHeader):
    """t1308 request header. Inherits the standard LS request header schema."""
    pass


class T1308ResponseHeader(BlockResponseHeader):
    """t1308 response header. Inherits the standard LS response header schema."""
    pass


class T1308InBlock(BaseModel):
    """t1308InBlock — input block for the time-bucket trade chart query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code. Length 6. Required.",
        examples=["005930", "000660", "001200"],
    )
    starttime: str = Field(
        default="",
        title="시작시간 (Start time)",
        description=(
            "Window start time as HHMM (length 4). LS spec note: "
            "'장시작시간 이후' (at or after session-open time). Empty "
            "string is accepted on first request per LS example. "
            "Required by LS spec."
        ),
        examples=["", "0900", "1000"],
    )
    endtime: str = Field(
        default="",
        title="종료시간 (End time)",
        description=(
            "Window end time as HHMM (length 4). LS spec note: "
            "'장종료시간 이전' (at or before session-close time). Empty "
            "string is accepted on first request per LS example. "
            "Required by LS spec."
        ),
        examples=["", "1500", "1530"],
    )
    bun_term: str = Field(
        default="",
        title="분간격 (Bucket size in minutes)",
        description=(
            "Bucket size in minutes as a 2-character string (LS length "
            "2). Empty string is accepted on first request per LS "
            "example. Required by LS spec."
        ),
        examples=["", "01", "05", "30"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange code)",
        description=(
            "Exchange selector. Length 1. "
            "'K' = KRX, "
            "'N' = NXT (next-trade), "
            "'U' = unified (통합). "
            "Pydantic validates strictly — only these three are accepted; empty string and other values are rejected. Required."
        ),
        examples=["K", "N", "U"],
    )


class T1308Request(BaseModel):
    """t1308 request envelope."""

    header: T1308RequestHeader = T1308RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1308",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1308InBlock"], T1308InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1308"
    )


class T1308OutBlock(BaseModel):
    """t1308OutBlock — single response metadata block.

    Carries the exchange-prefixed short code returned by LS. This block
    is NOT a continuation cursor — t1308 has no LS-declared pagination
    mechanism. Single-shot TR.
    """

    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-prefixed short code)",
        description=(
            "Exchange-prefixed short code as returned by LS. Length 10. "
            "Token structure not declared in available LS source — "
            "consume as returned by LS."
        ),
        examples=[""],
    )


class T1308OutBlock1(BaseModel):
    """t1308OutBlock1 — one time-bucket trade row.

    Time ordering of rows is NOT declared in the source available to
    this codebase; consume as returned by LS.
    """

    chetime: str = Field(
        default="",
        title="시간 (Bucket time)",
        description=(
            "Bucket time as returned by LS. Observed values in LS "
            "example responses are 6-digit numeric strings such as "
            "``'102700'`` and ``'090030'`` (LS spec declares length "
            "8). Exact format (HHMMSS vs HHMM00 vs other) is not "
            "formally declared in available LS source — consume as "
            "returned by LS."
        ),
        examples=["102700", "090030"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Current price for the bucket. Decimal scale and currency "
            "unit not declared in available LS source. Length 8."
        ),
        examples=[3685, 3660],
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
            "'5' = down (하락). Enum mapping is declared by LS for "
            "t1308 (per xingAPI reference)."
        ),
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description=(
            "Magnitude of change versus previous close. Sign "
            "convention is not declared in available LS source — "
            "consume as returned by LS. Length 8."
        ),
        examples=[0, 25],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0.69' or "
            "'0.01'); Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.69, 0.01],
    )
    cvolume: int = Field(
        default=0,
        title="체결수량 (Per-row trade quantity)",
        description=(
            "Per-row trade quantity in shares. Length 8. "
            "Cumulative-vs-per-bucket relationship to ``volume`` / "
            "``mdvolume`` / ``msvolume`` is not declared in available "
            "LS source."
        ),
        examples=[0, 19856],
    )
    chdegvol: float = Field(
        default=0.0,
        title="체결강도(거래량) (Trade strength by volume)",
        description=(
            "LS-defined volume-based trade strength indicator in % "
            "(LS scale 8.2). Formula not declared in available LS "
            "source. LS may serialize this value as a string "
            "(e.g., '163.65' or '6.97'); Pydantic auto-coerces to "
            "float."
        ),
        examples=[0.0, 163.65, 6.97],
    )
    chdegcnt: float = Field(
        default=0.0,
        title="체결강도(건수) (Trade strength by count)",
        description=(
            "LS-defined count-based trade strength indicator in % "
            "(LS scale 8.2). Formula not declared in available LS "
            "source. LS may serialize this value as a string "
            "(e.g., '92.97' or '14.29'); Pydantic auto-coerces to "
            "float."
        ),
        examples=[0.0, 92.97, 14.29],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description=(
            "Volume as labeled by LS. Length 12. Cumulative-vs-"
            "per-bucket semantics relative to ``cvolume`` is not "
            "declared in available LS source."
        ),
        examples=[321201, 19857],
    )
    mdvolume: int = Field(
        default=0,
        title="매도체결수량 (Sell trade quantity)",
        description=(
            "Sell trade quantity in shares. Length 12. Cumulative-vs-"
            "per-bucket semantics not declared in available LS source."
        ),
        examples=[119531, 12895],
    )
    mdchecnt: int = Field(
        default=0,
        title="매도체결건수 (Sell trade count)",
        description=(
            "Sell trade count. Length 8. Cumulative-vs-per-bucket "
            "semantics not declared in available LS source."
        ),
        examples=[256, 14],
    )
    msvolume: int = Field(
        default=0,
        title="매수체결수량 (Buy trade quantity)",
        description=(
            "Buy trade quantity in shares. Length 12. Cumulative-vs-"
            "per-bucket semantics not declared in available LS source."
        ),
        examples=[195607, 899],
    )
    mschecnt: int = Field(
        default=0,
        title="매수체결건수 (Buy trade count)",
        description=(
            "Buy trade count. Length 8. Cumulative-vs-per-bucket "
            "semantics not declared in available LS source."
        ),
        examples=[238, 2],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description=(
            "Open price. Bucket scope (per row time bucket vs daily "
            "aggregate) not declared in available LS source. Decimal "
            "scale and currency unit not declared. Length 8."
        ),
        examples=[3685, 3660],
    )
    high: int = Field(
        default=0,
        title="고가 (High price)",
        description=(
            "High price. Bucket scope (per row time bucket vs daily "
            "aggregate) not declared in available LS source. Decimal "
            "scale and currency unit not declared. Length 8."
        ),
        examples=[3685, 3660],
    )
    low: int = Field(
        default=0,
        title="저가 (Low price)",
        description=(
            "Low price. Bucket scope (per row time bucket vs daily "
            "aggregate) not declared in available LS source. Decimal "
            "scale and currency unit not declared. Length 8."
        ),
        examples=[3685, 3660],
    )


class T1308Response(BaseModel):
    """t1308 response envelope."""

    header: Optional[T1308ResponseHeader]
    out_block: Optional[T1308OutBlock] = Field(
        None,
        title="응답 메타데이터 블록 (Response metadata block)",
        description=(
            "Single metadata block carrying the exchange-prefixed "
            "short code. NOT a continuation cursor — t1308 has no "
            "LS-declared pagination."
        ),
    )
    block: List[T1308OutBlock1] = Field(
        default_factory=list,
        title="시간대별 봉 리스트 (Per-time-bucket rows)",
        description=(
            "List of time-bucket trade rows. Row time ordering not "
            "declared in available LS source — consume as returned by "
            "LS."
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
