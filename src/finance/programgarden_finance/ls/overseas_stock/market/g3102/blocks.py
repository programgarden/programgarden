"""Pydantic models for LS Securities OpenAPI g3102 (Overseas Stock time-and-sales / tick-by-tick).

g3102 returns a time-and-sales feed for one overseas-stock symbol —
each ``OutBlock1`` row is a single trade tick (local + Korean
date / time, price, change-vs-previous, OHLC, executed quantity, side
classifier). The response supports continuation via ``cts_seq``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and ``cgubun`` enum codes are NOT
      enumerated in the source available to this codebase. Where
      classification is generic, the description states "consume as
      returned by LS" rather than inventing additional codes.
    - Time ordering of ``OutBlock1`` rows is NOT declared in the source —
      consumers should not assume ascending or descending order.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3102.py``
      (delaygb='R', keysymbol='82TSLA', exchcd='82', symbol='TSLA',
      readcnt=30) plus neutral placeholder numerics.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3102RequestHeader(BlockRequestHeader):
    """g3102 request header. Inherits the standard LS request header schema."""
    pass


class G3102ResponseHeader(BlockResponseHeader):
    """g3102 response header. Inherits the standard LS response header schema."""
    pass


class G3102InBlock(BaseModel):
    """g3102InBlock — input block for the time-and-sales query."""

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
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA', 'AAPL').",
        examples=["TSLA", "AAPL"],
    )
    exchcd: Literal["81", "82"] = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description="Exchange code. '81' = NYSE / AMEX (뉴욕/아멕스), '82' = NASDAQ (나스닥).",
        examples=["82", "81"],
    )
    readcnt: int = Field(
        ...,
        title="조회갯수 (Read count)",
        description=(
            "Number of trade-tick rows to read per page. Length / max not "
            "declared in available source."
        ),
        examples=[30, 100],
    )
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스 (Continuation sequence)",
        description=(
            "Continuation sequence. Pass 0 (or empty) for the first page; "
            "echo the value returned in OutBlock for subsequent pages."
        ),
        examples=[0, 12345],
    )


class G3102Request(BaseModel):
    """g3102 full request envelope (header + body + setup options)."""

    header: G3102RequestHeader = Field(
        G3102RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3102",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3102InBlock"], G3102InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3102InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3102"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3102OutBlock(BaseModel):
    """g3102OutBlock — input echo + continuation control block.

    ``cts_seq`` and ``rec_count`` together drive paged retrieval of the
    underlying ``OutBlock1`` rows.
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
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스 (Continuation sequence)",
        description=(
            "Continuation sequence to use on the next page request. A "
            "value of 0 typically signals no further pages."
        ),
        examples=[0, 12345],
    )
    rec_count: int = Field(
        default=0,
        title="레코드카운트 (Record count)",
        description="Number of trade-tick rows returned in OutBlock1 for this page.",
        examples=[0, 30],
    )


class G3102OutBlock1(BaseModel):
    """g3102OutBlock1 — single trade-tick row.

    Decimal scale and currency unit are not declared in the source
    available to this codebase. The ``floatpoint`` field describes the
    decimal-place convention LS uses for the price strings on this row.
    Time ordering across consecutive rows is not declared — consume as
    returned by LS.
    """

    locdate: str = Field(
        default="",
        title="현지일자 (Local trade date)",
        description="Trade date in the local exchange timezone (YYYYMMDD).",
        examples=["20250414"],
    )
    loctime: str = Field(
        default="",
        title="현지시간 (Local trade time)",
        description="Trade time in the local exchange timezone (HHMMSS).",
        examples=["093015"],
    )
    kordate: str = Field(
        default="",
        title="한국일자 (Korean trade date)",
        description="Trade date in Korean Standard Time (YYYYMMDD).",
        examples=["20250414"],
    )
    kortime: str = Field(
        default="",
        title="한국시간 (Korean trade time)",
        description="Trade time in Korean Standard Time (HHMMSS).",
        examples=["223015"],
    )
    price: str = Field(
        default="",
        title="현재가 (Tick price)",
        description=(
            "Trade-tick price as a string. Decimal scale not declared in "
            "available source; see ``floatpoint`` on this row."
        ),
        examples=["250.25"],
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
        description=(
            "Absolute change vs. previous trading day. Decimal scale not "
            "declared in available source."
        ),
        examples=["1.50"],
    )
    rate: float = Field(
        default=0.0,
        title="등락률 (Change rate)",
        description=(
            "Percent change vs. previous trading day. Decimal scale not "
            "declared in available source."
        ),
        examples=[0.0, 0.67],
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
    exevol: int = Field(
        default=0,
        title="체결량 (Executed volume)",
        description="Executed volume for this trade tick (shares).",
        examples=[0, 100],
    )
    cgubun: str = Field(
        default="",
        title="체결구분 (Trade-side classifier)",
        description=(
            "Trade-side classifier as returned by LS. Code-set not "
            "enumerated in available source; consume as returned by LS."
        ),
        examples=["", "+", "-"],
    )
    floatpoint: str = Field(
        default="",
        title="소숫점자릿수 (Decimal places)",
        description="Number of decimal places LS applies to the price strings on this row.",
        examples=["4", "2"],
    )


class G3102Response(BaseModel):
    """g3102 full response envelope."""

    header: Optional[G3102ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3102OutBlock] = Field(
        None,
        title="기본 응답 블록 (Echo + continuation block)",
        description="Echo + continuation block (cts_seq / rec_count).",
    )
    block1: List[G3102OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Trade-tick rows)",
        description="List of trade-tick rows. Time ordering: consume as returned by LS.",
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
