"""Pydantic models for LS Securities OpenAPI t1452 (거래량상위 / volume ranking).

t1452 returns Korean stock issues ranked by cumulative trading volume,
filtered by market division (KOSPI / KOSDAQ), today vs. previous-day mode,
price-change range, target-exclusion bitmask, and volume thresholds.
Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jc_num`` (target-exclusion bitmask) bit-position semantics are NOT
      declared in available source; consume as returned by LS.
    - Decimal scale of ``price`` / ``change`` is NOT declared in available
      source; consume as returned by LS.
    - ``vol`` (회전율) and ``bef_diff`` (전일비) baseline definitions are
      NOT declared in the available source; consume as returned by LS.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1452RequestHeader(BlockRequestHeader):
    """t1452 request header. Inherits the standard LS request header schema."""
    pass


class T1452ResponseHeader(BlockResponseHeader):
    """t1452 response header. Inherits the standard LS response header schema."""
    pass


class T1452InBlock(BaseModel):
    """t1452InBlock — input block for the volume ranking screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="시장구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    jnilgubun: Literal["1", "2"] = Field(
        ...,
        title="전일구분 (Day flag)",
        description="Day flag. '1' = today (당일), '2' = previous day (전일).",
        examples=["1", "2"],
    )
    sdiff: int = Field(
        default=0,
        title="시작등락율 (Start change percent)",
        description="Inclusive lower bound of the price-change percent filter. 0 means no lower bound. Decimal scale convention not declared in available source; pass as integer per LS sample.",
        examples=[0, -10, 5],
    )
    ediff: int = Field(
        default=0,
        title="종료등락율 (End change percent)",
        description="Inclusive upper bound of the price-change percent filter. 0 means no upper bound.",
        examples=[0, 30],
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


class T1452Request(BaseModel):
    """t1452 request envelope."""

    header: T1452RequestHeader = T1452RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1452",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1452InBlock"], T1452InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1452"
    )


class T1452OutBlock(BaseModel):
    """t1452OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1452OutBlock1(BaseModel):
    """t1452OutBlock1 — per-issue volume ranking row."""

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
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    vol: float = Field(
        ...,
        title="회전율(%) (Turnover percent)",
        description="Turnover ratio expressed as a percentage. Baseline definition (vs. listed shares, vs. floating shares, etc.) not declared in available source.",
        examples=[3.5, 0.0],
    )
    jnilvolume: int = Field(
        ...,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's cumulative volume in shares.",
        examples=[12000000],
    )
    bef_diff: float = Field(
        ...,
        title="전일비(%) (Volume vs. previous-day percent)",
        description="Volume comparison versus previous day expressed as a percentage. Exact baseline definition not declared in available source.",
        examples=[125.0, 50.0, 0.0],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1452Response(BaseModel):
    """t1452 response envelope."""

    header: Optional[T1452ResponseHeader]
    cont_block: Optional[T1452OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1452OutBlock1] = Field(
        default_factory=list,
        title="거래량상위 종목 리스트 (Volume ranking rows)",
        description="List of issues ranked by cumulative trading volume.",
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
