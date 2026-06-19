"""Pydantic models for LS Securities OpenAPI t1511 (업종현재가 / sector current quote).

t1511 returns a single-shot snapshot for a given sector/index code: current
index value, previous-day index, change/percent change, intraday volume and
trading value, open/high/low + 52-week / year-to-date high/low milestones,
the four leading sub-indices for the sector, and the rising / falling /
limit-up / limit-down / unchanged constituent counts.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``upcode`` examples ('001' KOSPI composite, '101' KOSPI200, '501'
      KRX100, '301' KOSDAQ composite) mirror LS sample script verbatim;
      the full sector code table is NOT enumerated in the available
      source — additional sector codes exist beyond these four.
    - ``sign`` 5-way direction ('1'..'5') mirrors LS conventions used in
      neighbouring TRs (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락); not
      re-asserted per-field here when delegated to ``firsign`` / ``secsign``
      / ``thrsign`` / ``forsign`` (sub-index direction codes).
    - Decimal scale of ``pricejisu`` / ``jniljisu`` / sub-index values is
      10.2 (LS scale), declared by LS Securities on 2026-06-13 (field width
      7.2→10.2). The currency unit of ``value`` / ``valuechange`` /
      ``jnilvalue`` is still NOT declared in the available source — consume
      as returned by LS.
    - ``opentime`` / ``hightime`` / ``lowtime`` are HHMMSS-style timestamps
      per LS convention; format not asserted beyond what source declares.
    - Constituent-count fields (``highjo`` / ``upjo`` / ``unchgjo`` /
      ``lowjo`` / ``downjo``) are population counts of stocks within the
      sector; the membership criterion (cap floor / liquidity) is NOT
      declared in the available source.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1511RequestHeader(BlockRequestHeader):
    """t1511 request header. Inherits the standard LS request header schema."""
    pass


class T1511ResponseHeader(BlockResponseHeader):
    """t1511 response header. Inherits the standard LS response header schema."""
    pass


class T1511InBlock(BaseModel):
    """t1511InBlock — input block for the sector current-quote query."""

    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description=(
            "Sector / index code. LS sample-script declared values include "
            "'001' (KOSPI composite), '101' (KOSPI200), '501' (KRX100), "
            "'301' (KOSDAQ composite). Full sector code table not "
            "enumerated in the available source."
        ),
        examples=["001", "101", "501", "301"],
    )


class T1511Request(BaseModel):
    """t1511 request envelope."""

    header: T1511RequestHeader = T1511RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1511",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1511InBlock"], T1511InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1511"
    )


class T1511OutBlock(BaseModel):
    """t1511OutBlock — sector current-quote snapshot block."""

    gubun: str = Field(
        default="",
        title="업종구분 (Sector division)",
        description="Sector division marker. Code values not enumerated in the available source; consume as returned by LS.",
        examples=[""],
    )
    hname: str = Field(
        default="",
        title="업종명 (Sector name)",
        description="Sector / index display name in Korean.",
        examples=["코스피", "코스피200", "코스닥"],
    )
    pricejisu: float = Field(
        default=0.0,
        title="현재지수 (Current index value)",
        description="Current index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2650.50],
    )
    jniljisu: float = Field(
        default=0.0,
        title="전일지수 (Previous-day index value)",
        description="Previous-day close index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2640.10],
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
        description="Magnitude of index change versus previous close. Pair with ``sign`` for direction. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[10.40, 0.0],
    )
    diffjisu: float = Field(
        default=0.0,
        title="지수등락율 (Index change percent)",
        description="Percent change of the index versus previous close.",
        examples=[0.39, -0.50],
    )
    jnilvolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description="Previous-day cumulative traded volume across the sector.",
        examples=[450000000],
    )
    volume: int = Field(
        default=0,
        title="당일거래량 (Today volume)",
        description="Today cumulative traded volume across the sector.",
        examples=[460000000],
    )
    volumechange: int = Field(
        default=0,
        title="거래량전일대비 (Volume delta vs prior day)",
        description="Volume difference versus previous day.",
        examples=[10000000, -5000000],
    )
    volumerate: float = Field(
        default=0.0,
        title="거래량비율 (Volume ratio)",
        description="Volume ratio versus previous day. Baseline definition not declared in the available source; consume as returned by LS.",
        examples=[102.22],
    )
    jnilvalue: int = Field(
        default=0,
        title="전일거래대금 (Previous-day trading value)",
        description="Previous-day cumulative trading value. Currency unit not declared in the available source.",
        examples=[7800000],
    )
    value: int = Field(
        default=0,
        title="당일거래대금 (Today trading value)",
        description="Today cumulative trading value. Currency unit not declared in the available source.",
        examples=[8000000],
    )
    valuechange: int = Field(
        default=0,
        title="거래대금전일대비 (Trading-value delta vs prior day)",
        description="Trading-value difference versus previous day.",
        examples=[200000, -100000],
    )
    valuerate: float = Field(
        default=0.0,
        title="거래대금비율 (Trading-value ratio)",
        description="Trading-value ratio versus previous day. Baseline definition not declared in the available source.",
        examples=[102.56],
    )
    openjisu: float = Field(
        default=0.0,
        title="시가지수 (Open index value)",
        description="Index level at session open. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2641.20],
    )
    opendiff: float = Field(
        default=0.0,
        title="시가등락율 (Open change percent)",
        description="Percent change at open versus previous close.",
        examples=[0.04, -0.20],
    )
    opentime: str = Field(
        default="",
        title="시가시간 (Open time)",
        description="Time at which the open index value was set, HHMMSS-style per LS convention.",
        examples=["090000"],
    )
    highjisu: float = Field(
        default=0.0,
        title="고가지수 (Intraday high index value)",
        description="Intraday high index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2655.80],
    )
    highdiff: float = Field(
        default=0.0,
        title="고가등락율 (High change percent)",
        description="Percent change at intraday high versus previous close.",
        examples=[0.59],
    )
    hightime: str = Field(
        default="",
        title="고가시간 (High time)",
        description="Time at which the intraday high was set, HHMMSS-style per LS convention.",
        examples=["103045"],
    )
    lowjisu: float = Field(
        default=0.0,
        title="저가지수 (Intraday low index value)",
        description="Intraday low index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2638.20],
    )
    lowdiff: float = Field(
        default=0.0,
        title="저가등락율 (Low change percent)",
        description="Percent change at intraday low versus previous close.",
        examples=[-0.07],
    )
    lowtime: str = Field(
        default="",
        title="저가시간 (Low time)",
        description="Time at which the intraday low was set, HHMMSS-style per LS convention.",
        examples=["091230"],
    )
    whjisu: float = Field(
        default=0.0,
        title="52주최고지수 (52-week high index value)",
        description="52-week high index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2700.00],
    )
    whchange: float = Field(
        default=0.0,
        title="52주최고현재가대비 (52-week high vs current delta)",
        description="Difference between current index and the 52-week high. Sign convention not declared in the available source.",
        examples=[-49.50],
    )
    whjday: str = Field(
        default="",
        title="52주최고지수일자 (52-week high date)",
        description="Date on which the 52-week high was set, YYYYMMDD-style per LS convention.",
        examples=["20260201"],
    )
    wljisu: float = Field(
        default=0.0,
        title="52주최저지수 (52-week low index value)",
        description="52-week low index level.",
        examples=[2400.00],
    )
    wlchange: float = Field(
        default=0.0,
        title="52주최저현재가대비 (52-week low vs current delta)",
        description="Difference between current index and the 52-week low. Sign convention not declared in the available source.",
        examples=[250.50],
    )
    wljday: str = Field(
        default="",
        title="52주최저지수일자 (52-week low date)",
        description="Date on which the 52-week low was set, YYYYMMDD-style per LS convention.",
        examples=["20251015"],
    )
    yhjisu: float = Field(
        default=0.0,
        title="연중최고지수 (Year-to-date high index value)",
        description="Year-to-date high index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2700.00],
    )
    yhchange: float = Field(
        default=0.0,
        title="연중최고현재가대비 (YTD high vs current delta)",
        description="Difference between current index and the YTD high. Sign convention not declared in the available source.",
        examples=[-49.50],
    )
    yhjday: str = Field(
        default="",
        title="연중최고지수일자 (YTD high date)",
        description="Date on which the YTD high was set, YYYYMMDD-style per LS convention.",
        examples=["20260201"],
    )
    yljisu: float = Field(
        default=0.0,
        title="연중최저지수 (Year-to-date low index value)",
        description="Year-to-date low index level. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2500.00],
    )
    ylchange: float = Field(
        default=0.0,
        title="연중최저현재가대비 (YTD low vs current delta)",
        description="Difference between current index and the YTD low. Sign convention not declared in the available source.",
        examples=[150.50],
    )
    yljday: str = Field(
        default="",
        title="연중최저지수일자 (YTD low date)",
        description="Date on which the YTD low was set, YYYYMMDD-style per LS convention.",
        examples=["20260105"],
    )
    firstjcode: str = Field(
        default="",
        title="첫번째지수코드 (First sub-index code)",
        description="Sector code of the first leading sub-index.",
        examples=["002"],
    )
    firstjname: str = Field(
        default="",
        title="첫번째지수명 (First sub-index name)",
        description="Display name of the first leading sub-index.",
        examples=["대형주"],
    )
    firstjisu: float = Field(
        default=0.0,
        title="첫번째지수 (First sub-index value)",
        description="Current value of the first leading sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2700.50],
    )
    firsign: str = Field(
        default="",
        title="첫번째대비구분 (First sub-index direction code)",
        description="Direction code per LS convention ('1'..'5') for the first sub-index.",
        examples=["2", "3"],
    )
    firchange: float = Field(
        default=0.0,
        title="첫번째전일대비 (First sub-index delta)",
        description="Magnitude of change vs previous close for the first sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[10.20, 0.0],
    )
    firdiff: float = Field(
        default=0.0,
        title="첫번째등락율 (First sub-index change percent)",
        description="Percent change vs previous close for the first sub-index.",
        examples=[0.38, -0.20],
    )
    secondjcode: str = Field(
        default="",
        title="두번째지수코드 (Second sub-index code)",
        description="Sector code of the second leading sub-index.",
        examples=["003"],
    )
    secondjname: str = Field(
        default="",
        title="두번째지수명 (Second sub-index name)",
        description="Display name of the second leading sub-index.",
        examples=["중형주"],
    )
    secondjisu: float = Field(
        default=0.0,
        title="두번째지수 (Second sub-index value)",
        description="Current value of the second leading sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2400.00],
    )
    secsign: str = Field(
        default="",
        title="두번째대비구분 (Second sub-index direction code)",
        description="Direction code per LS convention ('1'..'5') for the second sub-index.",
        examples=["2", "5"],
    )
    secchange: float = Field(
        default=0.0,
        title="두번째전일대비 (Second sub-index delta)",
        description="Magnitude of change vs previous close for the second sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[5.10, -3.20],
    )
    secdiff: float = Field(
        default=0.0,
        title="두번째등락율 (Second sub-index change percent)",
        description="Percent change vs previous close for the second sub-index.",
        examples=[0.21, -0.13],
    )
    thirdjcode: str = Field(
        default="",
        title="세번째지수코드 (Third sub-index code)",
        description="Sector code of the third leading sub-index.",
        examples=["004"],
    )
    thirdjname: str = Field(
        default="",
        title="세번째지수명 (Third sub-index name)",
        description="Display name of the third leading sub-index.",
        examples=["소형주"],
    )
    thirdjisu: float = Field(
        default=0.0,
        title="세번째지수 (Third sub-index value)",
        description="Current value of the third leading sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[2200.00],
    )
    thrsign: str = Field(
        default="",
        title="세번째대비구분 (Third sub-index direction code)",
        description="Direction code per LS convention ('1'..'5') for the third sub-index.",
        examples=["3", "2"],
    )
    thrchange: float = Field(
        default=0.0,
        title="세번째전일대비 (Third sub-index delta)",
        description="Magnitude of change vs previous close for the third sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[0.0, 1.50],
    )
    thrdiff: float = Field(
        default=0.0,
        title="세번째등락율 (Third sub-index change percent)",
        description="Percent change vs previous close for the third sub-index.",
        examples=[0.0, 0.07],
    )
    fourthjcode: str = Field(
        default="",
        title="네번째지수코드 (Fourth sub-index code)",
        description="Sector code of the fourth leading sub-index.",
        examples=["005"],
    )
    fourthjname: str = Field(
        default="",
        title="네번째지수명 (Fourth sub-index name)",
        description="Display name of the fourth leading sub-index.",
        examples=["코스피200"],
    )
    fourthjisu: float = Field(
        default=0.0,
        title="네번째지수 (Fourth sub-index value)",
        description="Current value of the fourth leading sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[350.50],
    )
    forsign: str = Field(
        default="",
        title="네번째대비구분 (Fourth sub-index direction code)",
        description="Direction code per LS convention ('1'..'5') for the fourth sub-index.",
        examples=["2", "5"],
    )
    forchange: float = Field(
        default=0.0,
        title="네번째전일대비 (Fourth sub-index delta)",
        description="Magnitude of change vs previous close for the fourth sub-index. Length 10.2 (LS scale). Changed by LS Securities on 2026-06-13 (field width 7.2→10.2).",
        examples=[1.50, -0.80],
    )
    fordiff: float = Field(
        default=0.0,
        title="네번째등락율 (Fourth sub-index change percent)",
        description="Percent change vs previous close for the fourth sub-index.",
        examples=[0.43, -0.23],
    )
    highjo: int = Field(
        default=0,
        title="상승종목수 (Rising-stock count)",
        description="Count of constituent stocks in the sector trading above previous close.",
        examples=[450],
    )
    upjo: int = Field(
        default=0,
        title="상한종목수 (Limit-up count)",
        description="Count of constituent stocks at the daily upper price limit.",
        examples=[5],
    )
    unchgjo: int = Field(
        default=0,
        title="보합종목수 (Unchanged count)",
        description="Count of constituent stocks unchanged versus previous close.",
        examples=[80],
    )
    lowjo: int = Field(
        default=0,
        title="하락종목수 (Falling-stock count)",
        description="Count of constituent stocks trading below previous close.",
        examples=[350],
    )
    downjo: int = Field(
        default=0,
        title="하한종목수 (Limit-down count)",
        description="Count of constituent stocks at the daily lower price limit.",
        examples=[2],
    )


class T1511Response(BaseModel):
    """t1511 response envelope."""

    header: Optional[T1511ResponseHeader] = None
    block: Optional[T1511OutBlock] = Field(
        None,
        title="업종현재가 데이터 (Sector current-quote data)",
        description="Sector index, change, volume, 52-week / YTD high-low milestones, and constituent counts.",
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
