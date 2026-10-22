"""Pydantic models for LS Securities OpenAPI t1404 (관리/불성실/투자유의조회 / supervision flags screen).

t1404 lists Korean stock issues currently flagged under one of four
supervision categories: 관리종목 (administrative issues), 불성실공시 (disclosure
violations), 투자유의 (investment caution), or 투자환기 (investment alert).
Pagination is via ``cts_shcode``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``reason`` text values, ``date``/``edate`` semantics (designation /
      release date conventions), ``tprice`` reference-date pricing scale,
      and ``cts_shcode`` token format are NOT declared in the available
      source; consume as returned by LS.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1404RequestHeader(BlockRequestHeader):
    """t1404 request header. Inherits the standard LS request header schema."""
    pass


class T1404ResponseHeader(BlockResponseHeader):
    """t1404 response header. Inherits the standard LS response header schema."""
    pass


class T1404InBlock(BaseModel):
    """t1404InBlock — input block for the supervision flags screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all (전체), '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥).",
        examples=["0", "1", "2"],
    )
    jongchk: Literal["1", "2", "3", "4"] = Field(
        ...,
        title="종목체크 (Supervision category)",
        description=(
            "Supervision category to query. '1' = administrative (관리), "
            "'2' = disclosure violations (불성실공시), '3' = investment "
            "caution (투자유의), '4' = investment alert (투자환기)."
        ),
        examples=["1", "2", "3", "4"],
    )
    cts_shcode: str = Field(
        default=" ",
        title="종목코드_CTS (Continuation cursor)",
        description="Continuation cursor for paged queries. Default ' ' (space) on first request; pass back ``cts_shcode`` from the previous response. Treat as opaque LS-defined token.",
        examples=[" "],
    )


class T1404Request(BaseModel):
    """t1404 request envelope."""

    header: T1404RequestHeader = T1404RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1404",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1404InBlock"], T1404InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1404"
    )


class T1404OutBlock(BaseModel):
    """t1404OutBlock — continuation block (echoes ``cts_shcode``)."""

    cts_shcode: str = Field(
        ...,
        title="종목코드_CTS (Continuation cursor)",
        description="Continuation cursor for the next paged request. Empty / space when no further rows are available.",
        examples=[" ", ""],
    )


class T1404OutBlock1(BaseModel):
    """t1404OutBlock1 — per-issue supervision row."""

    hname: str = Field(
        ...,
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price. Decimal scale not declared in available source.",
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5'). See ``sign`` in market TRs.",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        ...,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Sign convention not declared in available source.",
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
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    date: str = Field(
        ...,
        title="지정일 (Designation date)",
        description="Date the supervision flag was applied to the issue. Format not declared in available source; typically 'YYYYMMDD'.",
        examples=["20260101"],
    )
    tprice: int = Field(
        ...,
        title="지정일주가 (Price on designation date)",
        description="Price of the issue on the designation date. Decimal scale not declared in available source.",
        examples=[80000],
    )
    tchange: int = Field(
        ...,
        title="지정일대비 (Delta vs designation date)",
        description="Price change since the designation date. Sign convention not declared in available source.",
        examples=[200, 0, -500],
    )
    tdiff: float = Field(
        ...,
        title="대비율(%) (Percent change vs designation date)",
        description="Percent change since the designation date.",
        examples=[0.25, 0.0, -0.62],
    )
    reason: str = Field(
        ...,
        title="사유 (Reason)",
        description="Free-text reason for the supervision designation. Value set not declared in available source; consume as returned by LS.",
        examples=["감사의견 거절", "공시번복"],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    edate: str = Field(
        ...,
        title="해제일 (Release date)",
        description="Date the flag is scheduled to be released, when applicable. Empty otherwise. Format typically 'YYYYMMDD'.",
        examples=["", "20260301"],
    )


class T1404Response(BaseModel):
    """t1404 response envelope."""

    header: Optional[T1404ResponseHeader]
    cont_block: Optional[T1404OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1404OutBlock1] = Field(
        default_factory=list,
        title="관리/불성실/투자유의 종목 리스트 (Supervised issue rows)",
        description="List of issues currently flagged under the requested supervision category.",
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
