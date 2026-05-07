"""Pydantic models for LS Securities OpenAPI t1102 (주식현재가(시세)조회 / current quote + fundamentals + broker flow).

t1102 returns a comprehensive current-quote view for a Korean stock symbol:
basic price/sign/volume, today's session OHLC + timing, 52-week and YTD
high/low, valuation indicators (PER/PBR/시가총액), top-5 broker buy/sell flow,
foreign-broker aggregate flow, two prior-quarter financial snapshots with
year-over-year deltas, supervision/restriction flags, VI metadata, SPAC /
liquidity / lending / ETF-ETN advisory flags, and NXT venue extras.

Use t1101 for a 10-level orderbook only (no fundamentals, no broker flow).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and the ``listing`` (천 단위) /
      ``capital`` (백만원) / ``total`` (억원) units mirror LS labels
      verbatim.
    - The 5-broker top-flow rows (``offernocd1..5`` / ``bidnocd1..5``) are
      kept as flat scalar fields (Phase 4d ETF pattern). Broker code →
      brokerage-name resolution and 매도/매수 sign convention are NOT
      declared in the available source.
    - ``info1`` ~ ``info5`` advisory free-text labels and ``janginfo`` /
      ``alloc_gubun`` / ``low_lqdt_gu`` / ``abnormal_rise_gu`` / ``lend_text``
      / ``ty_text`` / ``spac_gubun`` flag value sets per LS source labels
      where declared, else "consume as returned by LS".
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1102RequestHeader(BlockRequestHeader):
    """t1102 request header. Inherits the standard LS request header schema."""
    pass


class T1102ResponseHeader(BlockResponseHeader):
    """t1102 response header. Inherits the standard LS response header schema."""
    pass


class T1102InBlock(BaseModel):
    """t1102InBlock — input block for the comprehensive current quote query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified. Other values are treated as KRX per LS source.",
        examples=["K", "N", "U"],
    )


class T1102Request(BaseModel):
    """t1102 request envelope."""

    header: T1102RequestHeader = T1102RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1102",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1102InBlock"], T1102InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1102"
    )


class T1102OutBlock(BaseModel):
    """t1102OutBlock — comprehensive current-quote block.

    Decimal scale, currency unit, and broker-code resolution are NOT
    declared in the source available to this codebase; consume as returned
    by LS. Unit hints in field titles ('백만원', '천 단위', '억원') mirror
    LS Korean source labels verbatim.
    """

    hname: str = Field(..., title="한글 종목명 (Korean name)", description="Korean issue name.", examples=["삼성전자"])
    price: int = Field(..., title="현재가 (Current price)", description="Current price for the issue.", examples=[79800])
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention. '1' = upper limit, '2' = up, '3' = unchanged, '4' = lower limit, '5' = down.",
        examples=["2", "3", "5"],
    )
    change: int = Field(..., title="전일대비 (Previous-day delta)", description="Magnitude of price change versus previous close (unsigned absolute value).", examples=[800, 0])
    diff: float = Field(..., title="등락율 (Change percent)", description="Percent change versus previous close.", examples=[1.02, 0.0, -0.5])
    volume: int = Field(..., title="누적거래량 (Cumulative volume)", description="Cumulative traded volume in shares for the session.", examples=[15000000])
    recprice: int = Field(..., title="기준가(평가가격) (Reference price)", description="Reference (evaluation) price for the issue.", examples=[79000])
    avg: int = Field(..., title="가중평균가 (Weighted average price)", description="Weighted average traded price.", examples=[79500])
    uplmtprice: int = Field(..., title="상한가(최고호가가격) (Upper limit price)", description="Daily upper price limit (highest quotable price).", examples=[102700])
    dnlmtprice: int = Field(..., title="하한가(최저호가가격) (Lower limit price)", description="Daily lower price limit (lowest quotable price).", examples=[55300])
    jnilvolume: int = Field(..., title="전일거래량 (Previous-day volume)", description="Previous trading day's cumulative volume in shares.", examples=[12000000])
    volumediff: int = Field(..., title="거래량차 (Volume difference)", description="Volume difference (today - previous-day same-time). Sign convention not declared in available source.", examples=[100000, 0, -50000])
    open: int = Field(..., title="시가 (Open)", description="Today's opening price.", examples=[79100])
    opentime: str = Field(..., title="시가시간 (Open time)", description="Time of the opening trade in 'HHMMSS' format.", examples=["090015"])
    high: int = Field(..., title="고가 (High)", description="Today's high price as of response time.", examples=[80000])
    hightime: str = Field(..., title="고가시간 (High time)", description="Time of the high in 'HHMMSS' format.", examples=["104500"])
    low: int = Field(..., title="저가 (Low)", description="Today's low price as of response time.", examples=[78900])
    lowtime: str = Field(..., title="저가시간 (Low time)", description="Time of the low in 'HHMMSS' format.", examples=["131200"])
    high52w: int = Field(..., title="52주 최고가 (52-week high)", description="52-week trailing high price.", examples=[88000])
    high52wdate: str = Field(..., title="52주 최고가일 (52-week high date)", description="Date of the 52-week high in 'YYYYMMDD' format.", examples=["20260115"])
    low52w: int = Field(..., title="52주 최저가 (52-week low)", description="52-week trailing low price.", examples=[68000])
    low52wdate: str = Field(..., title="52주 최저가일 (52-week low date)", description="Date of the 52-week low in 'YYYYMMDD' format.", examples=["20260801"])
    exhratio: float = Field(..., title="소진율 (Exhaust ratio percent)", description="Trading volume exhaust ratio (%) per LS source. Formula not declared in available source.", examples=[12.5])
    per: float = Field(..., title="PER (Price-earnings ratio)", description="Price-to-earnings ratio.", examples=[15.32])
    pbrx: float = Field(..., title="PBR (Price-book ratio)", description="Price-to-book ratio.", examples=[1.45])
    listing: int = Field(..., title="상장주식수 (천 단위) (Listed shares, thousands)", description="Listed share count in thousands of shares per LS source label '천 단위'.", examples=[5969783])
    jkrate: int = Field(..., title="증거금율 (Margin requirement percent)", description="Margin requirement (%) for trading the issue.", examples=[40])
    memedan: str = Field(..., title="수량단위 (Quantity unit)", description="Quantity unit / lot size per LS source. Format not declared in available source.", examples=["1"])
    offernocd1: str = Field(..., title="매도증권사코드1 (Top sell broker code 1)", description="Top sell-side broker code rank 1. Code-to-name mapping not declared in available source.", examples=["006"])
    offerno1: str = Field(..., title="매도증권사명1 (Top sell broker name 1)", description="Top sell-side broker display name rank 1.", examples=["미래에셋"])
    dvol1: int = Field(..., title="총매도수량1 (Total sell quantity rank 1)", description="Total sell-side quantity for the rank-1 broker.", examples=[150000])
    dcha1: int = Field(..., title="매도증감1 (Sell delta rank 1)", description="Change in sell-side quantity versus the previous tick. Sign convention not declared in available source.", examples=[1000, 0, -500])
    ddiff1: float = Field(..., title="매도비율1 (Sell ratio rank 1, %)", description="Sell-side share-of-flow percent for the rank-1 broker.", examples=[12.5])
    dval1: int = Field(..., title="총매도대금1 (백만원) (Total sell value rank 1, millions)", description="Total sell-side traded value in millions of KRW per LS source label '백만원'.", examples=[12000])
    davg1: int = Field(..., title="총매도평단가1 (Sell avg price rank 1)", description="Average sell-side traded price for the rank-1 broker.", examples=[79750])
    offernocd2: str = Field(..., title="매도증권사코드2 (Top sell broker code 2)", description="Top sell-side broker code rank 2.", examples=["005"])
    offerno2: str = Field(..., title="매도증권사명2 (Top sell broker name 2)", description="Top sell-side broker display name rank 2.", examples=["삼성"])
    dvol2: int = Field(..., title="총매도수량2 (Total sell quantity rank 2)", description="Total sell-side quantity for the rank-2 broker.", examples=[120000])
    dcha2: int = Field(..., title="매도증감2 (Sell delta rank 2)", description="Change in sell-side quantity versus the previous tick.", examples=[1000, 0, -500])
    ddiff2: float = Field(..., title="매도비율2 (Sell ratio rank 2, %)", description="Sell-side share-of-flow percent for the rank-2 broker.", examples=[10.0])
    dval2: int = Field(..., title="총매도대금2 (백만원) (Total sell value rank 2, millions)", description="Total sell-side traded value in millions of KRW.", examples=[9600])
    davg2: int = Field(..., title="총매도평단가2 (Sell avg price rank 2)", description="Average sell-side traded price for the rank-2 broker.", examples=[79700])
    offernocd3: str = Field(..., title="매도증권사코드3 (Top sell broker code 3)", description="Top sell-side broker code rank 3.", examples=["003"])
    offerno3: str = Field(..., title="매도증권사명3 (Top sell broker name 3)", description="Top sell-side broker display name rank 3.", examples=["KB"])
    dvol3: int = Field(..., title="총매도수량3 (Total sell quantity rank 3)", description="Total sell-side quantity for the rank-3 broker.", examples=[100000])
    dcha3: int = Field(..., title="매도증감3 (Sell delta rank 3)", description="Change in sell-side quantity versus the previous tick.", examples=[1000, 0, -500])
    ddiff3: float = Field(..., title="매도비율3 (Sell ratio rank 3, %)", description="Sell-side share-of-flow percent for the rank-3 broker.", examples=[8.5])
    dval3: int = Field(..., title="총매도대금3 (백만원) (Total sell value rank 3, millions)", description="Total sell-side traded value in millions of KRW.", examples=[8000])
    davg3: int = Field(..., title="총매도평단가3 (Sell avg price rank 3)", description="Average sell-side traded price for the rank-3 broker.", examples=[79680])
    offernocd4: str = Field(..., title="매도증권사코드4 (Top sell broker code 4)", description="Top sell-side broker code rank 4.", examples=["015"])
    offerno4: str = Field(..., title="매도증권사명4 (Top sell broker name 4)", description="Top sell-side broker display name rank 4.", examples=["NH"])
    dvol4: int = Field(..., title="총매도수량4 (Total sell quantity rank 4)", description="Total sell-side quantity for the rank-4 broker.", examples=[80000])
    dcha4: int = Field(..., title="매도증감4 (Sell delta rank 4)", description="Change in sell-side quantity versus the previous tick.", examples=[1000, 0, -500])
    ddiff4: float = Field(..., title="매도비율4 (Sell ratio rank 4, %)", description="Sell-side share-of-flow percent for the rank-4 broker.", examples=[7.0])
    dval4: int = Field(..., title="총매도대금4 (백만원) (Total sell value rank 4, millions)", description="Total sell-side traded value in millions of KRW.", examples=[6400])
    davg4: int = Field(..., title="총매도평단가4 (Sell avg price rank 4)", description="Average sell-side traded price for the rank-4 broker.", examples=[79650])
    offernocd5: str = Field(..., title="매도증권사코드5 (Top sell broker code 5)", description="Top sell-side broker code rank 5.", examples=["010"])
    offerno5: str = Field(..., title="매도증권사명5 (Top sell broker name 5)", description="Top sell-side broker display name rank 5.", examples=["하나"])
    dvol5: int = Field(..., title="총매도수량5 (Total sell quantity rank 5)", description="Total sell-side quantity for the rank-5 broker.", examples=[60000])
    dcha5: int = Field(..., title="매도증감5 (Sell delta rank 5)", description="Change in sell-side quantity versus the previous tick.", examples=[1000, 0, -500])
    ddiff5: float = Field(..., title="매도비율5 (Sell ratio rank 5, %)", description="Sell-side share-of-flow percent for the rank-5 broker.", examples=[5.5])
    dval5: int = Field(..., title="총매도대금5 (백만원) (Total sell value rank 5, millions)", description="Total sell-side traded value in millions of KRW.", examples=[4800])
    davg5: int = Field(..., title="총매도평단가5 (Sell avg price rank 5)", description="Average sell-side traded price for the rank-5 broker.", examples=[79620])
    bidnocd1: str = Field(..., title="매수증권사코드1 (Top buy broker code 1)", description="Top buy-side broker code rank 1.", examples=["006"])
    bidno1: str = Field(..., title="매수증권사명1 (Top buy broker name 1)", description="Top buy-side broker display name rank 1.", examples=["미래에셋"])
    svol1: int = Field(..., title="총매수수량1 (Total buy quantity rank 1)", description="Total buy-side quantity for the rank-1 broker.", examples=[150000])
    scha1: int = Field(..., title="매수증감1 (Buy delta rank 1)", description="Change in buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    sdiff1: float = Field(..., title="매수비율1 (Buy ratio rank 1, %)", description="Buy-side share-of-flow percent for the rank-1 broker.", examples=[12.5])
    sval1: int = Field(..., title="총매수대금1 (백만원) (Total buy value rank 1, millions)", description="Total buy-side traded value in millions of KRW.", examples=[12000])
    savg1: int = Field(..., title="총매수평단가1 (Buy avg price rank 1)", description="Average buy-side traded price for the rank-1 broker.", examples=[79750])
    bidnocd2: str = Field(..., title="매수증권사코드2 (Top buy broker code 2)", description="Top buy-side broker code rank 2.", examples=["005"])
    bidno2: str = Field(..., title="매수증권사명2 (Top buy broker name 2)", description="Top buy-side broker display name rank 2.", examples=["삼성"])
    svol2: int = Field(..., title="총매수수량2 (Total buy quantity rank 2)", description="Total buy-side quantity for the rank-2 broker.", examples=[120000])
    scha2: int = Field(..., title="매수증감2 (Buy delta rank 2)", description="Change in buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    sdiff2: float = Field(..., title="매수비율2 (Buy ratio rank 2, %)", description="Buy-side share-of-flow percent for the rank-2 broker.", examples=[10.0])
    sval2: int = Field(..., title="총매수대금2 (백만원) (Total buy value rank 2, millions)", description="Total buy-side traded value in millions of KRW.", examples=[9600])
    savg2: int = Field(..., title="총매수평단가2 (Buy avg price rank 2)", description="Average buy-side traded price for the rank-2 broker.", examples=[79700])
    bidnocd3: str = Field(..., title="매수증권사코드3 (Top buy broker code 3)", description="Top buy-side broker code rank 3.", examples=["003"])
    bidno3: str = Field(..., title="매수증권사명3 (Top buy broker name 3)", description="Top buy-side broker display name rank 3.", examples=["KB"])
    svol3: int = Field(..., title="총매수수량3 (Total buy quantity rank 3)", description="Total buy-side quantity for the rank-3 broker.", examples=[100000])
    scha3: int = Field(..., title="매수증감3 (Buy delta rank 3)", description="Change in buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    sdiff3: float = Field(..., title="매수비율3 (Buy ratio rank 3, %)", description="Buy-side share-of-flow percent for the rank-3 broker.", examples=[8.5])
    sval3: int = Field(..., title="총매수대금3 (백만원) (Total buy value rank 3, millions)", description="Total buy-side traded value in millions of KRW.", examples=[8000])
    savg3: int = Field(..., title="총매수평단가3 (Buy avg price rank 3)", description="Average buy-side traded price for the rank-3 broker.", examples=[79680])
    bidnocd4: str = Field(..., title="매수증권사코드4 (Top buy broker code 4)", description="Top buy-side broker code rank 4.", examples=["015"])
    bidno4: str = Field(..., title="매수증권사명4 (Top buy broker name 4)", description="Top buy-side broker display name rank 4.", examples=["NH"])
    svol4: int = Field(..., title="총매수수량4 (Total buy quantity rank 4)", description="Total buy-side quantity for the rank-4 broker.", examples=[80000])
    scha4: int = Field(..., title="매수증감4 (Buy delta rank 4)", description="Change in buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    sdiff4: float = Field(..., title="매수비율4 (Buy ratio rank 4, %)", description="Buy-side share-of-flow percent for the rank-4 broker.", examples=[7.0])
    sval4: int = Field(..., title="총매수대금4 (백만원) (Total buy value rank 4, millions)", description="Total buy-side traded value in millions of KRW.", examples=[6400])
    savg4: int = Field(..., title="총매수평단가4 (Buy avg price rank 4)", description="Average buy-side traded price for the rank-4 broker.", examples=[79650])
    bidnocd5: str = Field(..., title="매수증권사코드5 (Top buy broker code 5)", description="Top buy-side broker code rank 5.", examples=["010"])
    bidno5: str = Field(..., title="매수증권사명5 (Top buy broker name 5)", description="Top buy-side broker display name rank 5.", examples=["하나"])
    svol5: int = Field(..., title="총매수수량5 (Total buy quantity rank 5)", description="Total buy-side quantity for the rank-5 broker.", examples=[60000])
    scha5: int = Field(..., title="매수증감5 (Buy delta rank 5)", description="Change in buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    sdiff5: float = Field(..., title="매수비율5 (Buy ratio rank 5, %)", description="Buy-side share-of-flow percent for the rank-5 broker.", examples=[5.5])
    sval5: int = Field(..., title="총매수대금5 (백만원) (Total buy value rank 5, millions)", description="Total buy-side traded value in millions of KRW.", examples=[4800])
    savg5: int = Field(..., title="총매수평단가5 (Buy avg price rank 5)", description="Average buy-side traded price for the rank-5 broker.", examples=[79620])
    fwdvl: int = Field(..., title="외국계 매도합계수량 (Foreign-broker total sell quantity)", description="Aggregate foreign-broker sell-side quantity.", examples=[500000])
    ftradmdcha: int = Field(..., title="외국계 매도 직전대비 (Foreign-broker sell delta)", description="Change in foreign-broker sell-side quantity versus the previous tick. Sign convention not declared in available source.", examples=[1000, 0, -500])
    ftradmddiff: float = Field(..., title="외국계 매도비율 (Foreign-broker sell ratio, %)", description="Foreign-broker sell-side share-of-flow percent.", examples=[35.5])
    ftradmdval: int = Field(..., title="외국계 매도대금 (Foreign-broker sell value)", description="Foreign-broker sell-side traded value. Decimal scale not declared in available source.", examples=[40000])
    ftradmdvag: int = Field(..., title="외국계 매도평단가 (Foreign-broker sell avg price)", description="Average foreign-broker sell-side traded price.", examples=[79700])
    fwsvl: int = Field(..., title="외국계 매수합계수량 (Foreign-broker total buy quantity)", description="Aggregate foreign-broker buy-side quantity.", examples=[500000])
    ftradmscha: int = Field(..., title="외국계 매수 직전대비 (Foreign-broker buy delta)", description="Change in foreign-broker buy-side quantity versus the previous tick.", examples=[1000, 0, -500])
    ftradmsdiff: float = Field(..., title="외국계 매수비율 (Foreign-broker buy ratio, %)", description="Foreign-broker buy-side share-of-flow percent.", examples=[35.5])
    ftradmsval: int = Field(..., title="외국계 매수대금 (Foreign-broker buy value)", description="Foreign-broker buy-side traded value.", examples=[40000])
    ftradmsvag: int = Field(..., title="외국계 매수평단가 (Foreign-broker buy avg price)", description="Average foreign-broker buy-side traded price.", examples=[79700])
    vol: float = Field(..., title="회전율 (Turnover ratio, %)", description="Share turnover ratio in percent.", examples=[0.45])
    shcode: str = Field(..., title="단축코드 (Short code)", description="6-digit Korean stock short code echoed for the issue.", examples=["005930"])
    value: int = Field(..., title="누적거래대금 (백만원) (Cumulative trade value, millions)", description="Cumulative traded value in millions of KRW per LS source label '백만원'.", examples=[1185000])
    jvolume: int = Field(..., title="전일동시간거래량 (Previous-day same-time volume)", description="Previous trading day's volume at the same intraday time-of-day. Comparison time alignment not declared in available source.", examples=[12000000])
    highyear: int = Field(..., title="연중최고가 (YTD high)", description="Year-to-date high price.", examples=[88000])
    highyeardate: str = Field(..., title="연중최고일자 (YTD high date)", description="Date of the YTD high in 'YYYYMMDD' format.", examples=["20260115"])
    lowyear: int = Field(..., title="연중최저가 (YTD low)", description="Year-to-date low price.", examples=[68000])
    lowyeardate: str = Field(..., title="연중최저일자 (YTD low date)", description="Date of the YTD low in 'YYYYMMDD' format.", examples=["20260315"])
    target: int = Field(..., title="목표가 (Target price)", description="Analyst target price (LS-aggregated). 0 when not available.", examples=[0, 95000])
    capital: int = Field(..., title="자본금 (백만원) (Capital, millions)", description="Issued capital in millions of KRW per LS source label '백만원'.", examples=[778047])
    abscnt: int = Field(..., title="유동주식수 (천 단위) (Float shares, thousands)", description="Free-float share count in thousands of shares per LS source label '천 단위'.", examples=[4500000])
    parprice: int = Field(..., title="액면가 (Par value)", description="Per-share par (face) value.", examples=[100])
    gsmm: str = Field(..., title="결산월 (Fiscal close month)", description="Fiscal year-end month in 'MM' format.", examples=["12"])
    subprice: int = Field(..., title="대용가 (Substitute price)", description="Substitute (collateral) reference price.", examples=[63800])
    total: int = Field(..., title="시가총액 (억원) (Market cap, hundred-millions)", description="Market capitalization in 100-millions of KRW (억원) per LS source label.", examples=[4762000])
    listdate: str = Field(..., title="상장일 (Listing date)", description="Listing date in 'YYYYMMDD' format.", examples=["19750611"])
    name: str = Field(..., title="전분기명 (Prior-quarter label)", description="Display label of the prior fiscal quarter (e.g., '2403 1분기').", examples=["2403 1분기"])
    bfsales: int = Field(..., title="전분기 매출액 (억원) (Prior-quarter revenue, hundred-millions)", description="Prior fiscal quarter revenue in 억원.", examples=[710000])
    bfoperatingincome: int = Field(..., title="전분기 영업이익 (억원) (Prior-quarter operating income, hundred-millions)", description="Prior fiscal quarter operating income in 억원.", examples=[66000])
    bfordinaryincome: int = Field(..., title="전분기 경상이익 (억원) (Prior-quarter ordinary income, hundred-millions)", description="Prior fiscal quarter ordinary income in 억원.", examples=[66000])
    bfnetincome: int = Field(..., title="전분기 순이익 (억원) (Prior-quarter net income, hundred-millions)", description="Prior fiscal quarter net income in 억원.", examples=[60000])
    bfeps: float = Field(..., title="전분기 EPS (Prior-quarter EPS)", description="Prior fiscal quarter earnings per share.", examples=[850.5])
    name2: str = Field(..., title="전전분기명 (Two-quarters-ago label)", description="Display label of the quarter two periods prior (e.g., '2312 결산').", examples=["2312 결산"])
    bfsales2: int = Field(..., title="전전분기 매출액 (억원) (Two-quarters-ago revenue, hundred-millions)", description="Revenue two fiscal quarters prior in 억원.", examples=[670000])
    bfoperatingincome2: int = Field(..., title="전전분기 영업이익 (억원) (Two-quarters-ago operating income, hundred-millions)", description="Operating income two fiscal quarters prior in 억원.", examples=[60000])
    bfordinaryincome2: int = Field(..., title="전전분기 경상이익 (억원) (Two-quarters-ago ordinary income, hundred-millions)", description="Ordinary income two fiscal quarters prior in 억원.", examples=[60000])
    bfnetincome2: int = Field(..., title="전전분기 순이익 (억원) (Two-quarters-ago net income, hundred-millions)", description="Net income two fiscal quarters prior in 억원.", examples=[55000])
    bfeps2: float = Field(..., title="전전분기 EPS (Two-quarters-ago EPS)", description="EPS two fiscal quarters prior.", examples=[800.0])
    salert: float = Field(..., title="전년대비 매출액 증감율 (Revenue YoY percent)", description="Year-over-year change in revenue (%).", examples=[5.2, 0.0, -3.1])
    opert: float = Field(..., title="전년대비 영업이익 증감율 (Operating income YoY percent)", description="Year-over-year change in operating income (%).", examples=[10.0, 0.0, -5.0])
    ordrt: float = Field(..., title="전년대비 경상이익 증감율 (Ordinary income YoY percent)", description="Year-over-year change in ordinary income (%).", examples=[10.0, 0.0, -5.0])
    netrt: float = Field(..., title="전년대비 순이익 증감율 (Net income YoY percent)", description="Year-over-year change in net income (%).", examples=[12.5, 0.0, -3.0])
    epsrt: float = Field(..., title="전년대비 EPS 증감율 (EPS YoY percent)", description="Year-over-year change in EPS (%).", examples=[6.3, 0.0, -2.5])
    info1: str = Field(..., title="락구분 (Ex-rights flag)", description="Ex-rights / split / merger flag (권배락 / 권리락 / 배당락 / 액면분할 / 액면병합 / 감자 등). Empty when none.", examples=["", "권리락"])
    info2: str = Field(..., title="관리/급등구분 (Administrative / surge flag)", description="Administrative supervision / overheating flag (관리 / 경고 / 위험 / 예고 등). Empty when none.", examples=["", "관리"])
    info3: str = Field(..., title="정지/연장구분 (Halt / extension flag)", description="Trading halt / extension flag (거래정지 / 거래중단 / 시가연장 / 종가연장). Empty when none.", examples=["", "거래정지"])
    info4: str = Field(..., title="투자/불성실구분 (Investment caution flag)", description="Investment-caution / disclosure-violation flag. Value set per LS source where declared.", examples=["", "불성실공시"])
    info5: str = Field(..., title="투자주의환기 (Investment alert flag)", description="Investment-alert flag. Empty when none.", examples=["", "투자환기"])
    janginfo: str = Field(..., title="장구분 (Market segment)", description="Market segment label (KOSPI / KOSPI200 / KOSDAQ / KOSDAQ50 / CB 등).", examples=["KOSPI200"])
    t_per: float = Field(..., title="T.PER (Trailing PER)", description="Trailing 12-month price-to-earnings ratio.", examples=[14.85])
    tonghwa: str = Field(..., title="통화ISO코드 (ISO currency code)", description="ISO 4217 currency code for the issue.", examples=["KRW"])
    shterm_text: str = Field(..., title="단기과열/VI발동 (Short-term overheat / VI trigger)", description="Short-term overheating or VI trigger advisory text. Empty when none.", examples=["", "단기과열지정"])
    svi_uplmtprice: int = Field(..., title="정적VI 상한가 (Static VI upper limit)", description="Static volatility-interruption upper-limit price.", examples=[87000])
    svi_dnlmtprice: int = Field(..., title="정적VI 하한가 (Static VI lower limit)", description="Static volatility-interruption lower-limit price.", examples=[71000])
    spac_gubun: str = Field(..., title="기업인수목적회사(SPAC) 여부 (SPAC flag)", description="SPAC flag. 'Y' = SPAC, 'N' = not SPAC.", examples=["N", "Y"])
    issueprice: int = Field(..., title="발행가격 (Issue price)", description="Issue (offering) price.", examples=[5000])
    alloc_gubun: str = Field(..., title="배분적용구분코드 (Allocation flag code)", description="Allocation-application flag code. '1' = allocation triggered (배분발생), '2' = allocation released (배분해제), other = none per LS source.", examples=["", "1", "2"])
    alloc_text: str = Field(..., title="배분적용구분 텍스트 (Allocation flag text)", description="Allocation-application flag display text.", examples=[""])
    low_lqdt_gu: str = Field(..., title="저유동성종목여부 (Low-liquidity flag)", description="Low-liquidity flag. '0' = no, '1' = low-liquidity issue per LS source.", examples=["0", "1"])
    abnormal_rise_gu: str = Field(..., title="이상급등종목여부 (Abnormal-surge flag)", description="Abnormal-surge flag. '0' = no, '1' = abnormal-surge issue per LS source.", examples=["0", "1"])
    lend_text: str = Field(..., title="대차불가표시 (Lending-restricted text)", description="Lending-restriction display text. Empty when lending available; '대차불가' when restricted.", examples=["", "대차불가"])
    ty_text: str = Field(..., title="ETF/ETN투자유의 (ETF/ETN advisory text)", description="ETF / ETN investment-advisory display text. Empty when none; '투자유의' when applicable.", examples=["", "투자유의"])
    nxt_janginfo: str = Field(default="", title="NXT 장구분 (NXT market segment)", description="NXT market segment label. Empty when not applicable.", examples=[""])
    nxt_shterm_text: str = Field(default="", title="NXT 단기과열/VI발동 (NXT short-term overheat / VI trigger)", description="NXT short-term overheating or VI trigger advisory text.", examples=[""])
    nxt_svi_uplmtprice: int = Field(default=0, title="NXT 정적VI 상한가 (NXT static VI upper limit)", description="NXT static volatility-interruption upper-limit price.", examples=[0, 87000])
    nxt_svi_dnlmtprice: int = Field(default=0, title="NXT 정적VI 하한가 (NXT static VI lower limit)", description="NXT static volatility-interruption lower-limit price.", examples=[0, 71000])
    ex_shcode: str = Field(default="", title="거래소별 단축코드 (Exchange-specific short code)", description="Exchange-resolved short code echoed for the issue. Format not declared in available source.", examples=[""])


class T1102Response(BaseModel):
    """t1102 response envelope."""

    header: Optional[T1102ResponseHeader]
    block: Optional[T1102OutBlock] = Field(
        None,
        title="시세 데이터 (Comprehensive quote block)",
        description="Comprehensive current-quote block with fundamentals, broker flow, financials, and supervision flags.",
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
