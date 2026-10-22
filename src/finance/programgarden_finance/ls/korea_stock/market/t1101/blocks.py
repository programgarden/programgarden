"""Pydantic models for LS Securities OpenAPI t1101 (주식현재가호가조회 / 10-level orderbook).

t1101 returns the 10-level orderbook (best ask / bid prices, quantities, and
prior-tick deltas) for a Korean stock symbol along with current price, sign,
session OHLC, expected-cross fields, after-hours queue depth, and KRX mid-
price metadata. Use t1102 for fundamentals + broker-flow + financials, or
t8450 for the unified KRX/NXT 10-level orderbook with NXT/통합 sub-blocks.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and ``hotime`` format are NOT declared
      in the source available to this codebase; consume as returned by LS.
    - The ``preoffercha{i}`` / ``prebidcha{i}`` 10-level prior-tick delta
      fields are LS-source-declared but their sign convention is NOT;
      treat as a magnitude paired with implicit sign per LS convention.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1101RequestHeader(BlockRequestHeader):
    """t1101 request header. Inherits the standard LS request header schema."""
    pass


class T1101ResponseHeader(BlockResponseHeader):
    """t1101 response header. Inherits the standard LS response header schema."""
    pass


class T1101InBlock(BaseModel):
    """t1101InBlock — input block for the 10-level orderbook query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )


class T1101Request(BaseModel):
    """t1101 request envelope."""

    header: T1101RequestHeader = T1101RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1101",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1101InBlock"], T1101InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1101"
    )


class T1101OutBlock(BaseModel):
    """t1101OutBlock — 10-level orderbook + current-price snapshot for the issue.

    Decimal scale and currency unit are NOT declared in the source available
    to this codebase; consume as returned by LS.
    """

    hname: str = Field(
        ...,
        title="한글명 (Korean name)",
        description="Korean issue name as reported by LS.",
        examples=["삼성전자"],
    )
    price: int = Field(
        ...,
        title="현재가 (Current price)",
        description="Current price for the issue.",
        examples=[79800],
    )
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description=(
            "Direction code per LS convention. '1' = upper limit (상한), "
            "'2' = up (상승), '3' = unchanged (보합), '4' = lower limit "
            "(하한), '5' = down (하락)."
        ),
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
        title="등락율 (Change percent)",
        description="Percent change versus previous close.",
        examples=[1.02, 0.0, -0.5],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative traded volume in shares for the session.",
        examples=[15000000],
    )
    jnilclose: int = Field(
        ...,
        title="전일종가(기준가) (Previous close / reference price)",
        description="Previous trading day's closing price (reference price for daily limits).",
        examples=[79000],
    )
    offerho1: int = Field(..., title="매도호가1 (Ask price 1)", description="Ask price at level 1 (best).", examples=[79900])
    bidho1: int = Field(..., title="매수호가1 (Bid price 1)", description="Bid price at level 1 (best).", examples=[79800])
    offerrem1: int = Field(..., title="매도호가수량1 (Ask quantity 1)", description="Resting quantity at ask level 1.", examples=[5000])
    bidrem1: int = Field(..., title="매수호가수량1 (Bid quantity 1)", description="Resting quantity at bid level 1.", examples=[3500])
    preoffercha1: int = Field(..., title="직전매도대비수량1 (Ask delta 1)", description="Quantity change at ask level 1 versus the previous tick. Sign convention not declared in available source.", examples=[100, 0, -50])
    prebidcha1: int = Field(..., title="직전매수대비수량1 (Bid delta 1)", description="Quantity change at bid level 1 versus the previous tick.", examples=[200, 0, -75])
    offerho2: int = Field(..., title="매도호가2 (Ask price 2)", description="Ask price at level 2.", examples=[80000])
    bidho2: int = Field(..., title="매수호가2 (Bid price 2)", description="Bid price at level 2.", examples=[79700])
    offerrem2: int = Field(..., title="매도호가수량2 (Ask quantity 2)", description="Resting quantity at ask level 2.", examples=[4000])
    bidrem2: int = Field(..., title="매수호가수량2 (Bid quantity 2)", description="Resting quantity at bid level 2.", examples=[3000])
    preoffercha2: int = Field(..., title="직전매도대비수량2 (Ask delta 2)", description="Quantity change at ask level 2 versus the previous tick.", examples=[0, 100, -50])
    prebidcha2: int = Field(..., title="직전매수대비수량2 (Bid delta 2)", description="Quantity change at bid level 2 versus the previous tick.", examples=[0, 200, -75])
    offerho3: int = Field(..., title="매도호가3 (Ask price 3)", description="Ask price at level 3.", examples=[80100])
    bidho3: int = Field(..., title="매수호가3 (Bid price 3)", description="Bid price at level 3.", examples=[79600])
    offerrem3: int = Field(..., title="매도호가수량3 (Ask quantity 3)", description="Resting quantity at ask level 3.", examples=[3500])
    bidrem3: int = Field(..., title="매수호가수량3 (Bid quantity 3)", description="Resting quantity at bid level 3.", examples=[2800])
    preoffercha3: int = Field(..., title="직전매도대비수량3 (Ask delta 3)", description="Quantity change at ask level 3 versus the previous tick.", examples=[0, 100, -50])
    prebidcha3: int = Field(..., title="직전매수대비수량3 (Bid delta 3)", description="Quantity change at bid level 3 versus the previous tick.", examples=[0, 200, -75])
    offerho4: int = Field(..., title="매도호가4 (Ask price 4)", description="Ask price at level 4.", examples=[80200])
    bidho4: int = Field(..., title="매수호가4 (Bid price 4)", description="Bid price at level 4.", examples=[79500])
    offerrem4: int = Field(..., title="매도호가수량4 (Ask quantity 4)", description="Resting quantity at ask level 4.", examples=[3000])
    bidrem4: int = Field(..., title="매수호가수량4 (Bid quantity 4)", description="Resting quantity at bid level 4.", examples=[2500])
    preoffercha4: int = Field(..., title="직전매도대비수량4 (Ask delta 4)", description="Quantity change at ask level 4 versus the previous tick.", examples=[0, 100, -50])
    prebidcha4: int = Field(..., title="직전매수대비수량4 (Bid delta 4)", description="Quantity change at bid level 4 versus the previous tick.", examples=[0, 200, -75])
    offerho5: int = Field(..., title="매도호가5 (Ask price 5)", description="Ask price at level 5.", examples=[80300])
    bidho5: int = Field(..., title="매수호가5 (Bid price 5)", description="Bid price at level 5.", examples=[79400])
    offerrem5: int = Field(..., title="매도호가수량5 (Ask quantity 5)", description="Resting quantity at ask level 5.", examples=[2500])
    bidrem5: int = Field(..., title="매수호가수량5 (Bid quantity 5)", description="Resting quantity at bid level 5.", examples=[2000])
    preoffercha5: int = Field(..., title="직전매도대비수량5 (Ask delta 5)", description="Quantity change at ask level 5 versus the previous tick.", examples=[0, 100, -50])
    prebidcha5: int = Field(..., title="직전매수대비수량5 (Bid delta 5)", description="Quantity change at bid level 5 versus the previous tick.", examples=[0, 200, -75])
    offerho6: int = Field(..., title="매도호가6 (Ask price 6)", description="Ask price at level 6.", examples=[80400])
    bidho6: int = Field(..., title="매수호가6 (Bid price 6)", description="Bid price at level 6.", examples=[79300])
    offerrem6: int = Field(..., title="매도호가수량6 (Ask quantity 6)", description="Resting quantity at ask level 6.", examples=[2000])
    bidrem6: int = Field(..., title="매수호가수량6 (Bid quantity 6)", description="Resting quantity at bid level 6.", examples=[1800])
    preoffercha6: int = Field(..., title="직전매도대비수량6 (Ask delta 6)", description="Quantity change at ask level 6 versus the previous tick.", examples=[0, 100, -50])
    prebidcha6: int = Field(..., title="직전매수대비수량6 (Bid delta 6)", description="Quantity change at bid level 6 versus the previous tick.", examples=[0, 200, -75])
    offerho7: int = Field(..., title="매도호가7 (Ask price 7)", description="Ask price at level 7.", examples=[80500])
    bidho7: int = Field(..., title="매수호가7 (Bid price 7)", description="Bid price at level 7.", examples=[79200])
    offerrem7: int = Field(..., title="매도호가수량7 (Ask quantity 7)", description="Resting quantity at ask level 7.", examples=[1800])
    bidrem7: int = Field(..., title="매수호가수량7 (Bid quantity 7)", description="Resting quantity at bid level 7.", examples=[1500])
    preoffercha7: int = Field(..., title="직전매도대비수량7 (Ask delta 7)", description="Quantity change at ask level 7 versus the previous tick.", examples=[0, 100, -50])
    prebidcha7: int = Field(..., title="직전매수대비수량7 (Bid delta 7)", description="Quantity change at bid level 7 versus the previous tick.", examples=[0, 200, -75])
    offerho8: int = Field(..., title="매도호가8 (Ask price 8)", description="Ask price at level 8.", examples=[80600])
    bidho8: int = Field(..., title="매수호가8 (Bid price 8)", description="Bid price at level 8.", examples=[79100])
    offerrem8: int = Field(..., title="매도호가수량8 (Ask quantity 8)", description="Resting quantity at ask level 8.", examples=[1500])
    bidrem8: int = Field(..., title="매수호가수량8 (Bid quantity 8)", description="Resting quantity at bid level 8.", examples=[1200])
    preoffercha8: int = Field(..., title="직전매도대비수량8 (Ask delta 8)", description="Quantity change at ask level 8 versus the previous tick.", examples=[0, 100, -50])
    prebidcha8: int = Field(..., title="직전매수대비수량8 (Bid delta 8)", description="Quantity change at bid level 8 versus the previous tick.", examples=[0, 200, -75])
    offerho9: int = Field(..., title="매도호가9 (Ask price 9)", description="Ask price at level 9.", examples=[80700])
    bidho9: int = Field(..., title="매수호가9 (Bid price 9)", description="Bid price at level 9.", examples=[79000])
    offerrem9: int = Field(..., title="매도호가수량9 (Ask quantity 9)", description="Resting quantity at ask level 9.", examples=[1200])
    bidrem9: int = Field(..., title="매수호가수량9 (Bid quantity 9)", description="Resting quantity at bid level 9.", examples=[1000])
    preoffercha9: int = Field(..., title="직전매도대비수량9 (Ask delta 9)", description="Quantity change at ask level 9 versus the previous tick.", examples=[0, 100, -50])
    prebidcha9: int = Field(..., title="직전매수대비수량9 (Bid delta 9)", description="Quantity change at bid level 9 versus the previous tick.", examples=[0, 200, -75])
    offerho10: int = Field(..., title="매도호가10 (Ask price 10)", description="Ask price at level 10.", examples=[80800])
    bidho10: int = Field(..., title="매수호가10 (Bid price 10)", description="Bid price at level 10.", examples=[78900])
    offerrem10: int = Field(..., title="매도호가수량10 (Ask quantity 10)", description="Resting quantity at ask level 10.", examples=[1000])
    bidrem10: int = Field(..., title="매수호가수량10 (Bid quantity 10)", description="Resting quantity at bid level 10.", examples=[800])
    preoffercha10: int = Field(..., title="직전매도대비수량10 (Ask delta 10)", description="Quantity change at ask level 10 versus the previous tick.", examples=[0, 100, -50])
    prebidcha10: int = Field(..., title="직전매수대비수량10 (Bid delta 10)", description="Quantity change at bid level 10 versus the previous tick.", examples=[0, 200, -75])
    offer: int = Field(
        ...,
        title="매도호가수량합 (Total ask quantity)",
        description="Aggregate ask-side resting quantity across all 10 visible levels.",
        examples=[27500],
    )
    bid: int = Field(
        ...,
        title="매수호가수량합 (Total bid quantity)",
        description="Aggregate bid-side resting quantity across all 10 visible levels.",
        examples=[20100],
    )
    preoffercha: int = Field(
        ...,
        title="직전매도대비수량합 (Total ask delta)",
        description="Aggregate change in ask-side quantity versus the previous tick. Sign convention not declared in available source.",
        examples=[0, 500, -200],
    )
    prebidcha: int = Field(
        ...,
        title="직전매수대비수량합 (Total bid delta)",
        description="Aggregate change in bid-side quantity versus the previous tick.",
        examples=[0, 500, -200],
    )
    hotime: str = Field(
        ...,
        title="수신시간 (Receive time)",
        description="Time the orderbook snapshot was received. Format not declared in available source; consume as returned by LS.",
        examples=["153012"],
    )
    yeprice: int = Field(
        ...,
        title="예상체결가격 (Expected cross price)",
        description="Expected cross price during single-price auction windows. 0 outside auction windows.",
        examples=[0, 79850],
    )
    yevolume: int = Field(
        ...,
        title="예상체결수량 (Expected cross quantity)",
        description="Expected cross quantity during single-price auction windows.",
        examples=[0, 15000],
    )
    yesign: str = Field(
        ...,
        title="예상체결전일구분 (Expected cross direction code)",
        description="Direction code for the expected cross price. '1' = upper limit, '2' = up, '3' = unchanged, '4' = lower limit, '5' = down per LS convention.",
        examples=["2", "3", "5"],
    )
    yechange: int = Field(
        ...,
        title="예상체결전일대비 (Expected cross delta)",
        description="Magnitude of expected-cross delta versus previous close.",
        examples=[0, 850],
    )
    yediff: float = Field(
        ...,
        title="예상체결등락율 (Expected cross percent change)",
        description="Percent change of the expected cross versus previous close.",
        examples=[0.0, 1.08],
    )
    tmoffer: int = Field(
        ...,
        title="시간외매도잔량 (After-hours ask quantity)",
        description="Aggregate after-hours ask-side queue depth in shares.",
        examples=[0, 50000],
    )
    tmbid: int = Field(
        ...,
        title="시간외매수잔량 (After-hours bid quantity)",
        description="Aggregate after-hours bid-side queue depth in shares.",
        examples=[0, 50000],
    )
    ho_status: str = Field(
        ...,
        title="동시구분 (Auction phase code)",
        description=(
            "Auction phase code per LS source. '1' = regular session "
            "(장중), '2' = after-hours (시간외), '3' = open / mid / close "
            "single-price auction (장전/장중/장마감 동시)."
        ),
        examples=["1", "2", "3"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code echoed for the issue.",
        examples=["005930"],
    )
    uplmtprice: int = Field(
        ...,
        title="상한가 (Upper limit price)",
        description="Daily upper price limit (상한가) for the issue.",
        examples=[102700],
    )
    dnlmtprice: int = Field(
        ...,
        title="하한가 (Lower limit price)",
        description="Daily lower price limit (하한가) for the issue.",
        examples=[55300],
    )
    open: int = Field(
        ...,
        title="시가 (Open)",
        description="Today's opening price.",
        examples=[79100],
    )
    high: int = Field(
        ...,
        title="고가 (High)",
        description="Today's high price as of response time.",
        examples=[80000],
    )
    low: int = Field(
        ...,
        title="저가 (Low)",
        description="Today's low price as of response time.",
        examples=[78900],
    )
    krx_midprice: int = Field(
        default=0,
        title="KRX중간가격 (KRX mid price)",
        description="KRX midpoint reference price. Specific definition not declared in available source; consume as returned by LS.",
        examples=[0, 79850],
    )
    krx_offermidsumrem: int = Field(
        default=0,
        title="KRX매도중간가잔량합계수량 (KRX ask-side midpoint quantity)",
        description="Aggregate KRX midpoint ask-side resting quantity.",
        examples=[0, 5000],
    )
    krx_bidmidsumrem: int = Field(
        default=0,
        title="KRX매수중간가잔량합계수량 (KRX bid-side midpoint quantity)",
        description="Aggregate KRX midpoint bid-side resting quantity.",
        examples=[0, 5000],
    )
    krx_midsumrem: int = Field(
        default=0,
        title="KRX중간가잔량합계수량 (KRX total midpoint quantity)",
        description="Aggregate KRX midpoint resting quantity (combined sides).",
        examples=[0, 10000],
    )
    krx_midsumremgubun: str = Field(
        default="",
        title="KRX중간가잔량구분 (KRX midpoint side flag)",
        description="KRX midpoint side flag. '' = none (없음), '1' = sell (매도), '2' = buy (매수) per LS source.",
        examples=["", "1", "2"],
    )


class T1101Response(BaseModel):
    """t1101 response envelope."""

    header: Optional[T1101ResponseHeader]
    block: Optional[T1101OutBlock] = Field(
        None,
        title="호가 데이터 (Orderbook block)",
        description="10-level orderbook snapshot for the queried issue.",
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
