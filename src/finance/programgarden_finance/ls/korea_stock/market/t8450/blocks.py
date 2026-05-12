"""Pydantic models for LS Securities OpenAPI t8450 (주식현재가호가조회2 / unified KRX+NXT+통합 orderbook).

t8450 returns a 10-level orderbook for a Korean stock symbol with KRX, NXT,
and unified (통합) sub-blocks side-by-side. The KRX side carries best bid/ask
prices, quantities, expected-cross fields, and after-hours queue depth; the
NXT and 통합 sides carry best-quantity-only views (NXT prices are not
provided in this TR — use realtime NH1 / NVI for NXT prices). KRX and NXT
midpoint metadata is also exposed.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English; Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, ``hotime`` format, and the meaning of
      the unprefixed ``offerho{i}`` / ``bidho{i}`` price levels (KRX-only
      vs. KRX+NXT consolidated) are NOT declared explicitly in the
      available source; consume as returned by LS.
    - ``ho_status`` codes for KRX and NXT are not enumerated in the
      available source for this TR; treat as opaque LS-defined codes.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8450RequestHeader(BlockRequestHeader):
    """t8450 request header. Inherits the standard LS request header schema."""
    pass


class T8450ResponseHeader(BlockResponseHeader):
    """t8450 response header. Inherits the standard LS response header schema."""
    pass


class T8450InBlock(BaseModel):
    """t8450InBlock — input block for the unified KRX+NXT+통합 orderbook query."""

    shcode: str = Field(
        ...,
        title="단축코드 (Short code)",
        description="6-digit Korean stock short code.",
        examples=["005930"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division. 'K' = KRX, 'N' = NXT, 'U' = unified. Pydantic validates strictly — only 'K', 'N', 'U' are accepted; empty string and other values are rejected. Omit the field to use the 'K' default.",
        examples=["K", "N", "U"],
    )


class T8450Request(BaseModel):
    """t8450 request envelope."""

    header: T8450RequestHeader = T8450RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8450",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t8450InBlock"], T8450InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8450"
    )


class T8450OutBlock(BaseModel):
    """t8450OutBlock — orderbook block with KRX 10-level + NXT/통합 quantity-only sub-blocks.

    Decimal scale, currency unit, and ``hotime`` format are NOT declared in
    the source available to this codebase; consume as returned by LS.
    """

    hname: str = Field(..., title="한글명 (Korean name)", description="Korean issue name.", examples=["삼성전자"])
    price: int = Field(..., title="현재가 (Current price)", description="Current price for the issue.", examples=[79800])
    sign: str = Field(
        ...,
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention. '1' = upper limit, '2' = up, '3' = unchanged, '4' = lower limit, '5' = down.",
        examples=["2", "3", "5"],
    )
    change: int = Field(..., title="전일대비 (Previous-day delta)", description="Magnitude of price change versus previous close.", examples=[800, 0])
    diff: float = Field(..., title="등락율 (Change percent)", description="Percent change versus previous close.", examples=[1.02, 0.0, -0.5])
    volume: int = Field(..., title="누적거래량 (Cumulative volume)", description="Cumulative traded volume in shares for the session.", examples=[15000000])
    jnilclose: int = Field(..., title="전일종가(기준가) (Previous close / reference)", description="Previous trading day's closing price (reference price).", examples=[79000])
    offerho1: int = Field(..., title="매도호가1 (Ask price 1)", description="Ask price at level 1 (best). Venue scope (KRX-only vs. consolidated) not declared explicitly.", examples=[79900])
    bidho1: int = Field(..., title="매수호가1 (Bid price 1)", description="Bid price at level 1.", examples=[79800])
    offerrem1: int = Field(..., title="매도호가수량1 (Ask quantity 1)", description="Resting quantity at ask level 1.", examples=[5000])
    bidrem1: int = Field(..., title="매수호가수량1 (Bid quantity 1)", description="Resting quantity at bid level 1.", examples=[3500])
    offerho2: int = Field(..., title="매도호가2 (Ask price 2)", description="Ask price at level 2.", examples=[80000])
    bidho2: int = Field(..., title="매수호가2 (Bid price 2)", description="Bid price at level 2.", examples=[79700])
    offerrem2: int = Field(..., title="매도호가수량2 (Ask quantity 2)", description="Resting quantity at ask level 2.", examples=[4000])
    bidrem2: int = Field(..., title="매수호가수량2 (Bid quantity 2)", description="Resting quantity at bid level 2.", examples=[3000])
    offerho3: int = Field(..., title="매도호가3 (Ask price 3)", description="Ask price at level 3.", examples=[80100])
    bidho3: int = Field(..., title="매수호가3 (Bid price 3)", description="Bid price at level 3.", examples=[79600])
    offerrem3: int = Field(..., title="매도호가수량3 (Ask quantity 3)", description="Resting quantity at ask level 3.", examples=[3500])
    bidrem3: int = Field(..., title="매수호가수량3 (Bid quantity 3)", description="Resting quantity at bid level 3.", examples=[2800])
    offerho4: int = Field(..., title="매도호가4 (Ask price 4)", description="Ask price at level 4.", examples=[80200])
    bidho4: int = Field(..., title="매수호가4 (Bid price 4)", description="Bid price at level 4.", examples=[79500])
    offerrem4: int = Field(..., title="매도호가수량4 (Ask quantity 4)", description="Resting quantity at ask level 4.", examples=[3000])
    bidrem4: int = Field(..., title="매수호가수량4 (Bid quantity 4)", description="Resting quantity at bid level 4.", examples=[2500])
    offerho5: int = Field(..., title="매도호가5 (Ask price 5)", description="Ask price at level 5.", examples=[80300])
    bidho5: int = Field(..., title="매수호가5 (Bid price 5)", description="Bid price at level 5.", examples=[79400])
    offerrem5: int = Field(..., title="매도호가수량5 (Ask quantity 5)", description="Resting quantity at ask level 5.", examples=[2500])
    bidrem5: int = Field(..., title="매수호가수량5 (Bid quantity 5)", description="Resting quantity at bid level 5.", examples=[2000])
    offerho6: int = Field(..., title="매도호가6 (Ask price 6)", description="Ask price at level 6.", examples=[80400])
    bidho6: int = Field(..., title="매수호가6 (Bid price 6)", description="Bid price at level 6.", examples=[79300])
    offerrem6: int = Field(..., title="매도호가수량6 (Ask quantity 6)", description="Resting quantity at ask level 6.", examples=[2000])
    bidrem6: int = Field(..., title="매수호가수량6 (Bid quantity 6)", description="Resting quantity at bid level 6.", examples=[1800])
    offerho7: int = Field(..., title="매도호가7 (Ask price 7)", description="Ask price at level 7.", examples=[80500])
    bidho7: int = Field(..., title="매수호가7 (Bid price 7)", description="Bid price at level 7.", examples=[79200])
    offerrem7: int = Field(..., title="매도호가수량7 (Ask quantity 7)", description="Resting quantity at ask level 7.", examples=[1800])
    bidrem7: int = Field(..., title="매수호가수량7 (Bid quantity 7)", description="Resting quantity at bid level 7.", examples=[1500])
    offerho8: int = Field(..., title="매도호가8 (Ask price 8)", description="Ask price at level 8.", examples=[80600])
    bidho8: int = Field(..., title="매수호가8 (Bid price 8)", description="Bid price at level 8.", examples=[79100])
    offerrem8: int = Field(..., title="매도호가수량8 (Ask quantity 8)", description="Resting quantity at ask level 8.", examples=[1500])
    bidrem8: int = Field(..., title="매수호가수량8 (Bid quantity 8)", description="Resting quantity at bid level 8.", examples=[1200])
    offerho9: int = Field(..., title="매도호가9 (Ask price 9)", description="Ask price at level 9.", examples=[80700])
    bidho9: int = Field(..., title="매수호가9 (Bid price 9)", description="Bid price at level 9.", examples=[79000])
    offerrem9: int = Field(..., title="매도호가수량9 (Ask quantity 9)", description="Resting quantity at ask level 9.", examples=[1200])
    bidrem9: int = Field(..., title="매수호가수량9 (Bid quantity 9)", description="Resting quantity at bid level 9.", examples=[1000])
    offerho10: int = Field(..., title="매도호가10 (Ask price 10)", description="Ask price at level 10.", examples=[80800])
    bidho10: int = Field(..., title="매수호가10 (Bid price 10)", description="Bid price at level 10.", examples=[78900])
    offerrem10: int = Field(..., title="매도호가수량10 (Ask quantity 10)", description="Resting quantity at ask level 10.", examples=[1000])
    bidrem10: int = Field(..., title="매수호가수량10 (Bid quantity 10)", description="Resting quantity at bid level 10.", examples=[800])
    offer: int = Field(..., title="매도호가수량합 (Total ask quantity)", description="Aggregate ask-side resting quantity across the visible levels.", examples=[27500])
    bid: int = Field(..., title="매수호가수량합 (Total bid quantity)", description="Aggregate bid-side resting quantity across the visible levels.", examples=[20100])
    hotime: str = Field(..., title="수신시간 (Receive time)", description="Time the orderbook snapshot was received. Format not declared in available source.", examples=["153012"])
    yeprice: int = Field(..., title="예상체결가격 (Expected cross price)", description="Expected cross price during single-price auction windows.", examples=[0, 79850])
    yevolume: int = Field(..., title="예상체결수량 (Expected cross quantity)", description="Expected cross quantity during single-price auction windows.", examples=[0, 15000])
    yesign: str = Field(..., title="예상체결전일구분 (Expected cross direction)", description="Direction code for the expected cross price ('1'..'5' per LS).", examples=["2", "3", "5"])
    yechange: int = Field(..., title="예상체결전일대비 (Expected cross delta)", description="Magnitude of expected-cross delta versus previous close.", examples=[0, 850])
    yediff: float = Field(..., title="예상체결등락율 (Expected cross percent change)", description="Percent change of the expected cross versus previous close.", examples=[0.0, 1.08])
    tmoffer: int = Field(..., title="시간외매도잔량 (After-hours ask quantity)", description="Aggregate after-hours ask-side queue depth in shares.", examples=[0, 50000])
    tmbid: int = Field(..., title="시간외매수잔량 (After-hours bid quantity)", description="Aggregate after-hours bid-side queue depth in shares.", examples=[0, 50000])
    ho_status: str = Field(
        ...,
        title="동시구분 (Auction phase code)",
        description="Auction phase code. Code values not declared in available source for this TR; consume as returned by LS.",
        examples=["1", "2", "3"],
    )
    shcode: str = Field(..., title="단축코드 (Short code)", description="6-digit Korean stock short code echoed for the issue.", examples=["005930"])
    uplmtprice: int = Field(..., title="상한가 (Upper limit price)", description="Daily upper price limit for the issue.", examples=[102700])
    dnlmtprice: int = Field(..., title="하한가 (Lower limit price)", description="Daily lower price limit for the issue.", examples=[55300])
    open: int = Field(..., title="시가 (Open)", description="Today's opening price.", examples=[79100])
    high: int = Field(..., title="고가 (High)", description="Today's high price as of response time.", examples=[80000])
    low: int = Field(..., title="저가 (Low)", description="Today's low price as of response time.", examples=[78900])
    nxt_offerrem1: int = Field(default=0, title="NXT매도호가수량1 (NXT ask quantity 1)", description="NXT ask-side resting quantity at level 1. NXT prices are not exposed in this TR.", examples=[0, 1000])
    nxt_bidrem1: int = Field(default=0, title="NXT매수호가수량1 (NXT bid quantity 1)", description="NXT bid-side resting quantity at level 1.", examples=[0, 1000])
    nxt_offerrem2: int = Field(default=0, title="NXT매도호가수량2 (NXT ask quantity 2)", description="NXT ask-side resting quantity at level 2.", examples=[0, 800])
    nxt_bidrem2: int = Field(default=0, title="NXT매수호가수량2 (NXT bid quantity 2)", description="NXT bid-side resting quantity at level 2.", examples=[0, 800])
    nxt_offerrem3: int = Field(default=0, title="NXT매도호가수량3 (NXT ask quantity 3)", description="NXT ask-side resting quantity at level 3.", examples=[0, 600])
    nxt_bidrem3: int = Field(default=0, title="NXT매수호가수량3 (NXT bid quantity 3)", description="NXT bid-side resting quantity at level 3.", examples=[0, 600])
    nxt_offerrem4: int = Field(default=0, title="NXT매도호가수량4 (NXT ask quantity 4)", description="NXT ask-side resting quantity at level 4.", examples=[0, 500])
    nxt_bidrem4: int = Field(default=0, title="NXT매수호가수량4 (NXT bid quantity 4)", description="NXT bid-side resting quantity at level 4.", examples=[0, 500])
    nxt_offerrem5: int = Field(default=0, title="NXT매도호가수량5 (NXT ask quantity 5)", description="NXT ask-side resting quantity at level 5.", examples=[0, 400])
    nxt_bidrem5: int = Field(default=0, title="NXT매수호가수량5 (NXT bid quantity 5)", description="NXT bid-side resting quantity at level 5.", examples=[0, 400])
    nxt_offerrem6: int = Field(default=0, title="NXT매도호가수량6 (NXT ask quantity 6)", description="NXT ask-side resting quantity at level 6.", examples=[0, 300])
    nxt_bidrem6: int = Field(default=0, title="NXT매수호가수량6 (NXT bid quantity 6)", description="NXT bid-side resting quantity at level 6.", examples=[0, 300])
    nxt_offerrem7: int = Field(default=0, title="NXT매도호가수량7 (NXT ask quantity 7)", description="NXT ask-side resting quantity at level 7.", examples=[0, 200])
    nxt_bidrem7: int = Field(default=0, title="NXT매수호가수량7 (NXT bid quantity 7)", description="NXT bid-side resting quantity at level 7.", examples=[0, 200])
    nxt_offerrem8: int = Field(default=0, title="NXT매도호가수량8 (NXT ask quantity 8)", description="NXT ask-side resting quantity at level 8.", examples=[0, 150])
    nxt_bidrem8: int = Field(default=0, title="NXT매수호가수량8 (NXT bid quantity 8)", description="NXT bid-side resting quantity at level 8.", examples=[0, 150])
    nxt_offerrem9: int = Field(default=0, title="NXT매도호가수량9 (NXT ask quantity 9)", description="NXT ask-side resting quantity at level 9.", examples=[0, 100])
    nxt_bidrem9: int = Field(default=0, title="NXT매수호가수량9 (NXT bid quantity 9)", description="NXT bid-side resting quantity at level 9.", examples=[0, 100])
    nxt_offerrem10: int = Field(default=0, title="NXT매도호가수량10 (NXT ask quantity 10)", description="NXT ask-side resting quantity at level 10.", examples=[0, 80])
    nxt_bidrem10: int = Field(default=0, title="NXT매수호가수량10 (NXT bid quantity 10)", description="NXT bid-side resting quantity at level 10.", examples=[0, 80])
    nxt_offer: int = Field(default=0, title="NXT매도호가수량합 (NXT total ask quantity)", description="Aggregate NXT ask-side resting quantity across the visible levels.", examples=[0, 5000])
    nxt_bid: int = Field(default=0, title="NXT매수호가수량합 (NXT total bid quantity)", description="Aggregate NXT bid-side resting quantity across the visible levels.", examples=[0, 5000])
    nxt_yeprice: int = Field(default=0, title="NXT예상체결가격 (NXT expected cross price)", description="NXT expected cross price during auction windows.", examples=[0, 79850])
    nxt_yevolume: int = Field(default=0, title="NXT예상체결수량 (NXT expected cross quantity)", description="NXT expected cross quantity during auction windows.", examples=[0, 1000])
    nxt_yesign: str = Field(default="", title="NXT예상체결전일구분 (NXT expected cross direction)", description="Direction code for the NXT expected cross price ('1'..'5' per LS). Empty when not in auction.", examples=["", "2", "5"])
    nxt_yechange: int = Field(default=0, title="NXT예상체결전일대비 (NXT expected cross delta)", description="Magnitude of NXT expected-cross delta versus previous close.", examples=[0, 850])
    nxt_yediff: float = Field(default=0.0, title="NXT예상체결등락율 (NXT expected cross percent change)", description="Percent change of the NXT expected cross versus previous close.", examples=[0.0, 1.08])
    nxt_ho_status: str = Field(default="", title="NXT동시구분 (NXT auction phase code)", description="NXT auction phase code. Code values not declared in available source.", examples=["", "1", "2"])
    unx_offerrem1: int = Field(default=0, title="통합매도호가수량1 (Unified ask quantity 1)", description="Unified (KRX+NXT) ask-side resting quantity at level 1.", examples=[0, 6000])
    unx_bidrem1: int = Field(default=0, title="통합매수호가수량1 (Unified bid quantity 1)", description="Unified (KRX+NXT) bid-side resting quantity at level 1.", examples=[0, 4500])
    unx_offerrem2: int = Field(default=0, title="통합매도호가수량2 (Unified ask quantity 2)", description="Unified ask-side resting quantity at level 2.", examples=[0, 5000])
    unx_bidrem2: int = Field(default=0, title="통합매수호가수량2 (Unified bid quantity 2)", description="Unified bid-side resting quantity at level 2.", examples=[0, 4000])
    unx_offerrem3: int = Field(default=0, title="통합매도호가수량3 (Unified ask quantity 3)", description="Unified ask-side resting quantity at level 3.", examples=[0, 4000])
    unx_bidrem3: int = Field(default=0, title="통합매수호가수량3 (Unified bid quantity 3)", description="Unified bid-side resting quantity at level 3.", examples=[0, 3500])
    unx_offerrem4: int = Field(default=0, title="통합매도호가수량4 (Unified ask quantity 4)", description="Unified ask-side resting quantity at level 4.", examples=[0, 3500])
    unx_bidrem4: int = Field(default=0, title="통합매수호가수량4 (Unified bid quantity 4)", description="Unified bid-side resting quantity at level 4.", examples=[0, 3000])
    unx_offerrem5: int = Field(default=0, title="통합매도호가수량5 (Unified ask quantity 5)", description="Unified ask-side resting quantity at level 5.", examples=[0, 2900])
    unx_bidrem5: int = Field(default=0, title="통합매수호가수량5 (Unified bid quantity 5)", description="Unified bid-side resting quantity at level 5.", examples=[0, 2400])
    unx_offerrem6: int = Field(default=0, title="통합매도호가수량6 (Unified ask quantity 6)", description="Unified ask-side resting quantity at level 6.", examples=[0, 2300])
    unx_bidrem6: int = Field(default=0, title="통합매수호가수량6 (Unified bid quantity 6)", description="Unified bid-side resting quantity at level 6.", examples=[0, 2100])
    unx_offerrem7: int = Field(default=0, title="통합매도호가수량7 (Unified ask quantity 7)", description="Unified ask-side resting quantity at level 7.", examples=[0, 2000])
    unx_bidrem7: int = Field(default=0, title="통합매수호가수량7 (Unified bid quantity 7)", description="Unified bid-side resting quantity at level 7.", examples=[0, 1700])
    unx_offerrem8: int = Field(default=0, title="통합매도호가수량8 (Unified ask quantity 8)", description="Unified ask-side resting quantity at level 8.", examples=[0, 1650])
    unx_bidrem8: int = Field(default=0, title="통합매수호가수량8 (Unified bid quantity 8)", description="Unified bid-side resting quantity at level 8.", examples=[0, 1350])
    unx_offerrem9: int = Field(default=0, title="통합매도호가수량9 (Unified ask quantity 9)", description="Unified ask-side resting quantity at level 9.", examples=[0, 1300])
    unx_bidrem9: int = Field(default=0, title="통합매수호가수량9 (Unified bid quantity 9)", description="Unified bid-side resting quantity at level 9.", examples=[0, 1100])
    unx_offerrem10: int = Field(default=0, title="통합매도호가수량10 (Unified ask quantity 10)", description="Unified ask-side resting quantity at level 10.", examples=[0, 1080])
    unx_bidrem10: int = Field(default=0, title="통합매수호가수량10 (Unified bid quantity 10)", description="Unified bid-side resting quantity at level 10.", examples=[0, 880])
    unx_offer: int = Field(default=0, title="통합매도호가수량합 (Unified total ask quantity)", description="Aggregate unified ask-side resting quantity across the visible levels.", examples=[0, 32500])
    unx_bid: int = Field(default=0, title="통합매수호가수량합 (Unified total bid quantity)", description="Aggregate unified bid-side resting quantity across the visible levels.", examples=[0, 25100])
    krx_midprice: int = Field(default=0, title="KRX중간가격 (KRX mid price)", description="KRX midpoint reference price. Specific definition not declared in available source.", examples=[0, 79850])
    krx_offermidsumrem: int = Field(default=0, title="KRX매도중간가잔량합계수량 (KRX ask-side midpoint quantity)", description="Aggregate KRX midpoint ask-side resting quantity.", examples=[0, 5000])
    krx_bidmidsumrem: int = Field(default=0, title="KRX매수중간가잔량합계수량 (KRX bid-side midpoint quantity)", description="Aggregate KRX midpoint bid-side resting quantity.", examples=[0, 5000])
    nxt_midprice: int = Field(default=0, title="NXT중간가격 (NXT mid price)", description="NXT midpoint reference price. Specific definition not declared in available source.", examples=[0, 79850])
    nxt_offermidsumrem: int = Field(default=0, title="NXT매도중간가잔량합계수량 (NXT ask-side midpoint quantity)", description="Aggregate NXT midpoint ask-side resting quantity.", examples=[0, 1000])
    nxt_bidmidsumrem: int = Field(default=0, title="NXT매수중간가잔량합계수량 (NXT bid-side midpoint quantity)", description="Aggregate NXT midpoint bid-side resting quantity.", examples=[0, 1000])
    ex_shcode: str = Field(default="", title="거래소별단축코드 (Exchange-specific short code)", description="Exchange-resolved short code for the issue. Format not declared in available source.", examples=[""])
    krx_midsumrem: int = Field(default=0, title="KRX중간가잔량합계수량 (KRX total midpoint quantity)", description="Aggregate KRX midpoint resting quantity (combined sides).", examples=[0, 10000])
    krx_midsumremgubun: str = Field(default="", title="KRX중간가잔량구분 (KRX midpoint side flag)", description="KRX midpoint side flag. '' = none, '1' = sell, '2' = buy per LS source.", examples=["", "1", "2"])
    nxt_midsumrem: int = Field(default=0, title="NXT중간가잔량합계수량 (NXT total midpoint quantity)", description="Aggregate NXT midpoint resting quantity (combined sides).", examples=[0, 2000])
    nxt_midsumremgubun: str = Field(default="", title="NXT중간가잔량구분 (NXT midpoint side flag)", description="NXT midpoint side flag. '' = none, '1' = sell, '2' = buy per LS source.", examples=["", "1", "2"])


class T8450Response(BaseModel):
    """t8450 response envelope."""

    header: Optional[T8450ResponseHeader]
    block: Optional[T8450OutBlock] = Field(
        None,
        title="호가 데이터 (Orderbook block)",
        description="Unified KRX + NXT + 통합 orderbook snapshot for the queried issue.",
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
