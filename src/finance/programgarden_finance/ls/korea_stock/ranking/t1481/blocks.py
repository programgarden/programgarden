"""Pydantic models for LS Securities OpenAPI t1481 (시간외등락율상위 / after-hours change-percent ranking).

t1481 returns Korean stock issues ranked by after-hours single-price session
percent change, filtered by market division (KOSPI / KOSDAQ), direction
(gainers / losers), inclusion mode (preferreds / managed-issue exclusion), and
volume bucket. Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``volume`` (input bucket) labels are LS-defined buckets; their
      inclusive / exclusive endpoint semantics are NOT declared in
      available source. Use as opaque LS-defined values.
    - ``total`` 단위 ('억') mirrors the LS Korean source label verbatim
      — keep as is.
    - Decimal scale of ``price`` / ``change`` / ``offerho1`` / ``bidho1``
      / ``value`` is NOT declared in available source.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1481RequestHeader(BlockRequestHeader):
    """t1481 request header. Inherits the standard LS request header schema."""
    pass


class T1481ResponseHeader(BlockResponseHeader):
    """t1481 response header. Inherits the standard LS response header schema."""
    pass


class T1481InBlock(BaseModel):
    """t1481InBlock — input block for the after-hours change-percent ranking screen."""

    gubun1: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    gubun2: Literal["0", "1"] = Field(
        ...,
        title="상승하락 (Direction)",
        description="Direction. '0' = gainers (상승률), '1' = losers (하락률).",
        examples=["0", "1"],
    )
    jongchk: Literal["0", "1", "2", "3"] = Field(
        ...,
        title="종목체크 (Issue inclusion mode)",
        description="Issue inclusion mode per LS enumeration: '0' = all (전체), '1' = exclude preferred (우선제외), '2' = exclude managed-issue (관리제외), '3' = exclude both preferred and managed-issue (우선관리제외).",
        examples=["0", "1", "2", "3"],
    )
    volume: Literal["0", "1", "2", "3", "4", "5", "6", "7"] = Field(
        ...,
        title="거래량 (Volume bucket)",
        description="Volume bucket per LS enumeration: '0' = all (전체), '1' = ≥1천주, '2' = ≥5천주, '3' = ≥1만주, '4' = ≥5만주, '5' = ≥10만주, '6' = ≥50만주, '7' = ≥100만주.",
        examples=["0", "1", "2", "3", "4", "5", "6", "7"],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[0],
    )


class T1481Request(BaseModel):
    """t1481 request envelope."""

    header: T1481RequestHeader = T1481RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1481",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1481InBlock"], T1481InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1481"
    )


class T1481OutBlock(BaseModel):
    """t1481OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1481OutBlock1(BaseModel):
    """t1481OutBlock1 — per-issue after-hours change-percent ranking row."""

    hname: str = Field(
        ...,
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="After-hours single-price session current price. Decimal scale not declared in available source.",
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
        description="After-hours session percent change versus previous close.",
        examples=[2.78, -1.45, 0.0],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="After-hours cumulative traded volume in shares.",
        examples=[150000],
    )
    offerrem1: int = Field(
        ...,
        title="매도잔량 (Best ask quantity)",
        description="Quantity at the best ask price.",
        examples=[5000, 0],
    )
    bidrem1: int = Field(
        ...,
        title="매수잔량 (Best bid quantity)",
        description="Quantity at the best bid price.",
        examples=[3500, 0],
    )
    offerho1: int = Field(
        ...,
        title="매도호가 (Best ask price)",
        description="Best ask price. Decimal scale not declared in available source.",
        examples=[55400, 0],
    )
    bidho1: int = Field(
        ...,
        title="매수호가 (Best bid price)",
        description="Best bid price. Decimal scale not declared in available source.",
        examples=[55300, 0],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    value: int = Field(
        ...,
        title="누적거래대금 (Cumulative trading value)",
        description="After-hours cumulative trading value. Currency unit and scale not declared in available source.",
        examples=[8500],
    )
    total: int = Field(
        ...,
        title="시가총액 (Market capitalization, 억)",
        description="Market capitalization in units of 억 (100 million KRW) per the LS Korean source label.",
        examples=[3300000],
    )


class T1481Response(BaseModel):
    """t1481 response envelope."""

    header: Optional[T1481ResponseHeader]
    cont_block: Optional[T1481OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1481OutBlock1] = Field(
        default_factory=list,
        title="시간외등락율상위 종목 리스트 (After-hours change-percent ranking rows)",
        description="List of issues ranked by after-hours session percent change.",
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
