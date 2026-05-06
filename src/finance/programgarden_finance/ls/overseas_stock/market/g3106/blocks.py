"""Pydantic models for LS Securities OpenAPI g3106 (Overseas Stock 10-level orderbook + quote snapshot).

g3106 returns a 10-level bid/ask orderbook combined with the
current-price snapshot for one overseas-stock symbol. For each of
levels 1..10 LS returns a price (``offerho`` / ``bidho``), an
order-count (``offercnt`` / ``bidcnt``), and a remaining quantity
(``offerrem`` / ``bidrem``). Aggregate totals (``offer`` / ``bid``)
and aggregate count totals (``offercnt`` / ``bidcnt`` at the bottom of
the block) are also returned.

⚠️ LS API constraint observed in this codebase (overseas-stock only):
    - Per-level prices and per-level remaining quantities are populated
      normally.
    - Per-level order-count fields (``offercnt1``..``offercnt10``,
      ``bidcnt1``..``bidcnt10``) are always returned as 0 by LS for
      overseas stock — the count side is not exposed for this market.
    - Aggregate count totals (``offercnt`` / ``bidcnt`` without a level
      suffix) are also always 0.
    - Overseas futures and Korean stock TRs do expose count fields.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale and currency unit are NOT declared in the source
      available to this codebase. The ``floatpoint`` field describes the
      decimal-place convention LS uses for the price strings.
    - The "always 0" notes on count fields mirror existing in-codebase
      observations and are preserved verbatim — they are observed
      behaviour, not inferred.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3106.py``
      (delaygb='R', keysymbol='82TSLA', exchcd='82', symbol='TSLA') plus
      neutral placeholder numerics.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3106RequestHeader(BlockRequestHeader):
    """g3106 request header. Inherits the standard LS request header schema."""
    pass


class G3106ResponseHeader(BlockResponseHeader):
    """g3106 response header. Inherits the standard LS response header schema."""
    pass


class G3106InBlock(BaseModel):
    """g3106InBlock — input block for the 10-level orderbook + snapshot query."""

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Delay flag. Always 'R' (real-time / 실시간) per LS source.",
        examples=["R"],
    )
    keysymbol: str = Field(
        ...,
        title="KEY종목코드 (Key symbol code)",
        description=(
            "LS-internal key symbol code combining exchange code and ticker "
            "(e.g., '82TSLA' = NASDAQ + TSLA)."
        ),
        examples=["82TSLA", "82AAPL"],
    )
    exchcd: Literal["81", "82"] = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description="Exchange code. '81' = NYSE / AMEX (뉴욕/아멕스), '82' = NASDAQ (나스닥).",
        examples=["82", "81"],
    )
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA', 'AAPL').",
        examples=["TSLA", "AAPL"],
    )


class G3106Request(BaseModel):
    """g3106 full request envelope (header + body + setup options)."""

    header: G3106RequestHeader = Field(
        G3106RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3106",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3106InBlock"], G3106InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3106InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3106"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3106OutBlock(BaseModel):
    """g3106OutBlock — 10-level orderbook + current-price snapshot.

    Decimal scale and currency unit are not declared in the source
    available to this codebase. See ``floatpoint`` for LS-reported
    decimal-place count.
    """

    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분 (Delay flag)",
        description="Echoed delay flag. Always 'R'.",
        examples=["R"],
    )
    keysymbol: str = Field(
        default="",
        title="KEY종목코드 (Key symbol code)",
        description="Echoed LS-internal key symbol code (e.g., '82TSLA').",
        examples=["82TSLA"],
    )
    exchcd: Literal["81", "82"] = Field(
        default="82",
        title="거래소코드 (Exchange code)",
        description="Echoed exchange code. '81' = NYSE / AMEX, '82' = NASDAQ.",
        examples=["82", "81"],
    )
    symbol: str = Field(
        default="",
        title="종목코드 (Symbol / ticker)",
        description="Echoed ticker symbol.",
        examples=["TSLA"],
    )
    korname: str = Field(
        default="",
        title="한글종목명 (Korean issue name)",
        description="Issue name in Korean.",
        examples=["테슬라"],
    )
    price: str = Field(
        default="",
        title="현재가 (Current price)",
        description=(
            "Latest traded price as a string. Decimal scale not declared "
            "in available source; see ``floatpoint``."
        ),
        examples=["250.25"],
    )
    floatpoint: str = Field(
        default="",
        title="소수점자리수 (Decimal places)",
        description="Number of decimal places LS applies to the price strings.",
        examples=["4", "2"],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Change-vs-previous sign)",
        description=(
            "Sign indicator vs. previous trading day. '+' = up (상승), "
            "'-' = down (하락). Other LS-defined codes may appear; consume "
            "as returned by LS."
        ),
        examples=["+", "-"],
    )
    diff: str = Field(
        default="",
        title="전일대비 (Change vs. previous)",
        description="Absolute change vs. previous trading day.",
        examples=["1.50"],
    )
    rate: float = Field(
        default=0.0,
        title="등락율 (Change rate)",
        description="Percent change vs. previous trading day.",
        examples=[0.0, 0.67],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative trading volume for the day (shares).",
        examples=[0, 1000000],
    )
    amount: int = Field(
        default=0,
        title="누적거래대금 (Cumulative trade value)",
        description="Cumulative trade value for the day. Currency unit not declared in available source.",
        examples=[0, 250000000],
    )
    jnilclose: str = Field(
        default="",
        title="전일종가 (Previous close)",
        description="Previous trading day close price as a string.",
        examples=["248.00"],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Open price)",
        description="Opening price of the day.",
        examples=[0.0, 248.00],
    )
    high: float = Field(
        default=0.0,
        title="고가 (High price)",
        description="Highest traded price of the day.",
        examples=[0.0, 252.00],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low price)",
        description="Lowest traded price of the day.",
        examples=[0.0, 247.00],
    )
    hotime: str = Field(
        default="",
        title="현지시간 (Local time of orderbook snapshot)",
        description="Local exchange time at which the orderbook snapshot was taken (HHMMSS).",
        examples=["093015"],
    )
    # Level 1
    offerho1: str = Field(
        default="",
        title="매도호가1 (Ask price level 1)",
        description="Ask price at level 1.",
        examples=["250.30"],
    )
    bidho1: str = Field(
        default="",
        title="매수호가1 (Bid price level 1)",
        description="Bid price at level 1.",
        examples=["250.20"],
    )
    offercnt1: str = Field(
        default="",
        title="매도호가건수1 (Ask order-count level 1)",
        description="Ask order count at level 1. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt1: str = Field(
        default="",
        title="매수호가건수1 (Bid order-count level 1)",
        description="Bid order count at level 1. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem1: int = Field(
        default=0,
        title="매도호가수량1 (Ask remaining quantity level 1)",
        description="Ask remaining quantity at level 1 (shares).",
        examples=[0, 100],
    )
    bidrem1: int = Field(
        default=0,
        title="매수호가수량1 (Bid remaining quantity level 1)",
        description="Bid remaining quantity at level 1 (shares).",
        examples=[0, 100],
    )
    # Level 2
    offerho2: str = Field(
        default="",
        title="매도호가2 (Ask price level 2)",
        description="Ask price at level 2.",
        examples=["250.35"],
    )
    bidho2: str = Field(
        default="",
        title="매수호가2 (Bid price level 2)",
        description="Bid price at level 2.",
        examples=["250.15"],
    )
    offercnt2: str = Field(
        default="",
        title="매도호가건수2 (Ask order-count level 2)",
        description="Ask order count at level 2. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt2: str = Field(
        default="",
        title="매수호가건수2 (Bid order-count level 2)",
        description="Bid order count at level 2. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem2: int = Field(
        default=0,
        title="매도호가수량2 (Ask remaining quantity level 2)",
        description="Ask remaining quantity at level 2 (shares).",
        examples=[0, 200],
    )
    bidrem2: int = Field(
        default=0,
        title="매수호가수량2 (Bid remaining quantity level 2)",
        description="Bid remaining quantity at level 2 (shares).",
        examples=[0, 200],
    )
    # Level 3
    offerho3: str = Field(
        default="",
        title="매도호가3 (Ask price level 3)",
        description="Ask price at level 3.",
        examples=["250.40"],
    )
    bidho3: str = Field(
        default="",
        title="매수호가3 (Bid price level 3)",
        description="Bid price at level 3.",
        examples=["250.10"],
    )
    offercnt3: str = Field(
        default="",
        title="매도호가건수3 (Ask order-count level 3)",
        description="Ask order count at level 3. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt3: str = Field(
        default="",
        title="매수호가건수3 (Bid order-count level 3)",
        description="Bid order count at level 3. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem3: int = Field(
        default=0,
        title="매도호가수량3 (Ask remaining quantity level 3)",
        description="Ask remaining quantity at level 3 (shares).",
        examples=[0, 300],
    )
    bidrem3: int = Field(
        default=0,
        title="매수호가수량3 (Bid remaining quantity level 3)",
        description="Bid remaining quantity at level 3 (shares).",
        examples=[0, 300],
    )
    # Level 4
    offerho4: str = Field(
        default="",
        title="매도호가4 (Ask price level 4)",
        description="Ask price at level 4.",
        examples=["250.45"],
    )
    bidho4: str = Field(
        default="",
        title="매수호가4 (Bid price level 4)",
        description="Bid price at level 4.",
        examples=["250.05"],
    )
    offercnt4: str = Field(
        default="",
        title="매도호가건수4 (Ask order-count level 4)",
        description="Ask order count at level 4. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt4: str = Field(
        default="",
        title="매수호가건수4 (Bid order-count level 4)",
        description="Bid order count at level 4. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem4: int = Field(
        default=0,
        title="매도호가수량4 (Ask remaining quantity level 4)",
        description="Ask remaining quantity at level 4 (shares).",
        examples=[0, 400],
    )
    bidrem4: int = Field(
        default=0,
        title="매수호가수량4 (Bid remaining quantity level 4)",
        description="Bid remaining quantity at level 4 (shares).",
        examples=[0, 400],
    )
    # Level 5
    offerho5: str = Field(
        default="",
        title="매도호가5 (Ask price level 5)",
        description="Ask price at level 5.",
        examples=["250.50"],
    )
    bidho5: str = Field(
        default="",
        title="매수호가5 (Bid price level 5)",
        description="Bid price at level 5.",
        examples=["250.00"],
    )
    offercnt5: str = Field(
        default="",
        title="매도호가건수5 (Ask order-count level 5)",
        description="Ask order count at level 5. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt5: str = Field(
        default="",
        title="매수호가건수5 (Bid order-count level 5)",
        description="Bid order count at level 5. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem5: int = Field(
        default=0,
        title="매도호가수량5 (Ask remaining quantity level 5)",
        description="Ask remaining quantity at level 5 (shares).",
        examples=[0, 500],
    )
    bidrem5: int = Field(
        default=0,
        title="매수호가수량5 (Bid remaining quantity level 5)",
        description="Bid remaining quantity at level 5 (shares).",
        examples=[0, 500],
    )
    # Level 6
    offerho6: str = Field(
        default="",
        title="매도호가6 (Ask price level 6)",
        description="Ask price at level 6.",
        examples=["250.55"],
    )
    bidho6: str = Field(
        default="",
        title="매수호가6 (Bid price level 6)",
        description="Bid price at level 6.",
        examples=["249.95"],
    )
    offercnt6: str = Field(
        default="",
        title="매도호가건수6 (Ask order-count level 6)",
        description="Ask order count at level 6. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt6: str = Field(
        default="",
        title="매수호가건수6 (Bid order-count level 6)",
        description="Bid order count at level 6. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem6: int = Field(
        default=0,
        title="매도호가수량6 (Ask remaining quantity level 6)",
        description="Ask remaining quantity at level 6 (shares).",
        examples=[0, 600],
    )
    bidrem6: int = Field(
        default=0,
        title="매수호가수량6 (Bid remaining quantity level 6)",
        description="Bid remaining quantity at level 6 (shares).",
        examples=[0, 600],
    )
    # Level 7
    offerho7: str = Field(
        default="",
        title="매도호가7 (Ask price level 7)",
        description="Ask price at level 7.",
        examples=["250.60"],
    )
    bidho7: str = Field(
        default="",
        title="매수호가7 (Bid price level 7)",
        description="Bid price at level 7.",
        examples=["249.90"],
    )
    offercnt7: str = Field(
        default="",
        title="매도호가건수7 (Ask order-count level 7)",
        description="Ask order count at level 7. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt7: str = Field(
        default="",
        title="매수호가건수7 (Bid order-count level 7)",
        description="Bid order count at level 7. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem7: int = Field(
        default=0,
        title="매도호가수량7 (Ask remaining quantity level 7)",
        description="Ask remaining quantity at level 7 (shares).",
        examples=[0, 700],
    )
    bidrem7: int = Field(
        default=0,
        title="매수호가수량7 (Bid remaining quantity level 7)",
        description="Bid remaining quantity at level 7 (shares).",
        examples=[0, 700],
    )
    # Level 8
    offerho8: str = Field(
        default="",
        title="매도호가8 (Ask price level 8)",
        description="Ask price at level 8.",
        examples=["250.65"],
    )
    bidho8: str = Field(
        default="",
        title="매수호가8 (Bid price level 8)",
        description="Bid price at level 8.",
        examples=["249.85"],
    )
    offercnt8: str = Field(
        default="",
        title="매도호가건수8 (Ask order-count level 8)",
        description="Ask order count at level 8. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt8: str = Field(
        default="",
        title="매수호가건수8 (Bid order-count level 8)",
        description="Bid order count at level 8. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem8: int = Field(
        default=0,
        title="매도호가수량8 (Ask remaining quantity level 8)",
        description="Ask remaining quantity at level 8 (shares).",
        examples=[0, 800],
    )
    bidrem8: int = Field(
        default=0,
        title="매수호가수량8 (Bid remaining quantity level 8)",
        description="Bid remaining quantity at level 8 (shares).",
        examples=[0, 800],
    )
    # Level 9
    offerho9: str = Field(
        default="",
        title="매도호가9 (Ask price level 9)",
        description="Ask price at level 9.",
        examples=["250.70"],
    )
    bidho9: str = Field(
        default="",
        title="매수호가9 (Bid price level 9)",
        description="Bid price at level 9.",
        examples=["249.80"],
    )
    offercnt9: str = Field(
        default="",
        title="매도호가건수9 (Ask order-count level 9)",
        description="Ask order count at level 9. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt9: str = Field(
        default="",
        title="매수호가건수9 (Bid order-count level 9)",
        description="Bid order count at level 9. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem9: int = Field(
        default=0,
        title="매도호가수량9 (Ask remaining quantity level 9)",
        description="Ask remaining quantity at level 9 (shares).",
        examples=[0, 900],
    )
    bidrem9: int = Field(
        default=0,
        title="매수호가수량9 (Bid remaining quantity level 9)",
        description="Bid remaining quantity at level 9 (shares).",
        examples=[0, 900],
    )
    # Level 10
    offerho10: str = Field(
        default="",
        title="매도호가10 (Ask price level 10)",
        description="Ask price at level 10.",
        examples=["250.75"],
    )
    bidho10: str = Field(
        default="",
        title="매수호가10 (Bid price level 10)",
        description="Bid price at level 10.",
        examples=["249.75"],
    )
    offercnt10: str = Field(
        default="",
        title="매도호가건수10 (Ask order-count level 10)",
        description="Ask order count at level 10. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    bidcnt10: str = Field(
        default="",
        title="매수호가건수10 (Bid order-count level 10)",
        description="Bid order count at level 10. ⚠️ LS API does not expose this for overseas stock — always returned as 0.",
        examples=["0"],
    )
    offerrem10: int = Field(
        default=0,
        title="매도호가수량10 (Ask remaining quantity level 10)",
        description="Ask remaining quantity at level 10 (shares).",
        examples=[0, 1000],
    )
    bidrem10: int = Field(
        default=0,
        title="매수호가수량10 (Bid remaining quantity level 10)",
        description="Bid remaining quantity at level 10 (shares).",
        examples=[0, 1000],
    )
    # Aggregates
    offercnt: str = Field(
        default="",
        title="총매도호가건수 (Total ask order count)",
        description=(
            "Total ask order count across all levels. ⚠️ LS API does not "
            "expose this for overseas stock — always returned as 0."
        ),
        examples=["0"],
    )
    bidcnt: str = Field(
        default="",
        title="총매수호가건수 (Total bid order count)",
        description=(
            "Total bid order count across all levels. ⚠️ LS API does not "
            "expose this for overseas stock — always returned as 0."
        ),
        examples=["0"],
    )
    offer: int = Field(
        default=0,
        title="총매도호가수량 (Total ask remaining quantity)",
        description="Aggregate ask-side remaining quantity across all levels (shares).",
        examples=[0, 5500],
    )
    bid: int = Field(
        default=0,
        title="총매수호가수량 (Total bid remaining quantity)",
        description="Aggregate bid-side remaining quantity across all levels (shares).",
        examples=[0, 5500],
    )


class G3106Response(BaseModel):
    """g3106 full response envelope."""

    header: Optional[G3106ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3106OutBlock] = Field(
        None,
        title="기본 응답 블록 (Orderbook + snapshot block)",
        description="10-level orderbook + current-price snapshot block.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (LS response message)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
