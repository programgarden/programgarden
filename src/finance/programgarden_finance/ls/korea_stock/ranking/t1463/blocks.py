"""Pydantic models for LS Securities OpenAPI t1463 (거래대금상위 / trading-value ranking).

t1463 returns Korean stock issues ranked by cumulative trading value (won
volume), filtered by market division (KOSPI / KOSDAQ), today vs. previous-day
mode, target-exclusion bitmasks, price / volume thresholds, and exchange
division (KRX / NXT / unified). Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jc_num`` / ``jc_num2`` (target-exclusion bitmasks) bit-position
      semantics are NOT declared in available source; consume as returned
      by LS.
    - ``value`` / ``jnilvalue`` / ``total`` 단위 ('백만원') mirrors the
      LS Korean source label verbatim — keep as is.
    - ``bef_diff`` (전일비) baseline (today's value / previous day's
      value, etc.) is NOT declared in available source.
    - ``filler`` is an LS-defined opaque field; semantics not declared.
    - ``idx`` is an opaque LS-defined paging cursor; pass back verbatim.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1463RequestHeader(BlockRequestHeader):
    """t1463 request header. Inherits the standard LS request header schema."""
    pass


class T1463ResponseHeader(BlockResponseHeader):
    """t1463 response header. Inherits the standard LS response header schema."""
    pass


class T1463InBlock(BaseModel):
    """t1463InBlock — input block for the trading-value ranking screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="시장구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    jnilgubun: Literal["0", "1"] = Field(
        ...,
        title="전일구분 (Day flag)",
        description="Day flag. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
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
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified. Other values default to KRX behavior per LS.",
        examples=["K", "N", "U"],
    )


class T1463Request(BaseModel):
    """t1463 request envelope."""

    header: T1463RequestHeader = T1463RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1463",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1463InBlock"], T1463InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1463"
    )


class T1463OutBlock(BaseModel):
    """t1463OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1463OutBlock1(BaseModel):
    """t1463OutBlock1 — per-issue trading-value ranking row."""

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
    value: int = Field(
        ...,
        title="거래대금 (Trading value, 백만원)",
        description="Cumulative trading value in units of 백만원 (1 million KRW) per the LS Korean source label.",
        examples=[850],
    )
    jnilvalue: int = Field(
        ...,
        title="전일거래대금 (Previous-day trading value, 백만원)",
        description="Previous trading day's cumulative trading value in units of 백만원 per the LS Korean source label.",
        examples=[720],
    )
    bef_diff: float = Field(
        ...,
        title="전일비(%) (Value vs. previous-day percent)",
        description="Trading-value comparison versus previous day expressed as a percentage. Exact baseline definition not declared in available source.",
        examples=[118.0, 50.0, 0.0],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    filler: str = Field(
        default="",
        title="filler (Filler)",
        description="LS-defined opaque filler field. Semantics not declared in available source.",
        examples=[""],
    )
    jnilvolume: int = Field(
        ...,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's cumulative volume in shares.",
        examples=[12000000],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description="Exchange-resolved short code echoed for the issue. Format and semantics not declared in available source.",
        examples=[""],
    )
    total: int = Field(
        ...,
        title="시가총액 (Market capitalization, 백만원)",
        description="Market capitalization in units of 백만원 (1 million KRW) per the LS Korean source label.",
        examples=[330000000],
    )


class T1463Response(BaseModel):
    """t1463 response envelope."""

    header: Optional[T1463ResponseHeader]
    cont_block: Optional[T1463OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1463OutBlock1] = Field(
        default_factory=list,
        title="거래대금상위 종목 리스트 (Trading-value ranking rows)",
        description="List of issues ranked by cumulative trading value.",
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
