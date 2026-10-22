"""Pydantic models for LS Securities OpenAPI t1444 (시가총액상위 / market-cap ranking by sector).

t1444 returns Korean stock issues ranked by market capitalization within a
specific industry / sector code. Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``upcode`` (업종코드) is a 3-digit LS-defined sector code; full code
      table is not enumerated in available source. ``001`` (KOSPI
      composite) and ``301`` (KOSDAQ composite) are the most common
      examples per the LS sample script.
    - ``vol_rate`` (거래비중) baseline definition (vs. market-wide volume,
      vs. sector volume, etc.) is NOT declared in available source.
    - ``rate`` (비중) baseline (sector market-cap share, etc.) is NOT
      declared in the available source.
    - ``total`` 단위 ('억원') mirrors the LS Korean source label
      verbatim — keep as is.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1444RequestHeader(BlockRequestHeader):
    """t1444 request header. Inherits the standard LS request header schema."""
    pass


class T1444ResponseHeader(BlockResponseHeader):
    """t1444 response header. Inherits the standard LS response header schema."""
    pass


class T1444InBlock(BaseModel):
    """t1444InBlock — input block for the market-cap ranking screen."""

    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description="3-digit LS-defined sector / industry code. Common values: '001' (KOSPI composite), '301' (KOSDAQ composite). Other values map to specific industry sub-sectors per the LS sector code table.",
        examples=["001", "301"],
    )
    idx: int = Field(
        default=0,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response on follow-ups. Treat as opaque LS-defined token.",
        examples=[0],
    )


class T1444Request(BaseModel):
    """t1444 request envelope."""

    header: T1444RequestHeader = T1444RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1444",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1444InBlock"], T1444InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1444"
    )


class T1444OutBlock(BaseModel):
    """t1444OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1444OutBlock1(BaseModel):
    """t1444OutBlock1 — per-issue market-cap ranking row."""

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
    volume: int = Field(
        ...,
        title="거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    vol_rate: float = Field(
        ...,
        title="거래비중(%) (Volume share percent)",
        description="Volume share expressed as a percentage. Comparison baseline (vs. market-wide volume, vs. sector volume, etc.) not declared in available source.",
        examples=[1.25, 0.0],
    )
    total: int = Field(
        ...,
        title="시가총액 (Market capitalization, 억원)",
        description="Market capitalization in units of 억원 (100 million KRW) per the LS Korean source label.",
        examples=[3300000],
    )
    rate: float = Field(
        ...,
        title="비중(%) (Sector weight percent)",
        description="Weight expressed as a percentage. Baseline (sector market-cap share, etc.) not declared in available source.",
        examples=[18.5, 0.5],
    )
    for_rate: float = Field(
        ...,
        title="외인비중(%) (Foreign holding percent)",
        description="Foreign-investor holding ratio expressed as a percentage of issued shares.",
        examples=[52.34, 0.0],
    )


class T1444Response(BaseModel):
    """t1444 response envelope."""

    header: Optional[T1444ResponseHeader]
    cont_block: Optional[T1444OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1444OutBlock1] = Field(
        default_factory=list,
        title="시가총액상위 종목 리스트 (Market-cap ranking rows)",
        description="List of issues ranked by market capitalization within the requested sector.",
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
