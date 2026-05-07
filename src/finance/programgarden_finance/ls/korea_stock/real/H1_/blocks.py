"""Pydantic models for LS Securities OpenAPI H1_ (KOSPI 10-level orderbook).

H1_ is a Real-time WebSocket TR that pushes 10-level bid / ask orderbook
updates for KOSPI-listed stocks during regular session (09:00–15:30 KST).
The ``H1_RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + ``tr_key`` — 6-digit short symbol code); the
``H1_RealResponseBody`` carries the per-update orderbook push payload.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - Unlike overseas-stock GSH (which only populates aggregate
      quantities), H1_ populates per-level remaining quantities normally
      — preserved verbatim from the in-codebase Korean source.
    - ``donsigubun`` enum ('1'=장개시전 / '2'=장마감전 / '3'=장중 / '4'=장후)
      is preserved verbatim.
    - ``midsumremgubun`` enum (' '=없음 / '1'=매도 / '2'=매수) is preserved
      verbatim.
    - ``alloc_gubun`` (배분적용구분), aggregate count totals and decimal
      scale of price values are NOT declared in the available source —
      consume as returned by LS.
    - ``examples`` for ``tr_key`` and ``shcode`` mirror the example script
      (``src/finance/example/korea_stock/real_H1_.py`` uses ``"005930"``).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class H1_RealRequestHeader(BlockRealRequestHeader):
    """H1_ real-time request header. Inherits the standard LS WS request header schema."""
    pass


class H1_RealResponseHeader(BlockRealResponseHeader):
    """H1_ real-time response header. Inherits the standard LS WS response header schema."""
    pass


class H1_RealRequestBody(BaseModel):
    """H1_RealRequestBody — WebSocket subscription envelope for KOSPI orderbook push."""

    tr_cd: str = Field(
        default="H1_",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'H1_'.",
        examples=["H1_"],
    )
    tr_key: str = Field(
        ...,
        max_length=8,
        title="단축코드 (Short symbol code)",
        description="6-digit (or 8-character) KOSPI short symbol code.",
        examples=["005930", "035420"],
    )


class H1_RealRequest(BaseModel):
    """KOSPI 호가잔량(H1_) 실시간 시세 등록/해제 요청."""
    header: H1_RealRequestHeader = Field(
        H1_RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더 (Request header)",
        description="H1_ 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: H1_RealRequestBody = Field(
        H1_RealRequestBody(tr_cd="H1_", tr_key=""),
        title="요청 바디 (Request body)",
        description="KOSPI 호가잔량 실시간 등록에 필요한 종목코드 정보"
    )


class H1_RealResponseBody(BaseModel):
    """H1_RealResponseBody — KOSPI 10-level orderbook push payload (~50 fields)."""

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
        examples=["73500"],
    )
    bidho1: str = Field(
        ...,
        title="매수호가1 (Bid price — level 1)",
        description="Bid (buy) price at level 1.",
        examples=["73400"],
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
        examples=["73600"],
    )
    bidho2: str = Field(
        ...,
        title="매수호가2 (Bid price — level 2)",
        description="Bid price at level 2.",
        examples=["73300"],
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
        examples=["73700"],
    )
    bidho3: str = Field(
        ...,
        title="매수호가3 (Bid price — level 3)",
        description="Bid price at level 3.",
        examples=["73200"],
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
        examples=["73800"],
    )
    bidho4: str = Field(
        ...,
        title="매수호가4 (Bid price — level 4)",
        description="Bid price at level 4.",
        examples=["73100"],
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
        examples=["73900"],
    )
    bidho5: str = Field(
        ...,
        title="매수호가5 (Bid price — level 5)",
        description="Bid price at level 5.",
        examples=["73000"],
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
        examples=["74000"],
    )
    bidho6: str = Field(
        ...,
        title="매수호가6 (Bid price — level 6)",
        description="Bid price at level 6.",
        examples=["72900"],
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
        examples=["74100"],
    )
    bidho7: str = Field(
        ...,
        title="매수호가7 (Bid price — level 7)",
        description="Bid price at level 7.",
        examples=["72800"],
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
        examples=["74200"],
    )
    bidho8: str = Field(
        ...,
        title="매수호가8 (Bid price — level 8)",
        description="Bid price at level 8.",
        examples=["72700"],
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
        examples=["74300"],
    )
    bidho9: str = Field(
        ...,
        title="매수호가9 (Bid price — level 9)",
        description="Bid price at level 9.",
        examples=["72600"],
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
        examples=["74400"],
    )
    bidho10: str = Field(
        ...,
        title="매수호가10 (Bid price — level 10)",
        description="Bid price at level 10.",
        examples=["72500"],
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
            "Concurrent-quote phase code. LS-source-declared values: "
            "'1'=장개시전 (pre-open), '2'=장마감전 (pre-close), "
            "'3'=장중 (intraday), '4'=장후 (post-close)."
        ),
        examples=["1", "2", "3", "4"],
    )
    shcode: str = Field(
        ...,
        title="단축코드 (Short symbol code)",
        description="6-digit short symbol code matching the subscribed ``tr_key``.",
        examples=["005930", "035420"],
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
        examples=["73450"],
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


class H1_RealResponse(BaseModel):
    """KOSPI 호가잔량(H1_) 실시간 응답.

    Complete response model for H1_ real-time KOSPI orderbook data.
    """
    header: Optional[H1_RealResponseHeader]
    body: Optional[H1_RealResponseBody]

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
