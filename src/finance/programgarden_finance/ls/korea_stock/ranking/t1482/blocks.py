"""Pydantic models for LS Securities OpenAPI t1482 (시간외거래량상위 / after-hours volume ranking).

t1482 returns Korean stock issues ranked by after-hours single-price session
cumulative volume (or trading value, if requested), filtered by market
division (KOSPI / KOSDAQ) and issue inclusion mode (preferreds / managed-issue
exclusion). Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sort_gbn`` numeric Literal (0 / 1) preserves the LS-source-declared
      enum verbatim — note this is integer-typed unlike other ranking
      enums in this category.
    - ``vol`` (회전율) baseline definition (vs. listed shares, etc.) is
      NOT declared in available source; consume as returned by LS.
    - Decimal scale of ``price`` / ``change`` / ``value`` is NOT declared
      in available source.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1482RequestHeader(BlockRequestHeader):
    """t1482 request header. Inherits the standard LS request header schema."""
    pass


class T1482ResponseHeader(BlockResponseHeader):
    """t1482 response header. Inherits the standard LS response header schema."""
    pass


class T1482InBlock(BaseModel):
    """t1482InBlock — input block for the after-hours volume ranking screen."""

    sort_gbn: Literal[0, 1] = Field(
        default=0,
        title="정렬구분 (Sort key)",
        description="Sort key per LS enumeration (integer-typed). 0 = by volume (거래량), 1 = by trading value (거래대금).",
        examples=[0, 1],
    )
    gubun: Literal["0", "1", "2"] = Field(
        default="0",
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    jongchk: Literal["0", "1", "2", "3"] = Field(
        default="0",
        title="종목체크 (Issue inclusion mode)",
        description="Issue inclusion mode per LS enumeration: '0' = all (전체), '1' = exclude preferred (우선제외), '2' = exclude managed-issue (관리제외), '3' = exclude both preferred and managed-issue (우선관리제외). The source field-name 'jongchk' is preserved verbatim despite being labeled as a 거래량 mode in the source docstring — semantics follow this enum.",
        examples=["0", "1", "2", "3"],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[0],
    )


class T1482OutBlock(BaseModel):
    """t1482OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1482OutBlock1(BaseModel):
    """t1482OutBlock1 — per-issue after-hours volume ranking row."""

    hname: str = Field(
        default="",
        title="종목명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="After-hours single-price session current price. Decimal scale not declared in available source.",
        examples=[55300],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention: '1' = upper limit (상한), '2' = up (상승), '3' = unchanged (보합), '4' = lower limit (하한), '5' = down (하락).",
        examples=["1", "2", "3", "4", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Sign convention not declared; pair with ``sign`` for direction.",
        examples=[1500, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율(%) (Change percent)",
        description="After-hours session percent change versus previous close.",
        examples=[2.78, -1.45, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="After-hours cumulative traded volume in shares.",
        examples=[150000],
    )
    vol: float = Field(
        default=0.0,
        title="회전율(%) (Turnover percent)",
        description="Turnover ratio expressed as a percentage. Baseline definition (vs. listed shares, etc.) not declared in available source.",
        examples=[0.05, 0.0],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    value: int = Field(
        default=0,
        title="누적거래대금 (Cumulative trading value)",
        description="After-hours cumulative trading value. Currency unit and scale not declared in available source.",
        examples=[8500],
    )


class T1482Request(BaseModel):
    """t1482 request envelope."""
    header: T1482RequestHeader = T1482RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1482",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1482"
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1482Response(BaseModel):
    """t1482 response envelope."""
    header: Optional[T1482ResponseHeader] = None
    cont_block: Optional[T1482OutBlock] = None
    block: list[T1482OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1482RequestHeader",
    "T1482ResponseHeader",
    "T1482InBlock",
    "T1482OutBlock",
    "T1482OutBlock1",
    "T1482Request",
    "T1482Response",
]
