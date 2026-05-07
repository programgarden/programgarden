"""Pydantic models for LS Securities OpenAPI t1475 (체결강도추이 / trade strength history).

t1475 returns a per-time history of trade strength (체결강도) along with
moving averages over 5 / 20 / 60 days, paired with current price, sign,
change, and volume. ``vptype`` toggles between intraday and daily granularity;
``gubun`` between general and chart-mode queries.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Trade strength (VP) formula and value range are NOT declared in the
      available source; consume as returned by LS.
    - Moving-average windows (5/20/60) are LS-source-declared; computation
      method (simple vs. weighted vs. exponential) is NOT.
    - ``date`` / ``time`` continuation tokens are opaque LS-defined.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1475RequestHeader(BlockRequestHeader):
    """t1475 request header. Inherits the standard LS request header schema."""
    pass


class T1475ResponseHeader(BlockResponseHeader):
    """t1475 response header. Inherits the standard LS response header schema."""
    pass


class T1475InBlock(BaseModel):
    """t1475InBlock — input block for the trade strength history query."""

    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    vptype: Literal["0", "1"] = Field(
        default="0",
        title="상승하락 (Granularity)",
        description="Time-axis granularity. '0' = intraday by time (시간별), '1' = daily (일별).",
        examples=["0", "1"],
    )
    datacnt: int = Field(
        default=0,
        title="데이터개수 (Row count)",
        description="Number of rows to request. Per LS source, a value of 0 (or space-equivalent) returns up to 20 rows.",
        examples=[0, 20],
    )
    date: int = Field(
        default=0,
        title="기준일자 (Reference date / continuation cursor)",
        description="Reference date for the query, used as a continuation cursor for paged follow-ups (echoes ``OutBlock.date``).",
        examples=[0, 20260228],
    )
    time: int = Field(
        default=0,
        title="기준시간 (Reference time / continuation cursor)",
        description="Reference time for the query, used as a continuation cursor (echoes ``OutBlock.time``).",
        examples=[0, 153000],
    )
    rankcnt: int = Field(
        default=0,
        title="랭크카운터 (Rank counter, unused)",
        description="LS-reserved rank counter — not used per available source. Pass 0.",
        examples=[0],
    )
    gubun: Literal["0", "1"] = Field(
        default="0",
        title="조회구분 (Query mode)",
        description="Query mode. '0' = general query (일반조회), '1' = chart query (차트조회).",
        examples=["0", "1"],
    )


class T1475Request(BaseModel):
    """t1475 request envelope."""

    header: T1475RequestHeader = T1475RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1475",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1475InBlock"], T1475InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1475"
    )


class T1475OutBlock(BaseModel):
    """t1475OutBlock — continuation block (paging cursors)."""

    date: int = Field(
        ...,
        title="기준일자 (Continuation date)",
        description="Continuation date cursor for the next paged request. 0 when no further rows are available.",
        examples=[0, 20260228],
    )
    time: int = Field(
        ...,
        title="기준시간 (Continuation time)",
        description="Continuation time cursor for the next paged request.",
        examples=[0, 153000],
    )
    rankcnt: int = Field(
        ...,
        title="랭크카운터 (Rank counter)",
        description="LS-defined rank counter. Semantics not declared in available source.",
        examples=[0],
    )


class T1475OutBlock1(BaseModel):
    """t1475OutBlock1 — per-time / per-day trade strength row.

    VP (체결강도) formula and value range are NOT declared in the source
    available to this codebase; consume as returned by LS.
    """

    datetime: str = Field(
        ...,
        title="일자 (Date / time stamp)",
        description="Row timestamp. For ``vptype='1'`` (daily) this is a date; for ``vptype='0'`` (intraday) this is a time. Format not declared in available source.",
        examples=["20260228", "093000"],
    )
    price: int = Field(
        ...,
        title="현재가 (Price)",
        description="Price for the row. Decimal scale not declared in available source.",
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5').",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close.",
        examples=[800, 0],
    )
    diff: float = Field(
        ...,
        title="등락율(%) (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.02, 0.0, -0.5],
    )
    volume: int = Field(
        ...,
        title="거래량 (Volume)",
        description="Volume for the row in shares.",
        examples=[15000000],
    )
    todayvp: float = Field(
        ...,
        title="당일VP (Today VP)",
        description="Today's trade strength (체결강도). Formula and range not declared in available source.",
        examples=[105.32],
    )
    ma5vp: float = Field(
        ...,
        title="5일MAVP (5-day MA of VP)",
        description="5-day moving average of trade strength. Computation method not declared in available source.",
        examples=[102.5],
    )
    ma20vp: float = Field(
        ...,
        title="20일MAVP (20-day MA of VP)",
        description="20-day moving average of trade strength. Computation method not declared in available source.",
        examples=[101.0],
    )
    ma60vp: float = Field(
        ...,
        title="60일MAVP (60-day MA of VP)",
        description="60-day moving average of trade strength. Computation method not declared in available source.",
        examples=[99.7],
    )


class T1475Response(BaseModel):
    """t1475 response envelope."""

    header: Optional[T1475ResponseHeader]
    cont_block: Optional[T1475OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1475OutBlock1] = Field(
        default_factory=list,
        title="체결강도 리스트 (Trade strength rows)",
        description="List of per-time / per-day trade strength rows.",
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
