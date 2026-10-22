"""Pydantic models for LS Securities OpenAPI t1537 (테마종목별시세조회 / per-theme stock list).

t1537 returns the constituent stock list for a given theme ``tmcode``,
together with a theme-summary block (rising-stock count, total constituent
count, rising-stock ratio, theme name).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` 5-way direction ('1'..'5') mirrors LS convention used in
      neighbouring TRs (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).
    - ``jniltime`` (전일동시간) reference-time alignment (cumulative-to-
      cumulative same-clock vs full-day) is NOT declared in the available
      source.
    - ``yeprice`` (예상체결가) is the LS-published expected match price
      (typically used during pre-/post-auction phases); availability and
      semantics during continuous trading not declared.
    - ``value`` (누적거래대금) and ``marketcap`` (시가총액) units are
      explicitly declared as 백만 (millions of KRW) per the LS Korean
      source comments.
    - ``uprate`` is encoded as ``int`` per LS source; the unit (percent ×
      100 / percent / fraction) is NOT declared in the available source.
    - Time ordering of OutBlock1 rows not declared.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1537RequestHeader(BlockRequestHeader):
    """t1537 request header. Inherits the standard LS request header schema."""
    pass


class T1537ResponseHeader(BlockResponseHeader):
    """t1537 response header. Inherits the standard LS response header schema."""
    pass


class T1537InBlock(BaseModel):
    """t1537InBlock — input block for the per-theme stock-list query."""

    tmcode: str = Field(
        ...,
        title="테마코드 (Theme code)",
        description="Theme code. Discoverable via t8425.",
        examples=["0001"],
    )


class T1537Request(BaseModel):
    """t1537 request envelope."""

    header: T1537RequestHeader = T1537RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1537",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1537InBlock"], T1537InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1537"
    )


class T1537OutBlock(BaseModel):
    """t1537OutBlock — theme-summary continuation block."""

    upcnt: int = Field(
        default=0,
        title="상승종목수 (Rising-stock count)",
        description="Count of theme-constituent stocks trading above previous close.",
        examples=[12],
    )
    tmcnt: int = Field(
        default=0,
        title="테마종목수 (Theme-constituent count)",
        description="Total count of stocks in the theme.",
        examples=[20],
    )
    uprate: int = Field(
        default=0,
        title="상승종목비율 (Rising-stock ratio)",
        description="Ratio of rising stocks within the theme. Unit (percent ×100 / percent / fraction) not declared in the available source; consume as returned by LS.",
        examples=[60, 50],
    )
    tmname: str = Field(
        default="",
        title="테마명 (Theme name)",
        description="Theme display name in Korean.",
        examples=["2차전지"],
    )


class T1537OutBlock1(BaseModel):
    """t1537OutBlock1 — per-stock row within the theme."""

    hname: str = Field(
        default="",
        title="종목명 (Stock name)",
        description="Stock display name in Korean.",
        examples=["삼성SDI"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current trade price.",
        examples=[450000],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5'; 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Pair with ``sign`` for direction.",
        examples=[5000, 0, -2000],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.12, -0.45, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[150000],
    )
    jniltime: float = Field(
        default=0.0,
        title="전일동시간 (Same-time-prior-day volume)",
        description="Same-time-prior-day cumulative volume. Reference-time alignment (cumulative-to-cumulative same-clock vs full-day) not declared in the available source.",
        examples=[145000.0],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Stock short code)",
        description="6-digit Korean stock short code.",
        examples=["006400"],
    )
    yeprice: int = Field(
        default=0,
        title="예상체결가 (Expected match price)",
        description="LS-published expected match price (typically used during pre-/post-auction phases). Availability and semantics during continuous trading not declared in the available source.",
        examples=[449500, 0],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description="Open price for the session.",
        examples=[448000],
    )
    high: int = Field(
        default=0,
        title="고가 (Intraday high price)",
        description="Intraday high price for the session.",
        examples=[453000],
    )
    low: int = Field(
        default=0,
        title="저가 (Intraday low price)",
        description="Intraday low price for the session.",
        examples=[447500],
    )
    value: int = Field(
        default=0,
        title="누적거래대금(백만) (Cumulative trading value, millions KRW)",
        description="Cumulative trading value for the session, denominated in millions of KRW per LS source.",
        examples=[67500],
    )
    marketcap: int = Field(
        default=0,
        title="시가총액(백만) (Market cap, millions KRW)",
        description="Market capitalisation, denominated in millions of KRW per LS source.",
        examples=[31000000],
    )


class T1537Response(BaseModel):
    """t1537 response envelope."""

    header: Optional[T1537ResponseHeader] = None
    cont_block: Optional[T1537OutBlock] = Field(
        None,
        title="테마 요약 (Theme-summary block)",
        description="Theme-summary block: rising-stock count, total constituent count, rising-stock ratio, theme name.",
    )
    block: List[T1537OutBlock1] = Field(
        default_factory=list,
        title="종목 리스트 (Per-stock rows)",
        description="List of per-stock rows within the theme.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str = ""
    rsp_msg: str = ""
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
