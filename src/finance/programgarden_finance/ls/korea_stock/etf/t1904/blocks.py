"""Pydantic models for LS Securities OpenAPI t1904 (ETF constituents / PDF inquiry / ETF구성종목조회).

t1904 returns the constituent basket (PDF = Portfolio Deposit File) for
a Korean-market ETF on a specific PDF-application date. The response
carries:

    - ``OutBlock`` (``cont_block``) — ETF summary block: today-or-not
      flag, PDF date, ETF current quote (price + sign + change + diff +
      volume), NAV + previous-day NAV (with direction / change / ratio),
      sector reference, front-month future reference, benchmark index
      reference, ETF total NAV (in 100M-KRW units), constituent-issue
      count, CU share count, cash position, management company, and
      aggregate evaluation / market-cap totals.
    - ``OutBlock1`` (``block``) — list of per-constituent rows: short
      code, name, current price + previous-close direction + change +
      ratio, traded volume, traded value (in 백만 / million KRW units),
      unit count for index / cash / collateral / contracts, par price /
      setup-cash amount, evaluation amount, constituent market cap,
      PDF date, weight in evaluation amount, and per-constituent vs.
      ETF return spread.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Decimal scale and currency unit of price / NAV / cap / weight
      fields are NOT declared in the source available to this codebase
      beyond what the source label states (e.g., 백만 = million KRW for
      ``value``, 억원 = 100M KRW for ``etftotcap``); consume as returned
      by LS.
    - ``sign`` direction codes follow the standard LS stock convention
      ('1' = 상한 / '2' = 상승 / '3' = 보합 / '4' = 하한 / '5' = 하락).
    - ``sgb`` Literal["1", "2"] — '1' = evaluation amount (평가금액),
      '2' = security count (증권수). Source declares this enum.
    - ``chk_tday`` (당일구분) code values are NOT declared in the source
      available to this codebase; consume as returned by LS. Likely
      "is the queried PDF date today's basket" but exact code mapping
      is not asserted.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1904.py``
      (``shcode='069500'`` = KODEX 200, ``sgb='1'`` = sort by
      evaluation amount).
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1904RequestHeader(BlockRequestHeader):
    """t1904 request header. Inherits the standard LS request header schema."""
    pass


class T1904ResponseHeader(BlockResponseHeader):
    """t1904 response header. Inherits the standard LS response header schema."""
    pass


class T1904InBlock(BaseModel):
    """t1904InBlock — input block for the ETF constituents / PDF inquiry."""

    shcode: str = Field(
        default="",
        title="ETF단축코드 (ETF short code)",
        description="6-digit Korean ETF short code (e.g., '069500' for KODEX 200).",
        examples=["069500"],
    )
    date: str = Field(
        default="",
        title="PDF적용일자 (PDF application date)",
        description=(
            "PDF (Portfolio Deposit File) application date in 'YYYYMMDD' "
            "format. Empty string queries the most recent PDF."
        ),
        examples=["", "20260228"],
    )
    sgb: Literal["1", "2"] = Field(
        default="1",
        title="정렬기준 (Sort key)",
        description=(
            "Sort key for the constituent list. '1' = sort by evaluation "
            "amount (평가금액), '2' = sort by security count (증권수)."
        ),
        examples=["1", "2"],
    )


class T1904OutBlock(BaseModel):
    """t1904OutBlock — ETF summary block in the constituents response.

    Decimal scale and currency unit of price / NAV / cap fields beyond
    the source labels (e.g., 억원 for ``etftotcap``) are NOT declared
    in the source available to this codebase; consume as returned by LS.
    """

    chk_tday: str = Field(
        default="",
        title="당일구분 (Today flag)",
        description=(
            "Today-flag for the queried PDF date. Code values not "
            "declared in available source; consume as returned by LS."
        ),
        examples=[""],
    )
    date: str = Field(
        default="",
        title="PDF적용일자 (PDF application date)",
        description="PDF application date echoed for the queried request, in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    price: int = Field(
        default=0,
        title="ETF현재가 (ETF current price)",
        description="ETF current trade price. Decimal scale not declared in available source.",
        examples=[37520],
    )
    sign: str = Field(
        default="",
        title="ETF전일대비구분 (ETF direction)",
        description=(
            "ETF direction code vs. previous close. '1' = upper limit (상한), "
            "'2' = up (상승), '3' = unchanged (보합), '4' = lower limit (하한), "
            "'5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="ETF전일대비 (ETF change vs. previous close)",
        description="ETF price change vs. previous close. Sign convention not declared in available source.",
        examples=[120, -85, 0],
    )
    diff: float = Field(
        default=0.0,
        title="ETF등락율 (ETF change ratio)",
        description="ETF change ratio (%) vs. previous close. Decimal scale not declared in available source.",
        examples=[0.32, -0.23, 0.0],
    )
    volume: int = Field(
        default=0,
        title="ETF누적거래량 (ETF cumulative volume)",
        description="ETF cumulative traded volume in shares for the session.",
        examples=[2500000],
    )
    nav: float = Field(
        default=0.0,
        title="NAV",
        description="Current Net Asset Value per ETF share. Decimal scale not declared in available source.",
        examples=[37498.21],
    )
    navsign: str = Field(
        default="",
        title="NAV전일대비구분 (NAV direction)",
        description="Direction code for NAV vs. previous-day NAV. Same coding as ``sign``.",
        examples=["2", "3", "5"],
    )
    navchange: float = Field(
        default=0.0,
        title="NAV전일대비 (NAV change)",
        description="NAV change vs. previous-day NAV. Sign convention not declared in available source.",
        examples=[120.45, -85.20, 0.0],
    )
    navdiff: float = Field(
        default=0.0,
        title="NAV등락율 (NAV change ratio)",
        description="NAV change ratio (%) vs. previous-day NAV. Decimal scale not declared in available source.",
        examples=[0.32, -0.23, 0.0],
    )
    jnilnav: float = Field(
        default=0.0,
        title="전일NAV (Previous-day NAV)",
        description="Previous trading day's closing NAV per share.",
        examples=[37377.76],
    )
    jnilnavsign: str = Field(
        default="",
        title="전일NAV전일대비구분 (Previous-day NAV direction)",
        description="Direction code for previous-day NAV vs. NAV two days prior. Same coding as ``sign``.",
        examples=["2", "3", "5"],
    )
    jnilnavchange: float = Field(
        default=0.0,
        title="전일NAV전일대비 (Previous-day NAV change)",
        description="Previous-day NAV change vs. NAV two days prior.",
        examples=[105.20, -78.30, 0.0],
    )
    jnilnavdiff: float = Field(
        default=0.0,
        title="전일NAV등락율 (Previous-day NAV change ratio)",
        description="Previous-day NAV change ratio (%) vs. NAV two days prior.",
        examples=[0.28, -0.21, 0.0],
    )
    upname: str = Field(
        default="",
        title="업종명 (Sector name)",
        description="Sector name to which the ETF belongs.",
        examples=["KOSPI200"],
    )
    upcode: str = Field(
        default="",
        title="업종코드 (Sector code)",
        description="Sector code to which the ETF belongs.",
        examples=["001"],
    )
    upprice: float = Field(
        default=0.0,
        title="업종현재가 (Sector index value)",
        description="Sector index current value. Decimal scale not declared in available source.",
        examples=[375.42],
    )
    upsign: str = Field(
        default="",
        title="업종전일비구분 (Sector direction)",
        description="Sector index direction code vs. previous close. Same coding as ``sign``.",
        examples=["2", "3", "5"],
    )
    upchange: float = Field(
        default=0.0,
        title="업종전일대비 (Sector index change)",
        description="Sector index change vs. previous close.",
        examples=[1.25, -0.85, 0.0],
    )
    updiff: float = Field(
        default=0.0,
        title="업종등락율 (Sector index change ratio)",
        description="Sector index change ratio (%) vs. previous close.",
        examples=[0.33, -0.22, 0.0],
    )
    futname: str = Field(
        default="",
        title="선물최근월물명 (Front-month future name)",
        description="Front-month index-future contract name. Empty when not applicable.",
        examples=["KOSPI200 F 202512"],
    )
    futcode: str = Field(
        default="",
        title="선물최근월물코드 (Front-month future code)",
        description="Front-month index-future contract code.",
        examples=["101W6000"],
    )
    futprice: float = Field(
        default=0.0,
        title="선물현재가 (Front-month future price)",
        description="Front-month future current price. Decimal scale not declared in available source.",
        examples=[376.10],
    )
    futsign: str = Field(
        default="",
        title="선물전일비구분 (Future direction)",
        description="Front-month future direction code vs. previous close. Same coding as ``sign``.",
        examples=["2", "3", "5"],
    )
    futchange: float = Field(
        default=0.0,
        title="선물전일대비 (Future change)",
        description="Front-month future change vs. previous close.",
        examples=[1.30, -0.95, 0.0],
    )
    futdiff: float = Field(
        default=0.0,
        title="선물등락율 (Future change ratio)",
        description="Front-month future change ratio (%) vs. previous close.",
        examples=[0.35, -0.25, 0.0],
    )
    upname2: str = Field(
        default="",
        title="참고지수명 (Reference index name)",
        description="Reference (benchmark) index name that the ETF tracks.",
        examples=["KOSPI200"],
    )
    upcode2: str = Field(
        default="",
        title="참고지수코드 (Reference index code)",
        description="Reference (benchmark) index code that the ETF tracks.",
        examples=["001"],
    )
    upprice2: float = Field(
        default=0.0,
        title="참고지수현재가 (Reference index value)",
        description="Reference index current value. Decimal scale not declared in available source.",
        examples=[375.42],
    )
    etftotcap: int = Field(
        default=0,
        title="순자산총액(단위:억) (ETF NAV total / 100M KRW)",
        description=(
            "Total ETF net asset value in 억원 (100-million KRW units) "
            "per the LS source label."
        ),
        examples=[45000],
    )
    etfnum: int = Field(
        default=0,
        title="구성종목수 (Constituent count)",
        description="Number of constituent issues in the PDF basket.",
        examples=[200],
    )
    etfcunum: int = Field(
        default=0,
        title="CU주식수 (CU share count)",
        description=(
            "Creation Unit (CU) share count — number of ETF shares per "
            "creation / redemption unit."
        ),
        examples=[50000],
    )
    cash: int = Field(
        default=0,
        title="현금 (Cash position)",
        description="Cash position within the PDF basket. Currency unit not declared in available source; consume as returned by LS.",
        examples=[0],
    )
    opcom_nmk: str = Field(
        default="",
        title="운용사명 (Management company)",
        description="Asset-management company name (운용사).",
        examples=["삼성자산운용"],
    )
    tot_pval: int = Field(
        default=0,
        title="전종목평가금액합 (Aggregate constituent evaluation total)",
        description="Aggregate evaluation amount across all constituents. Currency unit not declared in available source.",
        examples=[450000000],
    )
    tot_sigatval: int = Field(
        default=0,
        title="전종목구성시가총액합 (Aggregate constituent market-cap total)",
        description="Aggregate constituent market-cap total. Currency unit not declared in available source.",
        examples=[2500000000],
    )


class T1904OutBlock1(BaseModel):
    """t1904OutBlock1 — per-constituent row in the ETF PDF response.

    Decimal scale and currency unit of price / value / cap / weight
    fields beyond the source labels are NOT declared in the source
    available to this codebase; consume as returned by LS.
    """

    shcode: str = Field(
        default="",
        title="단축코드 (Constituent short code)",
        description="6-digit Korean stock short code of the constituent issue.",
        examples=["005930"],
    )
    hname: str = Field(
        default="",
        title="한글명 (Korean name)",
        description="Korean name of the constituent issue.",
        examples=["삼성전자"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current trade price of the constituent issue. Decimal scale not declared in available source.",
        examples=[78500],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Direction)",
        description="Direction code vs. previous close. Same coding as in ``OutBlock.sign``.",
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change vs. previous close)",
        description="Constituent price change vs. previous close. Sign convention not declared in available source.",
        examples=[200, -150, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change ratio)",
        description="Constituent change ratio (%) vs. previous close.",
        examples=[0.26, -0.19, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the constituent.",
        examples=[3500000],
    )
    value: int = Field(
        default=0,
        title="거래대금(백만) (Trade value / million KRW)",
        description=(
            "Cumulative traded value, in 백만 (million KRW) units per the "
            "LS source label."
        ),
        examples=[275000],
    )
    icux: int = Field(
        default=0,
        title="단위증권수(계약수/원화현금/USD현금/창고증권) (Unit count)",
        description=(
            "Per-CU unit count for the constituent. Source label notes "
            "this can represent contract count, KRW cash, USD cash, or "
            "warehouse-receipt securities depending on the constituent "
            "type. Unit interpretation depends on the constituent and is "
            "not further declared in available source."
        ),
        examples=[120, 0],
    )
    parprice: int = Field(
        default=0,
        title="액면금액/설정현금액 (Par price / setup-cash amount)",
        description=(
            "Par price for stock constituents; setup-cash amount for cash "
            "items per the LS source label. Decimal scale not declared in "
            "available source."
        ),
        examples=[100, 5000],
    )
    pvalue: int = Field(
        default=0,
        title="평가금액 (Evaluation amount)",
        description="Evaluation amount for the constituent within the PDF basket. Currency unit not declared in available source.",
        examples=[9420000],
    )
    sigatvalue: int = Field(
        default=0,
        title="구성시가총액 (Constituent market cap)",
        description="Market capitalization of the constituent issue. Currency unit not declared in available source.",
        examples=[470000000000],
    )
    profitdate: str = Field(
        default="",
        title="PDF적용일자 (PDF application date)",
        description="PDF application date for the row, in 'YYYYMMDD' format.",
        examples=["20260228"],
    )
    weight: float = Field(
        default=0.0,
        title="비중(평가금액) (Weight by evaluation amount)",
        description="Constituent weight (%) based on evaluation amount. Decimal scale not declared in available source.",
        examples=[28.45],
    )
    diff2: float = Field(
        default=0.0,
        title="ETF종목과등락차 (ETF-vs.-constituent return spread)",
        description=(
            "Difference (%) between the constituent's return and the "
            "ETF's return. Decimal scale and sign convention not declared "
            "in available source."
        ),
        examples=[0.06, -0.04, 0.0],
    )


class T1904Request(BaseModel):
    """t1904 request envelope."""

    header: T1904RequestHeader = T1904RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1904",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1904Response(BaseModel):
    """t1904 response envelope."""

    header: Optional[T1904ResponseHeader] = None
    cont_block: Optional[T1904OutBlock] = None
    block: list[T1904OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1904RequestHeader",
    "T1904ResponseHeader",
    "T1904InBlock",
    "T1904OutBlock",
    "T1904OutBlock1",
    "T1904Request",
    "T1904Response",
]
