"""Pydantic models for LS Securities OpenAPI t1901 (ETF current quote / ETF현재가(시세)조회).

t1901 returns a snapshot of the current quote and ETF/ETN-specific
metadata for a single Korean-market ETF or ETN issue. The response
carries one ``OutBlock`` (no ``OutBlock1``) with:

    - Current price + previous-close direction + intraday OHLC + 52-week
      and year-high/low + cumulative volume / value.
    - ETF-specific NAV fields (current NAV, NAV vs. previous close,
      previous-day NAV, tracking error rate, premium/discount = 괴리율).
    - Top-5 sell-side and top-5 buy-side broker aggregate volumes with
      delta-vs-previous-snapshot and ratio columns.
    - Foreign-broker aggregate sell / buy totals.
    - Reference index name + code + current price (참고지수 — the
      benchmark the ETF tracks).
    - ETF / ETN classification, replication method (복제방법), VI flag,
      management company (운용사), up to 5 LPs (Liquidity Providers),
      ETN maturity / payment / final-trading dates and ETN-specific
      flags, listing date, and tracking-return multiplier (레버리지).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Decimal scale and currency unit of price / NAV / value fields are
      NOT declared in the source available to this codebase; consume
      as returned by LS. Domestic ETF prices in LS feeds are typically
      integer KRW per share, but this is not asserted as a contract.
    - ``sign`` direction codes follow the standard LS stock convention
      ('1' = 상한 / '2' = 상승 / '3' = 보합 / '4' = 하한 / '5' = 하락)
      per the example script display mapping at
      ``src/finance/example/korea_stock/run_t1901.py``.
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1901.py``
      (``shcode='069500'`` = KODEX 200).
    - Top-5 broker rank fields (offerno1..5 / bidno1..5 / dvol1..5 /
      svol1..5 / dcha1..5 / scha1..5 / ddiff1..5 / sdiff1..5) are
      preserved verbatim as 5 separate scalar fields rather than
      collapsed into an array — this matches the source layout exactly.
    - ETN-only fields are populated only for ETN issues and default to
      empty string for non-ETN ETF issues; this conditional behavior
      follows LS convention but is not asserted as a strict contract.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1901RequestHeader(BlockRequestHeader):
    """t1901 request header. Inherits the standard LS request header schema."""
    pass


class T1901ResponseHeader(BlockResponseHeader):
    """t1901 response header. Inherits the standard LS response header schema."""
    pass


class T1901InBlock(BaseModel):
    """t1901InBlock — input block for the ETF current-quote query."""

    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean ETF / ETN short code (e.g., '069500' for KODEX 200).",
        examples=["069500"],
    )


class T1901OutBlock(BaseModel):
    """t1901OutBlock — ETF current-quote and metadata block.

    Decimal scale and currency unit of price / NAV / value fields are
    NOT declared in the source available to this codebase; consume as
    returned by LS.
    """

    hname: str = Field(
        default="",
        title="한글명 (Korean name)",
        description="Korean ETF / ETN issue name.",
        examples=["KODEX 200"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current trade price. Decimal scale not declared in available source.",
        examples=[37520],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-close direction)",
        description=(
            "Direction code vs. previous close. '1' = upper limit (상한), "
            "'2' = up (상승), '3' = unchanged (보합), '4' = lower limit "
            "(하한), '5' = down (하락)."
        ),
        examples=["2", "3", "5"],
    )
    change: int = Field(
        default=0,
        title="전일대비 (Change vs. previous close)",
        description="Price change vs. previous close. Sign convention not declared in available source.",
        examples=[120, -85, 0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change ratio)",
        description="Change ratio (%) vs. previous close. Decimal scale not declared in available source.",
        examples=[0.32, -0.23, 0.0],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[2500000],
    )
    recprice: int = Field(
        default=0,
        title="기준가 (Base / reference price)",
        description="Reference price (typically previous close). Decimal scale not declared in available source.",
        examples=[37400],
    )
    avg: int = Field(
        default=0,
        title="가중평균 (Volume-weighted average price)",
        description="Volume-weighted average price for the session. Scale not declared in available source.",
        examples=[37510],
    )
    uplmtprice: int = Field(
        default=0,
        title="상한가 (Upper limit price)",
        description="Daily upper price limit (상한가) for the issue.",
        examples=[48620],
    )
    dnlmtprice: int = Field(
        default=0,
        title="하한가 (Lower limit price)",
        description="Daily lower price limit (하한가) for the issue.",
        examples=[26180],
    )
    jnilvolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description="Previous trading day's traded volume in shares.",
        examples=[3100000],
    )
    volumediff: int = Field(
        default=0,
        title="거래량차 (Volume difference)",
        description="Volume difference vs. previous-day cumulative volume at the same time of day. Sign convention not declared in available source.",
        examples=[150000, -200000, 0],
    )
    open: int = Field(
        default=0,
        title="시가 (Open)",
        description="Today's opening price.",
        examples=[37450],
    )
    opentime: str = Field(
        default="",
        title="시가시간 (Open time)",
        description="Time the opening price was set, in 'HHMMSS' format.",
        examples=["090000"],
    )
    high: int = Field(
        default=0,
        title="고가 (High)",
        description="Today's high price as of the response time.",
        examples=[37600],
    )
    hightime: str = Field(
        default="",
        title="고가시간 (High time)",
        description="Time the intraday high was set, in 'HHMMSS' format.",
        examples=["110523"],
    )
    low: int = Field(
        default=0,
        title="저가 (Low)",
        description="Today's low price as of the response time.",
        examples=[37380],
    )
    lowtime: str = Field(
        default="",
        title="저가시간 (Low time)",
        description="Time the intraday low was set, in 'HHMMSS' format.",
        examples=["091245"],
    )
    high52w: int = Field(
        default=0,
        title="52최고가 (52-week high)",
        description="52-week high price.",
        examples=[39250],
    )
    high52wdate: str = Field(
        default="",
        title="52최고가일 (52-week high date)",
        description="Date the 52-week high was set, in 'YYYYMMDD' format.",
        examples=["20251031"],
    )
    low52w: int = Field(
        default=0,
        title="52최저가 (52-week low)",
        description="52-week low price.",
        examples=[31200],
    )
    low52wdate: str = Field(
        default="",
        title="52최저가일 (52-week low date)",
        description="Date the 52-week low was set, in 'YYYYMMDD' format.",
        examples=["20250416"],
    )
    exhratio: float = Field(
        default=0.0,
        title="소진율 (Foreign holding limit-utilization ratio)",
        description="Foreign-investor holding limit utilization ratio (%). Decimal scale not declared in available source.",
        examples=[0.0],
    )
    flmtvol: int = Field(
        default=0,
        title="외국인보유수량 (Foreign-held quantity)",
        description="Total foreign-investor holding quantity in shares.",
        examples=[0],
    )
    per: float = Field(
        default=0.0,
        title="PER",
        description="Price-earnings ratio. Often 0 for ETF / ETN issues; consume as returned by LS.",
        examples=[0.0],
    )
    listing: int = Field(
        default=0,
        title="상장주식수(천) (Listed shares in thousands)",
        description="Listed share count, in thousands of shares (천주).",
        examples=[120000],
    )
    jkrate: int = Field(
        default=0,
        title="증거금율 (Margin ratio)",
        description="Margin ratio (%) for the issue. Scale not declared in available source.",
        examples=[20, 30, 40],
    )
    vol: float = Field(
        default=0.0,
        title="회전율 (Turnover ratio)",
        description="Turnover ratio. Decimal scale not declared in available source.",
        examples=[2.08],
    )
    shcode: str = Field(
        default="",
        title="단축코드 (Short code)",
        description="6-digit Korean ETF / ETN short code echoed for the queried issue.",
        examples=["069500"],
    )
    value: int = Field(
        default=0,
        title="누적거래대금 (Cumulative trade value)",
        description="Cumulative traded value (price × volume) for the session. Decimal scale not declared in available source.",
        examples=[93800000000],
    )
    highyear: int = Field(
        default=0,
        title="연중최고가 (Year-to-date high)",
        description="Year-to-date high price.",
        examples=[39100],
    )
    highyeardate: str = Field(
        default="",
        title="연중최고일자 (Year-to-date high date)",
        description="Date the year-to-date high was set, in 'YYYYMMDD' format.",
        examples=["20260315"],
    )
    lowyear: int = Field(
        default=0,
        title="연중최저가 (Year-to-date low)",
        description="Year-to-date low price.",
        examples=[33800],
    )
    lowyeardate: str = Field(
        default="",
        title="연중최저일자 (Year-to-date low date)",
        description="Date the year-to-date low was set, in 'YYYYMMDD' format.",
        examples=["20260108"],
    )
    upname: str = Field(
        default="",
        title="업종명 (Sector name)",
        description="Sector name to which the issue belongs.",
        examples=["KOSPI200"],
    )
    upcode: str = Field(
        default="",
        title="업종코드 (Sector code)",
        description="Sector code to which the issue belongs.",
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
        description=(
            "Sector index direction code vs. previous close. Same coding as "
            "``sign``: '1'..'5' = 상한 / 상승 / 보합 / 하한 / 하락."
        ),
        examples=["2", "3", "5"],
    )
    upchange: float = Field(
        default=0.0,
        title="업종전일대비 (Sector index change)",
        description="Sector index change vs. previous close. Sign convention not declared in available source.",
        examples=[1.25, -0.85, 0.0],
    )
    updiff: float = Field(
        default=0.0,
        title="업종등락율 (Sector index change ratio)",
        description="Sector index change ratio (%). Decimal scale not declared in available source.",
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
        description="Direction code for the front-month future vs. previous close. Same coding as ``sign``.",
        examples=["2", "3", "5"],
    )
    futchange: float = Field(
        default=0.0,
        title="선물전일대비 (Future change)",
        description="Front-month future change vs. previous close. Sign convention not declared in available source.",
        examples=[1.30, -0.95, 0.0],
    )
    futdiff: float = Field(
        default=0.0,
        title="선물등락율 (Future change ratio)",
        description="Front-month future change ratio (%). Decimal scale not declared in available source.",
        examples=[0.35, -0.25, 0.0],
    )
    nav: float = Field(
        default=0.0,
        title="NAV",
        description=(
            "Current Net Asset Value per share for the ETF. Decimal scale "
            "not declared in available source; consume as returned by LS."
        ),
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
    cocrate: float = Field(
        default=0.0,
        title="추적오차율 (Tracking error rate)",
        description=(
            "Tracking error rate (%) of the ETF vs. its underlying index. "
            "Decimal scale not declared in available source; sign convention "
            "(positive = above index vs. positive = absolute deviation) not "
            "declared either."
        ),
        examples=[0.05, -0.03, 0.0],
    )
    kasis: float = Field(
        default=0.0,
        title="괴리율 (Premium / discount ratio)",
        description=(
            "Premium / discount (%) of the market price relative to NAV. "
            "Decimal scale not declared in available source. Sign "
            "convention (positive = premium vs. negative = discount) "
            "not asserted; consume as returned by LS."
        ),
        examples=[0.06, -0.04, 0.0],
    )
    subprice: int = Field(
        default=0,
        title="대용가 (Substitute / collateral price)",
        description="Collateral substitute price for margin purposes. Scale not declared in available source.",
        examples=[28140],
    )
    offerno1: str = Field(
        default="",
        title="매도증권사코드1 (Top-1 sell broker code)",
        description="Top-1 sell-side aggregate broker code.",
        examples=["003"],
    )
    bidno1: str = Field(
        default="",
        title="매수증권사코드1 (Top-1 buy broker code)",
        description="Top-1 buy-side aggregate broker code.",
        examples=["005"],
    )
    dvol1: int = Field(
        default=0,
        title="총매도수량1 (Top-1 sell aggregate quantity)",
        description="Top-1 sell-side aggregate volume in shares.",
        examples=[450000],
    )
    svol1: int = Field(
        default=0,
        title="총매수수량1 (Top-1 buy aggregate quantity)",
        description="Top-1 buy-side aggregate volume in shares.",
        examples=[420000],
    )
    dcha1: int = Field(
        default=0,
        title="매도증감1 (Top-1 sell delta)",
        description="Top-1 sell-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[5000, -2000, 0],
    )
    scha1: int = Field(
        default=0,
        title="매수증감1 (Top-1 buy delta)",
        description="Top-1 buy-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[4500, -1500, 0],
    )
    ddiff1: float = Field(
        default=0.0,
        title="매도비율1 (Top-1 sell ratio)",
        description="Top-1 sell-side aggregate volume share (%) of total trading. Decimal scale not declared in available source.",
        examples=[18.5],
    )
    sdiff1: float = Field(
        default=0.0,
        title="매수비율1 (Top-1 buy ratio)",
        description="Top-1 buy-side aggregate volume share (%) of total trading. Decimal scale not declared in available source.",
        examples=[17.2],
    )
    offerno2: str = Field(
        default="",
        title="매도증권사코드2 (Top-2 sell broker code)",
        description="Top-2 sell-side aggregate broker code.",
        examples=["006"],
    )
    bidno2: str = Field(
        default="",
        title="매수증권사코드2 (Top-2 buy broker code)",
        description="Top-2 buy-side aggregate broker code.",
        examples=["003"],
    )
    dvol2: int = Field(
        default=0,
        title="총매도수량2 (Top-2 sell aggregate quantity)",
        description="Top-2 sell-side aggregate volume in shares.",
        examples=[380000],
    )
    svol2: int = Field(
        default=0,
        title="총매수수량2 (Top-2 buy aggregate quantity)",
        description="Top-2 buy-side aggregate volume in shares.",
        examples=[360000],
    )
    dcha2: int = Field(
        default=0,
        title="매도증감2 (Top-2 sell delta)",
        description="Top-2 sell-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[3000, -1000, 0],
    )
    scha2: int = Field(
        default=0,
        title="매수증감2 (Top-2 buy delta)",
        description="Top-2 buy-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[2800, -900, 0],
    )
    ddiff2: float = Field(
        default=0.0,
        title="매도비율2 (Top-2 sell ratio)",
        description="Top-2 sell-side aggregate volume share (%) of total trading.",
        examples=[15.6],
    )
    sdiff2: float = Field(
        default=0.0,
        title="매수비율2 (Top-2 buy ratio)",
        description="Top-2 buy-side aggregate volume share (%) of total trading.",
        examples=[14.7],
    )
    offerno3: str = Field(
        default="",
        title="매도증권사코드3 (Top-3 sell broker code)",
        description="Top-3 sell-side aggregate broker code.",
        examples=["007"],
    )
    bidno3: str = Field(
        default="",
        title="매수증권사코드3 (Top-3 buy broker code)",
        description="Top-3 buy-side aggregate broker code.",
        examples=["006"],
    )
    dvol3: int = Field(
        default=0,
        title="총매도수량3 (Top-3 sell aggregate quantity)",
        description="Top-3 sell-side aggregate volume in shares.",
        examples=[310000],
    )
    svol3: int = Field(
        default=0,
        title="총매수수량3 (Top-3 buy aggregate quantity)",
        description="Top-3 buy-side aggregate volume in shares.",
        examples=[300000],
    )
    dcha3: int = Field(
        default=0,
        title="매도증감3 (Top-3 sell delta)",
        description="Top-3 sell-side aggregate delta vs. previous snapshot.",
        examples=[2200, -800, 0],
    )
    scha3: int = Field(
        default=0,
        title="매수증감3 (Top-3 buy delta)",
        description="Top-3 buy-side aggregate delta vs. previous snapshot.",
        examples=[2000, -700, 0],
    )
    ddiff3: float = Field(
        default=0.0,
        title="매도비율3 (Top-3 sell ratio)",
        description="Top-3 sell-side aggregate volume share (%).",
        examples=[12.7],
    )
    sdiff3: float = Field(
        default=0.0,
        title="매수비율3 (Top-3 buy ratio)",
        description="Top-3 buy-side aggregate volume share (%).",
        examples=[12.3],
    )
    offerno4: str = Field(
        default="",
        title="매도증권사코드4 (Top-4 sell broker code)",
        description="Top-4 sell-side aggregate broker code.",
        examples=["008"],
    )
    bidno4: str = Field(
        default="",
        title="매수증권사코드4 (Top-4 buy broker code)",
        description="Top-4 buy-side aggregate broker code.",
        examples=["007"],
    )
    dvol4: int = Field(
        default=0,
        title="총매도수량4 (Top-4 sell aggregate quantity)",
        description="Top-4 sell-side aggregate volume in shares.",
        examples=[260000],
    )
    svol4: int = Field(
        default=0,
        title="총매수수량4 (Top-4 buy aggregate quantity)",
        description="Top-4 buy-side aggregate volume in shares.",
        examples=[250000],
    )
    dcha4: int = Field(
        default=0,
        title="매도증감4 (Top-4 sell delta)",
        description="Top-4 sell-side aggregate delta vs. previous snapshot.",
        examples=[1500, -600, 0],
    )
    scha4: int = Field(
        default=0,
        title="매수증감4 (Top-4 buy delta)",
        description="Top-4 buy-side aggregate delta vs. previous snapshot.",
        examples=[1400, -500, 0],
    )
    ddiff4: float = Field(
        default=0.0,
        title="매도비율4 (Top-4 sell ratio)",
        description="Top-4 sell-side aggregate volume share (%).",
        examples=[10.6],
    )
    sdiff4: float = Field(
        default=0.0,
        title="매수비율4 (Top-4 buy ratio)",
        description="Top-4 buy-side aggregate volume share (%).",
        examples=[10.2],
    )
    offerno5: str = Field(
        default="",
        title="매도증권사코드5 (Top-5 sell broker code)",
        description="Top-5 sell-side aggregate broker code.",
        examples=["050"],
    )
    bidno5: str = Field(
        default="",
        title="매수증권사코드5 (Top-5 buy broker code)",
        description="Top-5 buy-side aggregate broker code.",
        examples=["008"],
    )
    dvol5: int = Field(
        default=0,
        title="총매도수량5 (Top-5 sell aggregate quantity)",
        description="Top-5 sell-side aggregate volume in shares.",
        examples=[210000],
    )
    svol5: int = Field(
        default=0,
        title="총매수수량5 (Top-5 buy aggregate quantity)",
        description="Top-5 buy-side aggregate volume in shares.",
        examples=[200000],
    )
    dcha5: int = Field(
        default=0,
        title="매도증감5 (Top-5 sell delta)",
        description="Top-5 sell-side aggregate delta vs. previous snapshot.",
        examples=[1000, -400, 0],
    )
    scha5: int = Field(
        default=0,
        title="매수증감5 (Top-5 buy delta)",
        description="Top-5 buy-side aggregate delta vs. previous snapshot.",
        examples=[950, -350, 0],
    )
    ddiff5: float = Field(
        default=0.0,
        title="매도비율5 (Top-5 sell ratio)",
        description="Top-5 sell-side aggregate volume share (%).",
        examples=[8.6],
    )
    sdiff5: float = Field(
        default=0.0,
        title="매수비율5 (Top-5 buy ratio)",
        description="Top-5 buy-side aggregate volume share (%).",
        examples=[8.2],
    )
    fwdvl: int = Field(
        default=0,
        title="외국계매도합계수량 (Foreign-broker aggregate sell quantity)",
        description="Aggregate sell-side volume by foreign brokers.",
        examples=[1200000],
    )
    ftradmdcha: int = Field(
        default=0,
        title="외국계매도직전대비 (Foreign-broker sell delta)",
        description="Foreign-broker sell-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[8000, -3000, 0],
    )
    ftradmddiff: float = Field(
        default=0.0,
        title="외국계매도비율 (Foreign-broker sell ratio)",
        description="Foreign-broker sell-side aggregate volume share (%) of total trading.",
        examples=[48.5],
    )
    fwsvl: int = Field(
        default=0,
        title="외국계매수합계수량 (Foreign-broker aggregate buy quantity)",
        description="Aggregate buy-side volume by foreign brokers.",
        examples=[1150000],
    )
    ftradmscha: int = Field(
        default=0,
        title="외국계매수직전대비 (Foreign-broker buy delta)",
        description="Foreign-broker buy-side aggregate delta vs. previous snapshot. Sign convention not declared in available source.",
        examples=[7000, -2500, 0],
    )
    ftradmsdiff: float = Field(
        default=0.0,
        title="외국계매수비율 (Foreign-broker buy ratio)",
        description="Foreign-broker buy-side aggregate volume share (%) of total trading.",
        examples=[46.7],
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
        title="참고지수현재가 (Reference index current value)",
        description="Reference index current value. Decimal scale not declared in available source.",
        examples=[375.42],
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
    etftotcap: int = Field(
        default=0,
        title="순자산총액(억원) (ETF NAV total / 100M KRW)",
        description=(
            "Total ETF net asset value in 억원 (100-million KRW units) per "
            "the LS source label. Always 0 for non-ETF / ETN issues."
        ),
        examples=[45000],
    )
    spread: float = Field(
        default=0.0,
        title="스프레드 (Spread)",
        description="Bid-ask spread metric. Definition / scale not declared in available source.",
        examples=[0.05],
    )
    leverage: int = Field(
        default=0,
        title="레버리지 (Leverage flag)",
        description=(
            "Leverage classification flag. Code values not declared in "
            "available source; consume as returned by LS."
        ),
        examples=[0, 1, 2],
    )
    taxgubun: str = Field(
        default="",
        title="과세구분 (Tax classification)",
        description=(
            "Tax classification code. Code values not declared in available "
            "source; consume as returned by LS."
        ),
        examples=[""],
    )
    opcom_nmk: str = Field(
        default="",
        title="운용사 (Management company)",
        description="Asset-management company name (운용사).",
        examples=["삼성자산운용"],
    )
    lp_nm1: str = Field(
        default="",
        title="LP1 (Liquidity provider 1)",
        description="Top-1 Liquidity Provider name. Empty when no LP is assigned.",
        examples=["미래에셋증권"],
    )
    lp_nm2: str = Field(
        default="",
        title="LP2 (Liquidity provider 2)",
        description="Top-2 Liquidity Provider name. Empty when fewer than 2 LPs assigned.",
        examples=["NH투자증권"],
    )
    lp_nm3: str = Field(
        default="",
        title="LP3 (Liquidity provider 3)",
        description="Top-3 Liquidity Provider name. Empty when fewer than 3 LPs assigned.",
        examples=["KB증권"],
    )
    lp_nm4: str = Field(
        default="",
        title="LP4 (Liquidity provider 4)",
        description="Top-4 Liquidity Provider name. Empty when fewer than 4 LPs assigned.",
        examples=["삼성증권"],
    )
    lp_nm5: str = Field(
        default="",
        title="LP5 (Liquidity provider 5)",
        description="Top-5 Liquidity Provider name. Empty when fewer than 5 LPs assigned.",
        examples=["한국투자증권"],
    )
    etf_cp: str = Field(
        default="",
        title="복제방법 (Replication method)",
        description=(
            "ETF replication method classification (e.g., physical / "
            "synthetic). Code values not declared in available source; "
            "consume as returned by LS."
        ),
        examples=[""],
    )
    etf_kind: str = Field(
        default="",
        title="상품유형(Filler) (Product type / filler)",
        description=(
            "Product-type filler. Source label notes this as a filler "
            "field; code values not declared in available source."
        ),
        examples=[""],
    )
    vi_gubun: str = Field(
        default="",
        title="VI발동해제 (Volatility-interruption activation flag)",
        description=(
            "Volatility Interruption (VI) activation / release flag. "
            "Code values not declared in available source; consume as "
            "returned by LS."
        ),
        examples=[""],
    )
    etn_kind_cd: str = Field(
        default="",
        title="ETN상품분류 (ETN product class)",
        description=(
            "ETN product classification code. Populated only for ETN "
            "issues; empty for ETF issues. Code values not declared in "
            "available source."
        ),
        examples=[""],
    )
    lastymd: str = Field(
        default="",
        title="ETN만기일 (ETN maturity date)",
        description="ETN maturity date in 'YYYYMMDD' format. Empty for ETF issues.",
        examples=[""],
    )
    payday: str = Field(
        default="",
        title="ETN지급일 (ETN payment date)",
        description="ETN settlement / payment date in 'YYYYMMDD' format. Empty for ETF issues.",
        examples=[""],
    )
    lastdate: str = Field(
        default="",
        title="ETN최종거래일 (ETN final-trading date)",
        description="ETN final-trading date in 'YYYYMMDD' format. Empty for ETF issues.",
        examples=[""],
    )
    issuernmk: str = Field(
        default="",
        title="ETN발행시장참가자 (ETN issuer / market participant)",
        description="ETN issuer / market participant name. Empty for ETF issues.",
        examples=[""],
    )
    last_sdate: str = Field(
        default="",
        title="ETN만기상환가격결정시작일 (ETN maturity redemption-price determination start date)",
        description="ETN maturity redemption-price determination start date in 'YYYYMMDD' format. Empty for ETF issues.",
        examples=[""],
    )
    last_edate: str = Field(
        default="",
        title="ETN만기상환가격결정종료일 (ETN maturity redemption-price determination end date)",
        description="ETN maturity redemption-price determination end date in 'YYYYMMDD' format. Empty for ETF issues.",
        examples=[""],
    )
    lp_holdvol: str = Field(
        default="",
        title="ETNLP보유수량 (ETN LP held quantity)",
        description=(
            "ETN Liquidity Provider held quantity. Source returns this as "
            "string per the model definition. Empty for ETF issues."
        ),
        examples=[""],
    )
    listdate: str = Field(
        default="",
        title="상장일 (Listing date)",
        description="Issue listing date in 'YYYYMMDD' format.",
        examples=["20021014"],
    )
    etp_gb: str = Field(
        default="",
        title="ETP상품구분코드 (ETP product type code)",
        description=(
            "ETP (Exchange-Traded Product) product-type code. Code values "
            "not declared in available source; consume as returned by LS."
        ),
        examples=[""],
    )
    etn_elback_yn: str = Field(
        default="",
        title="ETN조기상환가능여부 (ETN early-redemption flag)",
        description=(
            "ETN early-redemption availability flag. Empty for ETF issues. "
            "Code values not declared in available source."
        ),
        examples=[""],
    )
    settletype: str = Field(
        default="",
        title="최종결제 (Final-settlement type)",
        description=(
            "Final settlement type. Code values not declared in available "
            "source; consume as returned by LS."
        ),
        examples=[""],
    )
    idx_asset_class1: str = Field(
        default="",
        title="지수자산분류코드(대분류) (Index asset-class major code)",
        description=(
            "Index asset-class major-classification code. Code values not "
            "declared in available source."
        ),
        examples=[""],
    )
    ty_text: str = Field(
        default="",
        title="ETF/ETN투자유의 (ETF / ETN investment caution)",
        description="ETF / ETN investment-caution / advisory text. Empty when no advisory applies.",
        examples=[""],
    )
    leverage2: float = Field(
        default=0.0,
        title="추적수익률배수 (Tracking-return multiplier)",
        description=(
            "Tracking-return multiplier (e.g., 1.0 = 1x, 2.0 = 2x leveraged, "
            "-1.0 = inverse). Decimal scale not declared in available source."
        ),
        examples=[1.0, 2.0, -1.0],
    )


class T1901Request(BaseModel):
    """t1901 request envelope."""

    header: T1901RequestHeader = T1901RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1901",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1901Response(BaseModel):
    """t1901 response envelope."""

    header: Optional[T1901ResponseHeader] = None
    block: Optional[T1901OutBlock] = None
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1901RequestHeader",
    "T1901ResponseHeader",
    "T1901InBlock",
    "T1901OutBlock",
    "T1901Request",
    "T1901Response",
]
