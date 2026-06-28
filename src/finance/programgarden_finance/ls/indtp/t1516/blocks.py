"""Pydantic models for LS Securities OpenAPI t1516 (업종별종목시세 / per-sector stock list).

t1516 returns the constituent stock list for a given sector / index,
together with the sector index summary (continuation cursor + index value
+ change). Pagination is via ``shcode`` (last constituent's short code on
the previous page).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``gubun`` 3-way (1=KOSPI 업종 / 2=KOSDAQ 업종 / 3=섹터지수) is
      LS-source-declared verbatim.
    - ``upcode`` accepts both standard market sector codes (e.g. '001'
      KOSPI composite, '301' KOSDAQ composite) and theme/sector codes
      depending on ``gubun``; full code table not enumerated in source.
    - ``sign`` 5-way direction ('1'..'5') mirrors LS convention used in
      neighbouring TRs (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).
    - Decimal scale of ``pricejisu`` and currency unit of
      ``total`` (시가총액) / ``value`` (거래대금) are NOT declared in the
      available source — consume as returned by LS.
    - ``frgsvolume`` (외인순매수) / ``orgsvolume`` (기관순매수) sign
      convention (positive = net buy / negative = net sell) NOT
      declared in source — consume as returned by LS.
    - ``diff_vol`` (거래증가율) baseline (vs prior day vs average vs
      session) NOT declared in source.
    - ``sojinrate`` (소진율) baseline (foreign-ownership consumption
      rate; vs cap floor / vs total listed) NOT declared in source.
    - ``perx`` is current-period PER as published by LS; computation
      window not declared.
    - Time ordering of OutBlock1 rows not declared; consume as returned
      by LS.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ...models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1516RequestHeader(BlockRequestHeader):
    """t1516 request header. Inherits the standard LS request header schema."""
    pass


class T1516ResponseHeader(BlockResponseHeader):
    """t1516 response header. Inherits the standard LS response header schema."""
    pass


class T1516InBlock(BaseModel):
    """t1516InBlock — input block for the per-sector stock list query."""

    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description=(
            "Sector / index code. Interpretation depends on ``gubun``: market "
            "sector codes (e.g. '001' KOSPI composite, '301' KOSDAQ composite) "
            "for gubun='1'/'2', sector-index codes for gubun='3'. Full code "
            "table not enumerated in source."
        ),
        examples=["001", "301"],
    )
    gubun: Literal["1", "2", "3"] = Field(
        ...,
        title="구분 (Sector type)",
        description="Sector type. '1' = KOSPI 업종 (KOSPI sector), '2' = KOSDAQ 업종 (KOSDAQ sector), '3' = 섹터지수 (sector index).",
        examples=["1", "2", "3"],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Continuation short code)",
        description="Pagination cursor. Default ' ' (space) on first request; pass back ``shcode`` from the previous OutBlock for continuation.",
        examples=["", " ", "005930"],
    )


class T1516Request(BaseModel):
    """t1516 request envelope."""

    header: T1516RequestHeader = T1516RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1516",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1516InBlock"], T1516InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1516"
    )


class T1516OutBlock(BaseModel):
    """t1516OutBlock — sector-summary continuation block."""

    shcode: str = Field(
        default="",
        title="종목코드 (Continuation short code)",
        description="Last constituent's short code on this page; pass back as ``shcode`` for the next page.",
        examples=["005930"],
    )
    pricejisu: float = Field(
        default=0.0,
        title="지수 (Sector index value)",
        description="Current value of the sector index. Decimal scale not declared in the available source; consume as returned by LS.",
        examples=[2650.50],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5'; 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).",
        examples=["2", "3", "5"],
    )
    change: float = Field(
        default=0.0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of index change versus previous close. Pair with ``sign`` for direction.",
        examples=[10.40, 0.0],
    )
    jdiff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change of the sector index versus previous close.",
        examples=[0.39, -0.50],
    )


class T1516OutBlock1(BaseModel):
    """t1516OutBlock1 — per-stock row within the sector."""

    hname: str = Field(
        default="",
        title="종목명 (Stock name)",
        description="Stock display name in Korean.",
        examples=["삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current trade price.",
        examples=[79800],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5').",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of price change versus previous close. Pair with ``sign`` for direction.",
        examples=[800, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.02, -0.50],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    open: int = Field(
        default=0,
        title="시가 (Open price)",
        description="Open price for the session.",
        examples=[79000],
    )
    high: int = Field(
        default=0,
        title="고가 (Intraday high price)",
        description="Intraday high price for the session.",
        examples=[80100],
    )
    low: int = Field(
        default=0,
        title="저가 (Intraday low price)",
        description="Intraday low price for the session.",
        examples=[78800],
    )
    sojinrate: float = Field(
        default=0.0,
        title="소진율 (Foreign-ownership consumption rate)",
        description="Foreign-ownership consumption rate. Baseline (vs cap floor / vs total listed) not declared in the available source; consume as returned by LS.",
        examples=[35.50],
    )
    beta: float = Field(
        default=0.0,
        title="베타계수 (Beta coefficient)",
        description="Beta coefficient versus the market. Reference index and computation window not declared in the available source.",
        examples=[1.02, 0.85],
    )
    perx: float = Field(
        default=0.0,
        title="PER (Price-earnings ratio)",
        description="Price-earnings ratio published by LS. Computation window not declared in the available source.",
        examples=[10.50, 25.30],
    )
    frgsvolume: int = Field(
        default=0,
        title="외인순매수 (Foreign net buy)",
        description="Foreign-investor net-buy volume. Sign convention (positive = net buy / negative = net sell) not declared in the available source; consume as returned by LS.",
        examples=[100000, -50000, 0],
    )
    orgsvolume: int = Field(
        default=0,
        title="기관순매수 (Institutional net buy)",
        description="Institutional net-buy volume. Sign convention not declared in the available source; consume as returned by LS.",
        examples=[200000, -75000, 0],
    )
    diff_vol: float = Field(
        default=0.0,
        title="거래증가율 (Volume-growth percent)",
        description="Volume-growth percent. Baseline (vs prior day vs average vs session) not declared in the available source; consume as returned by LS.",
        examples=[12.50, -5.30],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Stock short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    total: int = Field(
        default=0,
        title="시가총액 (Market cap)",
        description="Market capitalisation. Currency unit not declared in the available source; consume as returned by LS.",
        examples=[480000000],
    )
    value: int = Field(
        default=0,
        title="거래대금 (Trading value)",
        description="Cumulative trading value for the session. Currency unit not declared in the available source; consume as returned by LS.",
        examples=[1200000],
    )


class T1516Response(BaseModel):
    """t1516 response envelope."""

    header: Optional[T1516ResponseHeader] = None
    cont_block: Optional[T1516OutBlock] = Field(
        None,
        title="연속 데이터 (Continuation block)",
        description="Sector-index summary + continuation cursor.",
    )
    block: List[T1516OutBlock1] = Field(
        default_factory=list,
        title="종목 리스트 (Per-stock rows)",
        description="List of per-stock rows within the sector.",
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
