"""Pydantic models for LS Securities OpenAPI t1403 (Domestic Stock newly-listed issues query).

t1403 returns the list of issues newly listed within a requested month
range (YYYYMM..YYYYMM) for KOSPI / KOSDAQ / both, plus pricing metrics for
each issue: current price, change vs. prev. close, IPO offering price
(공모가), listing-date base price (등록일기준가) and listing-day close,
and the corresponding return ratios. Used for IPO post-listing analysis
and new-listing monitoring.

Response carries:
    - ``OutBlock`` (``cont_block``) — single ``idx`` continuation key for
      paged queries.
    - ``OutBlock1`` (``block``) — list of newly-listed issue rows.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale of price fields and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase; consume
      as returned by LS.
    - ``idx`` is the LS continuation cursor; pass back verbatim on
      follow-up requests.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1403.py``.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1403RequestHeader(BlockRequestHeader):
    """t1403 request header. Inherits the standard LS request header schema."""
    pass


class T1403ResponseHeader(BlockResponseHeader):
    """t1403 response header. Inherits the standard LS response header schema."""
    pass


class T1403InBlock(BaseModel):
    """t1403InBlock — input block for the newly-listed issues query."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="시장구분 (Market type)",
        description="Market type. '0' = all (전체), '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥).",
        examples=["0", "1", "2"],
    )
    styymm: str = Field(
        ...,
        title="시작상장월 (Start listing month)",
        description="Start listing month in 'YYYYMM' format (e.g., '202601').",
        examples=["202601"],
    )
    enyymm: str = Field(
        ...,
        title="종료상장월 (End listing month)",
        description="End listing month in 'YYYYMM' format (e.g., '202612').",
        examples=["202612"],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Continuation index)",
        description=(
            "Continuation index for paged queries. 0 on the first request; "
            "on follow-ups, pass back ``OutBlock.idx`` from the previous "
            "response. Treat as opaque LS-defined token."
        ),
        examples=[0],
    )


class T1403Request(BaseModel):
    """t1403 request envelope."""

    header: T1403RequestHeader = T1403RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1403",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1403InBlock"], T1403InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1403"
    )


class T1403OutBlock(BaseModel):
    """t1403OutBlock — continuation block carrying the ``idx`` cursor."""

    idx: int = Field(
        ...,
        title="연속조회키 (Continuation index)",
        description=(
            "Continuation index for the next paged request. Pass into "
            "``InBlock.idx`` on the follow-up call. Treat as opaque "
            "LS-defined token."
        ),
        examples=[0, 100],
    )


class T1403OutBlock1(BaseModel):
    """t1403OutBlock1 — newly-listed issue row.

    Decimal scale of price fields, currency unit, and time ordering of rows
    are NOT declared in the source available to this codebase; consume as
    returned by LS. Returns (등락률) include positive, negative, and zero
    examples since post-IPO performance can take any sign.
    """

    hname: str = Field(
        ...,
        title="종목명 (Issue name)",
        description="Korean issue name (e.g., '삼성전자').",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price. Decimal scale not declared in available source.",
        examples=[50000],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Change direction)",
        description=(
            "Change direction code vs. previous close. '1' = upper limit "
            "(상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower "
            "limit (하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Change amount)",
        description="Change amount vs. previous close.",
        examples=[1000, -1000, 0],
    )
    diff: float = Field(
        ...,
        title="등락율 (Change ratio)",
        description="Change ratio (%) vs. previous close. Decimal scale not declared in available source.",
        examples=[2.50, -2.50, 0.0],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the day.",
        examples=[1000000],
    )
    kmprice: int = Field(
        ...,
        title="공모가 (IPO offering price)",
        description="IPO offering price (공모가) at listing.",
        examples=[40000],
    )
    date: str = Field(
        ...,
        title="등록일 (Listing date)",
        description="Listing date in 'YYYYMMDD' format.",
        examples=["20260115"],
    )
    recprice: int = Field(
        ...,
        title="등록일기준가 (Listing-date base price)",
        description="Reference price as of the listing date (등록일기준가).",
        examples=[40000],
    )
    kmdiff: float = Field(
        ...,
        title="기준가등락율 (Return vs. offering price)",
        description="Return ratio (%) of current price vs. IPO offering price (공모가 대비).",
        examples=[25.00, -10.00, 0.0],
    )
    close: int = Field(
        ...,
        title="등록일종가 (Listing-day close)",
        description="Closing price on the listing day (상장 첫날 종가).",
        examples=[48000],
    )
    recdiff: float = Field(
        ...,
        title="등록일등락율 (Return vs. listing-day close)",
        description="Return ratio (%) of current price vs. listing-day close (등록일종가 대비).",
        examples=[4.17, -5.00, 0.0],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1403Response(BaseModel):
    """t1403 response envelope."""

    header: Optional[T1403ResponseHeader]
    cont_block: Optional[T1403OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation block carrying the ``idx`` cursor for the next page.",
    )
    block: List[T1403OutBlock1] = Field(
        default_factory=list,
        title="신규상장 종목 리스트 (Newly-listed issue rows)",
        description="List of newly-listed issue rows for the requested month range.",
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
