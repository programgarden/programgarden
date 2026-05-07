"""Pydantic models for LS Securities OpenAPI NH1 (NXT 10-level orderbook).

NH1 is a Real-time WebSocket TR that pushes 10-level bid / ask orderbook
updates for NXT (Next Trading System)-listed stocks.  Field structure
mirrors H1_ / HA_ (KOSPI / KOSDAQ orderbook), with two key differences:

    1. Per-level price and quantity fields use ``int`` (Number in the API
       spec) rather than ``str``.
    2. ``tr_key`` is padded to 10 characters: ``'N'`` + 6-digit code +
       3 trailing spaces.
    3. ``ex_shcode`` exposes the exchange-prefixed short symbol code
       (e.g. ``'N000880'``) that does not appear in H1_ / HA_.

The ``NH1RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + padded ``tr_key``); the ``NH1RealResponseBody`` carries
the per-update orderbook push payload.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - ``donsigubun`` enum ('1'=장개시전 / '2'=장마감전 / '3'=장중 / '4'=장후)
      is preserved verbatim.
    - ``midsumremgubun`` enum (' '=없음 / '1'=매도 / '2'=매수) is preserved
      verbatim.
    - ``alloc_gubun`` (배분적용구분) and decimal scale of price values are
      NOT declared in the available source — consume as returned by LS.
    - ``examples`` for ``tr_key`` mirror the example script
      (``src/finance/example/korea_stock/real_NH1.py``).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class NH1RealRequestHeader(BlockRealRequestHeader):
    """NH1 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class NH1RealResponseHeader(BlockRealResponseHeader):
    """NH1 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class NH1RealRequestBody(BaseModel):
    """NH1RealRequestBody — WebSocket subscription envelope for NXT orderbook push."""

    tr_cd: str = Field(
        default="NH1",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'NH1'.",
        examples=["NH1"],
    )
    tr_key: str = Field(
        ...,
        max_length=10,
        title="단축코드 + padding ('N' + 6-digit code + 3 spaces)",
        description=(
            "Exchange-prefixed key combining 'N' + 6-digit short code, "
            "right-padded with spaces to 10 characters."
        ),
        examples=["N000880   ", "N005930   "],
    )

    @field_validator("tr_key", mode="before")
    def ensure_10_char_padding(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 10:
            return s.ljust(10)
        return s

    model_config = ConfigDict(validate_assignment=True)


class NH1RealRequest(BaseModel):
    """(NXT) 호가잔량(NH1) 실시간 시세 등록/해제 요청."""
    header: NH1RealRequestHeader = Field(
        NH1RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="NH1 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: NH1RealRequestBody = Field(
        NH1RealRequestBody(tr_cd="NH1", tr_key=""),
        title="요청 바디 (Request body)",
        description="NXT 호가잔량 실시간 등록에 필요한 종목코드 정보"
    )


class NH1RealResponseBody(BaseModel):
    """NH1RealResponseBody — NXT 10-level orderbook push payload (~52 fields, int prices/quantities)."""

    hotime: str = Field(
        ...,
        title="호가시간 (Orderbook time)",
        description="Orderbook receive time in HHMMSS format.",
        examples=["111244", "153000"],
    )
    offerho1: int = Field(
        ...,
        title="매도호가1 (Ask price — level 1)",
        description="Ask (sell) price at level 1.",
        examples=[73500],
    )
    bidho1: int = Field(
        ...,
        title="매수호가1 (Bid price — level 1)",
        description="Bid (buy) price at level 1.",
        examples=[73400],
    )
    offerrem1: int = Field(
        ...,
        title="매도호가잔량1 (Ask remaining quantity — level 1)",
        description="Ask remaining quantity at level 1.",
        examples=[1234],
    )
    bidrem1: int = Field(
        ...,
        title="매수호가잔량1 (Bid remaining quantity — level 1)",
        description="Bid remaining quantity at level 1.",
        examples=[2345],
    )
    offerho2: int = Field(..., title="매도호가2 (Ask price — level 2)", description="Ask price at level 2.", examples=[73600])
    bidho2: int = Field(..., title="매수호가2 (Bid price — level 2)", description="Bid price at level 2.", examples=[73300])
    offerrem2: int = Field(..., title="매도호가잔량2 (Ask remaining quantity — level 2)", description="Ask remaining quantity at level 2.", examples=[1500])
    bidrem2: int = Field(..., title="매수호가잔량2 (Bid remaining quantity — level 2)", description="Bid remaining quantity at level 2.", examples=[2500])
    offerho3: int = Field(..., title="매도호가3 (Ask price — level 3)", description="Ask price at level 3.", examples=[73700])
    bidho3: int = Field(..., title="매수호가3 (Bid price — level 3)", description="Bid price at level 3.", examples=[73200])
    offerrem3: int = Field(..., title="매도호가잔량3 (Ask remaining quantity — level 3)", description="Ask remaining quantity at level 3.", examples=[800])
    bidrem3: int = Field(..., title="매수호가잔량3 (Bid remaining quantity — level 3)", description="Bid remaining quantity at level 3.", examples=[1100])
    offerho4: int = Field(..., title="매도호가4 (Ask price — level 4)", description="Ask price at level 4.", examples=[73800])
    bidho4: int = Field(..., title="매수호가4 (Bid price — level 4)", description="Bid price at level 4.", examples=[73100])
    offerrem4: int = Field(..., title="매도호가잔량4 (Ask remaining quantity — level 4)", description="Ask remaining quantity at level 4.", examples=[650])
    bidrem4: int = Field(..., title="매수호가잔량4 (Bid remaining quantity — level 4)", description="Bid remaining quantity at level 4.", examples=[900])
    offerho5: int = Field(..., title="매도호가5 (Ask price — level 5)", description="Ask price at level 5.", examples=[73900])
    bidho5: int = Field(..., title="매수호가5 (Bid price — level 5)", description="Bid price at level 5.", examples=[73000])
    offerrem5: int = Field(..., title="매도호가잔량5 (Ask remaining quantity — level 5)", description="Ask remaining quantity at level 5.", examples=[540])
    bidrem5: int = Field(..., title="매수호가잔량5 (Bid remaining quantity — level 5)", description="Bid remaining quantity at level 5.", examples=[780])
    offerho6: int = Field(..., title="매도호가6 (Ask price — level 6)", description="Ask price at level 6.", examples=[74000])
    bidho6: int = Field(..., title="매수호가6 (Bid price — level 6)", description="Bid price at level 6.", examples=[72900])
    offerrem6: int = Field(..., title="매도호가잔량6 (Ask remaining quantity — level 6)", description="Ask remaining quantity at level 6.", examples=[430])
    bidrem6: int = Field(..., title="매수호가잔량6 (Bid remaining quantity — level 6)", description="Bid remaining quantity at level 6.", examples=[620])
    offerho7: int = Field(..., title="매도호가7 (Ask price — level 7)", description="Ask price at level 7.", examples=[74100])
    bidho7: int = Field(..., title="매수호가7 (Bid price — level 7)", description="Bid price at level 7.", examples=[72800])
    offerrem7: int = Field(..., title="매도호가잔량7 (Ask remaining quantity — level 7)", description="Ask remaining quantity at level 7.", examples=[320])
    bidrem7: int = Field(..., title="매수호가잔량7 (Bid remaining quantity — level 7)", description="Bid remaining quantity at level 7.", examples=[510])
    offerho8: int = Field(..., title="매도호가8 (Ask price — level 8)", description="Ask price at level 8.", examples=[74200])
    bidho8: int = Field(..., title="매수호가8 (Bid price — level 8)", description="Bid price at level 8.", examples=[72700])
    offerrem8: int = Field(..., title="매도호가잔량8 (Ask remaining quantity — level 8)", description="Ask remaining quantity at level 8.", examples=[280])
    bidrem8: int = Field(..., title="매수호가잔량8 (Bid remaining quantity — level 8)", description="Bid remaining quantity at level 8.", examples=[410])
    offerho9: int = Field(..., title="매도호가9 (Ask price — level 9)", description="Ask price at level 9.", examples=[74300])
    bidho9: int = Field(..., title="매수호가9 (Bid price — level 9)", description="Bid price at level 9.", examples=[72600])
    offerrem9: int = Field(..., title="매도호가잔량9 (Ask remaining quantity — level 9)", description="Ask remaining quantity at level 9.", examples=[210])
    bidrem9: int = Field(..., title="매수호가잔량9 (Bid remaining quantity — level 9)", description="Bid remaining quantity at level 9.", examples=[330])
    offerho10: int = Field(..., title="매도호가10 (Ask price — level 10)", description="Ask price at level 10.", examples=[74400])
    bidho10: int = Field(..., title="매수호가10 (Bid price — level 10)", description="Bid price at level 10.", examples=[72500])
    offerrem10: int = Field(..., title="매도호가잔량10 (Ask remaining quantity — level 10)", description="Ask remaining quantity at level 10.", examples=[180])
    bidrem10: int = Field(..., title="매수호가잔량10 (Bid remaining quantity — level 10)", description="Bid remaining quantity at level 10.", examples=[260])
    totofferrem: int = Field(
        ...,
        title="총매도호가잔량 (Total ask remaining quantity)",
        description="Sum of ask remaining quantities across levels 1–10.",
        examples=[6234],
    )
    totbidrem: int = Field(
        ...,
        title="총매수호가잔량 (Total bid remaining quantity)",
        description="Sum of bid remaining quantities across levels 1–10.",
        examples=[9655],
    )
    donsigubun: str = Field(
        ...,
        title="동시호가구분 (Concurrent-quote phase code)",
        description=(
            "Concurrent-quote phase code. LS-source-declared values: "
            "'1'=장개시전 (pre-open), '2'=장마감전 (pre-close), "
            "'3'=장중 (intraday), '4'=장후 (post-close)."
        ),
        examples=["1", "2", "3", "4"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="NXT short symbol code (9 characters as returned by LS).",
        examples=["000880000", "005930000"],
    )
    alloc_gubun: str = Field(
        ...,
        title="배분적용구분 (Allocation flag)",
        description=(
            "Allocation flag code. Source enum not declared in the available "
            "Korean source — consume as returned by LS."
        ),
        examples=["", "0"],
    )
    volume: int = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative session volume up to this orderbook update.",
        examples=[12345678],
    )
    midprice: int = Field(
        ...,
        title="중간가격 (Mid price)",
        description="Mid price between best ask (offerho1) and best bid (bidho1).",
        examples=[73450],
    )
    offermidsumrem: int = Field(
        ...,
        title="매도중간가잔량합계수량 (Ask mid-price remaining sum)",
        description="Sum of ask remaining quantities at the mid price.",
        examples=[0, 120],
    )
    bidmidsumrem: int = Field(
        ...,
        title="매수중간가잔량합계수량 (Bid mid-price remaining sum)",
        description="Sum of bid remaining quantities at the mid price.",
        examples=[0, 180],
    )
    midsumrem: int = Field(
        ...,
        title="중간가잔량합계수량 (Mid-price remaining sum)",
        description="Sum of ``offermidsumrem`` + ``bidmidsumrem``.",
        examples=[0, 300],
    )
    midsumremgubun: str = Field(
        ...,
        title="중간가잔량구분 (Mid-price remaining side flag)",
        description=(
            "Mid-price remaining side flag. LS-source-declared values: "
            "' '=none, '1'=ask side, '2'=bid side."
        ),
        examples=[" ", "1", "2"],
    )
    ex_shcode: str = Field(
        ...,
        title="거래소별단축코드 (Exchange-prefixed short symbol code)",
        description="Exchange-prefixed short symbol code (e.g. 'N000880').",
        examples=["N000880", "N005930"],
    )


class NH1RealResponse(BaseModel):
    """(NXT) 호가잔량(NH1) 실시간 응답.

    Complete response model for NH1 real-time NXT orderbook data.
    """
    header: Optional[NH1RealResponseHeader]
    body: Optional[NH1RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
