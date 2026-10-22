"""Pydantic models for LS Securities OpenAPI t1442 (신고/신저가 / 52-week-style new-high / new-low screen).

t1442 returns Korean stock issues currently breaking out to a new high or new
low across one of eight lookback windows (previous day, 5/10/20/60/90 days,
52-week, year-to-date), with optional 일시돌파 vs. 돌파유지 (transient vs.
sustained) filtering. Pagination is via the ``idx`` cursor.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``jc_num`` / ``jc_num2`` (target-exclusion bitmasks) bit semantics
      are NOT declared in the available source.
    - ``pastsign`` / ``pastchange`` / ``pastdiff`` reference comparison
      window relationship to ``type2`` is NOT declared explicitly; consume
      as returned by LS.
"""

from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1442RequestHeader(BlockRequestHeader):
    """t1442 request header. Inherits the standard LS request header schema."""
    pass


class T1442ResponseHeader(BlockResponseHeader):
    """t1442 response header. Inherits the standard LS response header schema."""
    pass


class T1442InBlock(BaseModel):
    """t1442InBlock — input block for the new-high / new-low screen."""

    gubun: Literal["0", "1", "2"] = Field(
        ...,
        title="구분 (Market division)",
        description="Market division. '0' = all, '1' = KOSPI, '2' = KOSDAQ.",
        examples=["0", "1", "2"],
    )
    type1: Literal["0", "1"] = Field(
        ...,
        title="신고신저 (High / low side)",
        description="High vs. low side. '0' = new high (신고), '1' = new low (신저).",
        examples=["0", "1"],
    )
    type2: Literal["0", "1", "2", "3", "4", "5", "6", "7"] = Field(
        ...,
        title="기간 (Lookback window)",
        description=(
            "Lookback window. '0' = previous day (전일), '1' = 5 days, '2' "
            "= 10 days, '3' = 20 days, '4' = 60 days, '5' = 90 days, '6' = "
            "52 weeks, '7' = year-to-date (년중)."
        ),
        examples=["0", "6", "7"],
    )
    type3: Literal["0", "1"] = Field(
        ...,
        title="유지여부 (Sustain flag)",
        description="Sustain flag. '0' = transient breakout (일시돌파), '1' = sustained breakout (돌파유지).",
        examples=["0", "1"],
    )
    jc_num: int = Field(
        default=0,
        title="대상제외 비트마스크 (Exclusion bitmask 1)",
        description="Primary target-exclusion bitmask. Bit-position semantics not declared in available source.",
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
        description="Pagination cursor. 0 on first request; pass back ``idx`` from the previous response.",
        examples=[0],
    )
    jc_num2: int = Field(
        default=0,
        title="대상제외2 비트마스크 (Exclusion bitmask 2)",
        description="Secondary target-exclusion bitmask. Bit-position semantics not declared in available source.",
        examples=[0],
    )


class T1442Request(BaseModel):
    """t1442 request envelope."""

    header: T1442RequestHeader = T1442RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1442",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1442InBlock"], T1442InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1442"
    )


class T1442OutBlock(BaseModel):
    """t1442OutBlock — continuation block (paging cursor)."""

    idx: int = Field(
        ...,
        title="연속조회키 (Pagination cursor)",
        description="Pagination cursor for the next paged request. 0 when no further rows are available.",
        examples=[0],
    )


class T1442OutBlock1(BaseModel):
    """t1442OutBlock1 — per-issue new-high / new-low row."""

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
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5').",
        examples=["2", "5"],
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
        title="거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    pastprice: int = Field(
        ...,
        title="이전가 (Past price)",
        description="Reference past price within the lookback window selected by ``type2``. Specific row alignment within the window not declared in available source.",
        examples=[78000],
    )
    pastsign: str = Field(
        ...,
        title="이전가대비구분 (Past-price direction code)",
        description="Direction code versus the past price per LS convention ('1'..'5').",
        examples=["2", "3", "5"],
    )
    pastchange: int = Field(
        ...,
        title="이전가대비 (Past-price delta)",
        description="Magnitude of price change versus the past price. Sign convention not declared in available source.",
        examples=[1800, 0],
    )
    pastdiff: float = Field(
        ...,
        title="이전가대비율(%) (Past-price percent change)",
        description="Percent change versus the past price.",
        examples=[2.31, 0.0, -1.5],
    )


class T1442Response(BaseModel):
    """t1442 response envelope."""

    header: Optional[T1442ResponseHeader]
    cont_block: Optional[T1442OutBlock] = Field(
        None,
        title="연속조회 블록 (Continuation block)",
        description="Continuation cursor block for paged follow-up requests.",
    )
    block: List[T1442OutBlock1] = Field(
        default_factory=list,
        title="신고/신저가 종목 리스트 (New-high / new-low rows)",
        description="List of issues currently breaking out under the requested high/low and lookback window.",
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
