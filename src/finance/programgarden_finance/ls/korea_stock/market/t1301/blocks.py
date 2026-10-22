"""Pydantic models for LS Securities OpenAPI t1301 (주식시간대별체결조회 / per-trade tape, KRX-only).

t1301 returns intraday per-trade rows for a Korean stock symbol on KRX, with
trade time, last price, sign, change, trade strength, side-resolved volumes
and counts, and net-trade aggregates. Pagination is via ``cts_time``. Use
t8454 for the unified KRX/NXT version.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``cts_time`` is an opaque LS-defined continuation token; pass back
      verbatim on follow-up requests.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1301RequestHeader(BlockRequestHeader):
    """t1301 request header. Inherits the standard LS request header schema."""
    pass


class T1301ResponseHeader(BlockResponseHeader):
    """t1301 response header. Inherits the standard LS response header schema."""
    pass


class T1301InBlock(BaseModel):
    """t1301InBlock — input block for the per-trade tape query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    cvolume: int = Field(
        default=0,
        title="특이거래량 (Notable trade quantity threshold)",
        description="Filter threshold — rows with trade quantity greater than this value are flagged. 0 means no filter.",
        examples=[0, 1000],
    )
    starttime: str = Field(
        default="",
        title="시작시간 (Start time)",
        description="Start of the time window in 'HHMM' or 'HHMMSS' format. Empty for session start.",
        examples=["", "0900"],
    )
    endtime: str = Field(
        default="",
        title="종료시간 (End time)",
        description="End of the time window in 'HHMM' or 'HHMMSS' format. Empty for session end.",
        examples=["", "1530"],
    )
    cts_time: str = Field(
        default="",
        title="시간CTS (Continuation cursor)",
        description="Continuation cursor for paged queries. Empty on first request; pass back ``cts_time`` from the previous response. Treat as opaque LS-defined token.",
        examples=[""],
    )


class T1301Request(BaseModel):
    """t1301 request envelope."""

    header: T1301RequestHeader = T1301RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1301",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1301InBlock"], T1301InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1301"
    )


class T1301OutBlock(BaseModel):
    """t1301OutBlock — continuation block (echoes ``cts_time``)."""

    cts_time: str = Field(
        ...,
        title="시간CTS (Continuation cursor)",
        description="Continuation cursor for the next paged request. Empty when no further rows are available.",
        examples=[""],
    )


class T1301OutBlock1(BaseModel):
    """t1301OutBlock1 — per-trade row.

    Time ordering of rows is NOT declared in the source available to this
    codebase; consume as returned by LS.
    """

    chetime: str = Field(
        ...,
        title="시간 (Trade time)",
        description="Trade time in 'HHMMSS' format.",
        examples=["093015"],
    )
    price: int = Field(
        ...,
        title="현재가 (Trade price)",
        description="Trade price for this row. Decimal scale not declared in available source.",
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code versus previous close. '1' = upper limit, '2' = "
            "up, '3' = unchanged, '4' = lower limit, '5' = down per LS "
            "convention."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of change versus previous close. Sign convention not declared in available source.",
        examples=[800, 0],
    )
    diff: float = Field(
        ...,
        title="등락율 (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.02, 0.0, -0.5],
    )
    cvolume: int = Field(
        ...,
        title="체결수량 (Trade quantity)",
        description="Trade quantity in shares for this row.",
        examples=[100, 5000],
    )
    chdegree: float = Field(
        ...,
        title="체결강도 (Trade strength)",
        description="LS-defined trade strength indicator. Formula not declared in available source.",
        examples=[105.32, 98.74],
    )
    volume: int = Field(
        ...,
        title="거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares as of this row.",
        examples=[15000000],
    )
    mdvolume: int = Field(
        ...,
        title="매도체결수량 (Sell-side trade volume)",
        description="Cumulative sell-aggressor trade volume in shares as of this row.",
        examples=[7500000],
    )
    mdchecnt: int = Field(
        ...,
        title="매도체결건수 (Sell-side trade count)",
        description="Cumulative sell-aggressor trade count as of this row.",
        examples=[12000],
    )
    msvolume: int = Field(
        ...,
        title="매수체결수량 (Buy-side trade volume)",
        description="Cumulative buy-aggressor trade volume in shares as of this row.",
        examples=[7500000],
    )
    mschecnt: int = Field(
        ...,
        title="매수체결건수 (Buy-side trade count)",
        description="Cumulative buy-aggressor trade count as of this row.",
        examples=[12000],
    )
    revolume: int = Field(
        ...,
        title="순체결량 (Net trade volume)",
        description="Net trade volume (buy minus sell aggressor) in shares. Sign convention per LS.",
        examples=[0, 100, -50],
    )
    rechecnt: int = Field(
        ...,
        title="순체결건수 (Net trade count)",
        description="Net trade count (buy minus sell aggressor). Sign convention per LS.",
        examples=[0, 5, -3],
    )


class T1301Response(BaseModel):
    """t1301 response envelope."""

    header: Optional[T1301ResponseHeader]
    cont_block: Optional[T1301OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1301OutBlock1] = Field(
        default_factory=list,
        title="시간대별 체결 리스트 (Per-trade rows)",
        description="List of per-trade rows. Time ordering not declared in available source.",
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
