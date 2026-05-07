"""Pydantic models for LS Securities OpenAPI HA_ (KOSDAQ 10-level orderbook).

HA_ is a Real-time WebSocket TR that pushes 10-level bid / ask orderbook
updates for KOSDAQ-listed stocks.  Field structure is identical to H1_
(KOSPI orderbook) — only the listing market differs.

The ``HA_RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — 6-digit short symbol code); the
``HA_RealResponseBody`` carries the per-update orderbook push payload.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - HA_ populates per-level remaining quantities normally, same as H1_.
    - ``donsigubun`` Korean source for HA_ does not declare an enum
      (unlike H1_) — falls back to "consume as returned by LS".
    - ``midsumremgubun`` enum (' '=없음 / '1'=매도 / '2'=매수) is preserved
      verbatim.
    - ``alloc_gubun`` (배분적용구분), aggregate count totals and decimal
      scale of price values are NOT declared in the available source —
      consume as returned by LS.
    - ``examples`` for ``tr_key`` and ``shcode`` mirror the example script
      (``src/finance/example/korea_stock/real_HA_.py`` uses ``"293490"``).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class HA_RealRequestHeader(BlockRealRequestHeader):
    """HA_ real-time request header. Inherits the standard LS WS request header schema."""
    pass


class HA_RealResponseHeader(BlockRealResponseHeader):
    """HA_ real-time response header. Inherits the standard LS WS response header schema."""
    pass


class HA_RealRequestBody(BaseModel):
    """HA_RealRequestBody — WebSocket subscription envelope for KOSDAQ orderbook push."""

    tr_cd: str = Field(
        default="HA_",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'HA_'.",
        examples=["HA_"],
    )
    tr_key: str = Field(
        ...,
        max_length=8,
        title="단축코드 (Short symbol code)",
        description="6-digit (or 8-character) KOSDAQ short symbol code.",
        examples=["293490", "086520"],
    )


class HA_RealRequest(BaseModel):
    """KOSDAQ 호가잔량(HA_) 실시간 시세 등록/해제 요청."""
    header: HA_RealRequestHeader = Field(
        HA_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="HA_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: HA_RealRequestBody = Field(
        HA_RealRequestBody(tr_cd="HA_", tr_key=""),
        title="요청 바디 (Request body)",
        description="KOSDAQ 호가잔량 실시간 등록에 필요한 종목코드 정보"
    )


class HA_RealResponseBody(BaseModel):
    """HA_RealResponseBody — KOSDAQ 10-level orderbook push payload (~50 fields)."""

    hotime: str = Field(
        ...,
        title="호가시간 (Orderbook time)",
        description="Orderbook receive time in HHMMSS format.",
        examples=["084242", "151530"],
    )
    offerho1: str = Field(
        ...,
        title="매도호가1 (Ask price — level 1)",
        description="Ask (sell) price at level 1.",
        examples=["28000"],
    )
    bidho1: str = Field(
        ...,
        title="매수호가1 (Bid price — level 1)",
        description="Bid (buy) price at level 1.",
        examples=["27950"],
    )
    offerrem1: str = Field(
        ...,
        title="매도호가잔량1 (Ask remaining quantity — level 1)",
        description="Ask remaining quantity at level 1.",
        examples=["1234"],
    )
    bidrem1: str = Field(
        ...,
        title="매수호가잔량1 (Bid remaining quantity — level 1)",
        description="Bid remaining quantity at level 1.",
        examples=["2345"],
    )
    offerho2: str = Field(
        ...,
        title="매도호가2 (Ask price — level 2)",
        description="Ask price at level 2.",
        examples=["28050"],
    )
    bidho2: str = Field(
        ...,
        title="매수호가2 (Bid price — level 2)",
        description="Bid price at level 2.",
        examples=["27900"],
    )
    offerrem2: str = Field(
        ...,
        title="매도호가잔량2 (Ask remaining quantity — level 2)",
        description="Ask remaining quantity at level 2.",
        examples=["1500"],
    )
    bidrem2: str = Field(
        ...,
        title="매수호가잔량2 (Bid remaining quantity — level 2)",
        description="Bid remaining quantity at level 2.",
        examples=["2500"],
    )
    offerho3: str = Field(
        ...,
        title="매도호가3 (Ask price — level 3)",
        description="Ask price at level 3.",
        examples=["28100"],
    )
    bidho3: str = Field(
        ...,
        title="매수호가3 (Bid price — level 3)",
        description="Bid price at level 3.",
        examples=["27850"],
    )
    offerrem3: str = Field(
        ...,
        title="매도호가잔량3 (Ask remaining quantity — level 3)",
        description="Ask remaining quantity at level 3.",
        examples=["800"],
    )
    bidrem3: str = Field(
        ...,
        title="매수호가잔량3 (Bid remaining quantity — level 3)",
        description="Bid remaining quantity at level 3.",
        examples=["1100"],
    )
    offerho4: str = Field(
        ...,
        title="매도호가4 (Ask price — level 4)",
        description="Ask price at level 4.",
        examples=["28150"],
    )
    bidho4: str = Field(
        ...,
        title="매수호가4 (Bid price — level 4)",
        description="Bid price at level 4.",
        examples=["27800"],
    )
    offerrem4: str = Field(
        ...,
        title="매도호가잔량4 (Ask remaining quantity — level 4)",
        description="Ask remaining quantity at level 4.",
        examples=["650"],
    )
    bidrem4: str = Field(
        ...,
        title="매수호가잔량4 (Bid remaining quantity — level 4)",
        description="Bid remaining quantity at level 4.",
        examples=["900"],
    )
    offerho5: str = Field(
        ...,
        title="매도호가5 (Ask price — level 5)",
        description="Ask price at level 5.",
        examples=["28200"],
    )
    bidho5: str = Field(
        ...,
        title="매수호가5 (Bid price — level 5)",
        description="Bid price at level 5.",
        examples=["27750"],
    )
    offerrem5: str = Field(
        ...,
        title="매도호가잔량5 (Ask remaining quantity — level 5)",
        description="Ask remaining quantity at level 5.",
        examples=["540"],
    )
    bidrem5: str = Field(
        ...,
        title="매수호가잔량5 (Bid remaining quantity — level 5)",
        description="Bid remaining quantity at level 5.",
        examples=["780"],
    )
    offerho6: str = Field(
        ...,
        title="매도호가6 (Ask price — level 6)",
        description="Ask price at level 6.",
        examples=["28250"],
    )
    bidho6: str = Field(
        ...,
        title="매수호가6 (Bid price — level 6)",
        description="Bid price at level 6.",
        examples=["27700"],
    )
    offerrem6: str = Field(
        ...,
        title="매도호가잔량6 (Ask remaining quantity — level 6)",
        description="Ask remaining quantity at level 6.",
        examples=["430"],
    )
    bidrem6: str = Field(
        ...,
        title="매수호가잔량6 (Bid remaining quantity — level 6)",
        description="Bid remaining quantity at level 6.",
        examples=["620"],
    )
    offerho7: str = Field(
        ...,
        title="매도호가7 (Ask price — level 7)",
        description="Ask price at level 7.",
        examples=["28300"],
    )
    bidho7: str = Field(
        ...,
        title="매수호가7 (Bid price — level 7)",
        description="Bid price at level 7.",
        examples=["27650"],
    )
    offerrem7: str = Field(
        ...,
        title="매도호가잔량7 (Ask remaining quantity — level 7)",
        description="Ask remaining quantity at level 7.",
        examples=["320"],
    )
    bidrem7: str = Field(
        ...,
        title="매수호가잔량7 (Bid remaining quantity — level 7)",
        description="Bid remaining quantity at level 7.",
        examples=["510"],
    )
    offerho8: str = Field(
        ...,
        title="매도호가8 (Ask price — level 8)",
        description="Ask price at level 8.",
        examples=["28350"],
    )
    bidho8: str = Field(
        ...,
        title="매수호가8 (Bid price — level 8)",
        description="Bid price at level 8.",
        examples=["27600"],
    )
    offerrem8: str = Field(
        ...,
        title="매도호가잔량8 (Ask remaining quantity — level 8)",
        description="Ask remaining quantity at level 8.",
        examples=["280"],
    )
    bidrem8: str = Field(
        ...,
        title="매수호가잔량8 (Bid remaining quantity — level 8)",
        description="Bid remaining quantity at level 8.",
        examples=["410"],
    )
    offerho9: str = Field(
        ...,
        title="매도호가9 (Ask price — level 9)",
        description="Ask price at level 9.",
        examples=["28400"],
    )
    bidho9: str = Field(
        ...,
        title="매수호가9 (Bid price — level 9)",
        description="Bid price at level 9.",
        examples=["27550"],
    )
    offerrem9: str = Field(
        ...,
        title="매도호가잔량9 (Ask remaining quantity — level 9)",
        description="Ask remaining quantity at level 9.",
        examples=["210"],
    )
    bidrem9: str = Field(
        ...,
        title="매수호가잔량9 (Bid remaining quantity — level 9)",
        description="Bid remaining quantity at level 9.",
        examples=["330"],
    )
    offerho10: str = Field(
        ...,
        title="매도호가10 (Ask price — level 10)",
        description="Ask price at level 10.",
        examples=["28450"],
    )
    bidho10: str = Field(
        ...,
        title="매수호가10 (Bid price — level 10)",
        description="Bid price at level 10.",
        examples=["27500"],
    )
    offerrem10: str = Field(
        ...,
        title="매도호가잔량10 (Ask remaining quantity — level 10)",
        description="Ask remaining quantity at level 10.",
        examples=["180"],
    )
    bidrem10: str = Field(
        ...,
        title="매수호가잔량10 (Bid remaining quantity — level 10)",
        description="Bid remaining quantity at level 10.",
        examples=["260"],
    )
    totofferrem: str = Field(
        ...,
        title="총매도호가잔량 (Total ask remaining quantity)",
        description="Sum of ask remaining quantities across levels 1–10.",
        examples=["6234"],
    )
    totbidrem: str = Field(
        ...,
        title="총매수호가잔량 (Total bid remaining quantity)",
        description="Sum of bid remaining quantities across levels 1–10.",
        examples=["9655"],
    )
    donsigubun: str = Field(
        ...,
        title="동시호가구분 (Concurrent-quote phase code)",
        description=(
            "Concurrent-quote phase code. Source enum not declared in the "
            "HA_ Korean source — consume as returned by LS. (See H1_ for an "
            "LS-source-declared enum reference.)"
        ),
        examples=["1", "2", "3", "4"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="6-digit short symbol code matching the subscribed ``tr_key``.",
        examples=["293490", "086520"],
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
    volume: str = Field(
        ...,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative session volume up to this orderbook update.",
        examples=["12345678"],
    )
    midprice: str = Field(
        ...,
        title="중간가격 (Mid price)",
        description="Mid price between best ask (offerho1) and best bid (bidho1).",
        examples=["27975"],
    )
    offermidsumrem: str = Field(
        ...,
        title="매도중간가잔량합계수량 (Ask mid-price remaining sum)",
        description="Sum of ask remaining quantities at the mid price.",
        examples=["0", "120"],
    )
    bidmidsumrem: str = Field(
        ...,
        title="매수중간가잔량합계수량 (Bid mid-price remaining sum)",
        description="Sum of bid remaining quantities at the mid price.",
        examples=["0", "180"],
    )
    midsumrem: str = Field(
        ...,
        title="중간가잔량합계수량 (Mid-price remaining sum)",
        description="Sum of ``offermidsumrem`` + ``bidmidsumrem``.",
        examples=["0", "300"],
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


class HA_RealResponse(BaseModel):
    """KOSDAQ 호가잔량(HA_) 실시간 응답.

    Complete response model for HA_ real-time KOSDAQ orderbook data.
    """
    header: Optional[HA_RealResponseHeader]
    body: Optional[HA_RealResponseBody]

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
