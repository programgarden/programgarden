"""Pydantic models for LS Securities OpenAPI t1466 (전일동시간대비거래급증 / volume-surge vs prior-day same-time ranking).

t1466 returns Korean stock issues whose intraday cumulative volume has surged
relative to the same time on the previous trading day, filtered by market
division (KOSPI / KOSDAQ), prior-day volume bucket, surge-rate bucket,
target-exclusion bitmasks, price / volume thresholds, and exchange division
(KRX / NXT / unified). Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``type1`` (전일거래량 buckets) and ``type2`` (거래급등율 buckets)
      verbatim from LS source: their inclusive / exclusive endpoint
      semantics are NOT declared in available source; use the bucket
      labels as opaque LS-defined values.
    - ``jc_num`` / ``jc_num2`` (target-exclusion bitmasks) bit-position
      semantics are NOT declared in available source; consume as returned
      by LS.
    - ``voldiff`` (거래급등율) reference-time alignment (today's
      same-clock cumulative vs. previous-day's same-clock cumulative,
      etc.) is NOT declared in available source; consume as returned by LS.
    - ``hhmm`` is the LS-server snapshot time for this response.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1466RequestHeader(BlockRequestHeader):
    """t1466 request header. Inherits the standard LS request header schema."""
    pass


class T1466ResponseHeader(BlockResponseHeader):
    """t1466 response header. Inherits the standard LS response header schema."""
    pass


class T1466InBlock(BaseModel):
    """t1466InBlock — input block for the volume-surge ranking screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    type1: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        ...,
        title="전일거래량 (Previous-day volume bucket)",
        description="Previous-day volume bucket per LS enumeration: '0' = ≥1주, '1' = ≥1만주, '2' = ≥5만주, '3' = ≥10만주, '4' = ≥20만주, '5' = ≥50만주, '6' = ≥100만주.",
        examples=["0", "1", "2", "3", "4", "5", "6"],
    )
    type2: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        ...,
        title="거래급등율 (Volume-surge rate bucket)",
        description="Volume-surge rate bucket per LS enumeration: '0' = all, '1' = ≤2000%, '2' = ≤1500%, '3' = ≤1000%, '4' = ≤500%, '5' = ≤100%, '6' = ≤50%.",
        examples=["0", "1", "2", "3", "4", "5", "6"],
    )
    jc_num: int = Field(
        default=0,
        title="대상제외 비트마스크 (Exclusion bitmask)",
        description="Target-exclusion bitmask. Bit-position semantics not declared in available source; consume as returned by LS. 0 means no exclusion.",
        examples=[0],
    )
    sprice: int = Field(
        default=0,
        title="시작가격 (Start price)",
        description="Inclusive lower bound of the price filter. 0 means no lower bound.",
        examples=[0, 1000],
    )
    eprice: int = Field(
        default=0,
        title="종료가격 (End price)",
        description="Inclusive upper bound of the price filter. 0 means no upper bound.",
        examples=[0, 100000],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume threshold)",
        description="Minimum cumulative volume filter in shares. 0 means no minimum.",
        examples=[0, 10000],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[0],
    )
    jc_num2: int = Field(
        default=0,
        title="대상제외2 비트마스크 (Exclusion bitmask 2)",
        description="Secondary target-exclusion bitmask. Bit-position semantics not declared in available source; consume as returned by LS. 0 means no exclusion.",
        examples=[0],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1466Request(BaseModel):
    """t1466 request envelope."""

    header: T1466RequestHeader = T1466RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1466",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1466InBlock"], T1466InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1466"
    )


class T1466OutBlock(BaseModel):
    """t1466OutBlock — continuation block (snapshot time + paging cursor)."""

    hhmm: str = Field(
        ...,
        title="현재시분 (Snapshot HHMM)",
        description="LS-server snapshot time for this response in HHMM (24-hour). Format and timezone semantics per LS server convention.",
        examples=["1430"],
    )
    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1466OutBlock1(BaseModel):
    """t1466OutBlock1 — per-issue volume-surge row."""

    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    hname: str = Field(
        ...,
        title="종목명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price. Decimal scale not declared in available source.",
        examples=[55300],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention: '1' = upper limit (상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower limit (하한), '5' = down (하락).",
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Sign convention not declared; pair with ``sign`` for direction.",
        examples=[1500, 0],
    )
    diff: float = Field(
        ...,
        title="등락율(%) (Change percent)",
        description="Percent change versus previous close.",
        examples=[2.78, -1.45, 0.0],
    )
    stdvolume: int = Field(
        ...,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's cumulative volume in shares (used as the denominator baseline for the surge metric).",
        examples=[12000000],
    )
    volume: int = Field(
        ...,
        title="당일거래량 (Today's volume)",
        description="Today's cumulative volume in shares as of the snapshot time.",
        examples=[18000000],
    )
    voldiff: float = Field(
        ...,
        title="거래급등율(%) (Volume-surge percent)",
        description="Volume-surge percentage versus the previous day. Reference-time alignment (cumulative-to-cumulative same-clock comparison vs. full-day comparison) not declared in available source.",
        examples=[150.0, 50.0, 0.0],
    )
    open: int = Field(
        ...,
        title="시가 (Open price)",
        description="Session opening price.",
        examples=[54000],
    )
    high: int = Field(
        ...,
        title="고가 (High price)",
        description="Session high price.",
        examples=[55800],
    )
    low: int = Field(
        ...,
        title="저가 (Low price)",
        description="Session low price.",
        examples=[53700],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description="Exchange-resolved short code echoed for the issue. Format and semantics not declared in available source.",
        examples=[""],
    )


class T1466Response(BaseModel):
    """t1466 response envelope."""

    header: Optional[T1466ResponseHeader]
    cont_block: Optional[T1466OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block (snapshot HHMM + paging cursor) for paged follow-up requests.",
    )
    block: List[T1466OutBlock1] = Field(
        default_factory=list,
        title="거래급증 종목 리스트 (Volume-surge ranking rows)",
        description="List of issues ranked by intraday volume-surge percentage versus the previous day.",
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
