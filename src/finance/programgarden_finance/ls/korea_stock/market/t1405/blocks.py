"""Pydantic models for LS Securities OpenAPI t1405 (투자경고/매매정지/정리매매조회 / restriction flags screen).

t1405 lists Korean stock issues currently flagged under one of nine
restriction categories: 투자경고 (investment warning), 매매정지 (trading
suspension), 정리매매 (delisting trading), 투자주의 (caution), 투자위험
(risk), 위험예고 (risk warning), 단기과열지정 (short-term overheating),
이상급등종목 (abnormal surge), 상장주식수부족 (listed-share shortage).
Pagination is via ``cts_shcode``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``date`` / ``edate`` (designation / release date) format and
      ``cts_shcode`` token format are NOT declared in the available
      source; consume as returned by LS.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1405RequestHeader(BlockRequestHeader):
    """t1405 request header. Inherits the standard LS request header schema."""
    pass


class T1405ResponseHeader(BlockResponseHeader):
    """t1405 response header. Inherits the standard LS response header schema."""
    pass


class T1405InBlock(BaseModel):
    """t1405InBlock — input block for the restriction flags screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all (전체), '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥).",
        examples=["0", "1", "2"],
    )
    jongchk: Literal["1", "2", "3", "4", "5", "6", "7", "8", "9"] = Field(
        ...,
        title="종목체크 (Restriction category)",
        description=(
            "Restriction category to query. '1' = investment warning "
            "(투자경고), '2' = trading suspension (매매정지), '3' = "
            "delisting trading (정리매매), '4' = caution (투자주의), '5' = "
            "risk (투자위험), '6' = risk warning (위험예고), '7' = short-"
            "term overheating (단기과열지정), '8' = abnormal surge "
            "(이상급등종목), '9' = listed-share shortage (상장주식수부족)."
        ),
        examples=["1", "2", "3", "7"],
    )
    cts_shcode: str = Field(
        default=" ",
        title="종목코드_CTS (Continuation cursor)",
        description="Continuation cursor for paged queries. Default ' ' (space) on first request; pass back ``cts_shcode`` from the previous response. Treat as opaque LS-defined token.",
        examples=[" "],
    )


class T1405Request(BaseModel):
    """t1405 request envelope."""

    header: T1405RequestHeader = T1405RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1405",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1405InBlock"], T1405InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1405"
    )


class T1405OutBlock(BaseModel):
    """t1405OutBlock — continuation block (echoes ``cts_shcode``)."""

    cts_shcode: str = Field(
        ...,
        title="종목코드_CTS (Continuation cursor)",
        description="Continuation cursor for the next paged request. Empty / space when no further rows are available.",
        examples=[" ", ""],
    )


class T1405OutBlock1(BaseModel):
    """t1405OutBlock1 — per-issue restriction row."""

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
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    date: str = Field(
        ...,
        title="지정일 (Designation date)",
        description="Date the restriction flag was applied. Format typically 'YYYYMMDD'.",
        examples=["20260101"],
    )
    edate: str = Field(
        ...,
        title="해제일 (Release date)",
        description="Date the flag is scheduled to be released. Empty when not applicable.",
        examples=["", "20260301"],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1405Response(BaseModel):
    """t1405 response envelope."""

    header: Optional[T1405ResponseHeader]
    cont_block: Optional[T1405OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1405OutBlock1] = Field(
        default_factory=list,
        title="투자경고/매매정지/정리매매 종목 리스트 (Restricted issue rows)",
        description="List of issues currently flagged under the requested restriction category.",
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
