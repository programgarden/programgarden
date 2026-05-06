"""Pydantic models for LS Securities OpenAPI g3104 (Overseas Stock security master / detail info).

g3104 returns the per-issue security master record for one
overseas-stock symbol — Korean / English issue names, exchange / nation
labels, industry, security type, currency, decimal-place convention,
trading restrictions, share count, tick / lot sizes, OHLC, prior close,
52-week range, market-cap, PER / EPS, FX rate, and alt lot sizes.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and the enum codes used by ``suspend``
      / ``sellonly`` are NOT enumerated in the source available to this
      codebase. Where the source is generic, the description states
      "consume as returned by LS" rather than inventing additional codes.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3104.py``
      (delaygb='R', keysymbol='82TSLA', exchcd='82', symbol='TSLA') plus
      neutral placeholder numerics.
    - Note: the original docstring claimed ``high52p``/``low52p`` as
      ``float``, but the actual annotations are ``str``. Annotations are
      preserved.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3104RequestHeader(BlockRequestHeader):
    """g3104 request header. Inherits the standard LS request header schema."""
    pass


class G3104ResponseHeader(BlockResponseHeader):
    """g3104 response header. Inherits the standard LS response header schema."""
    pass


class G3104InBlock(BaseModel):
    """g3104InBlock — input block for the security-master detail query."""

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


class G3104Request(BaseModel):
    """g3104 full request envelope (header + body + setup options)."""

    header: G3104RequestHeader = Field(
        G3104RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3104",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3104InBlock"], G3104InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3104InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3104"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3104OutBlock(BaseModel):
    """g3104OutBlock — security-master detail block.

    Decimal scale, currency unit, and lot-size unit are not declared in
    the source available to this codebase. The ``floatpoint`` field
    describes the decimal-place convention LS uses for the price
    strings.
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
    exchange: str = Field(
        default="",
        title="거래소ID (Exchange ID)",
        description="LS internal exchange identifier string.",
        examples=["NASDAQ", "NYSE"],
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
    engname: str = Field(
        default="",
        title="영문종목명 (English issue name)",
        description="Issue name in English.",
        examples=["TESLA INC"],
    )
    exchange_name: str = Field(
        default="",
        title="거래소명 (Exchange name)",
        description="Human-readable exchange name.",
        examples=["NASDAQ"],
    )
    nation_name: str = Field(
        default="",
        title="국가명 (Country / nation name)",
        description="Country / nation name for the listing.",
        examples=["United States"],
    )
    induname: str = Field(
        default="",
        title="업종명 (Industry name)",
        description="Industry / sector name.",
        examples=["자동차"],
    )
    instname: str = Field(
        default="",
        title="증권종류 (Security type)",
        description=(
            "Security type label as returned by LS. Code-set not "
            "enumerated in available source; consume as returned by LS."
        ),
        examples=["주식"],
    )
    floatpoint: str = Field(
        default="",
        title="소숫점자릿수 (Decimal places)",
        description="Number of decimal places LS applies to the price strings.",
        examples=["4", "2"],
    )
    currency: str = Field(
        default="",
        title="거래통화 (Trading currency)",
        description="ISO-style currency code for the price quotation.",
        examples=["USD"],
    )
    suspend: str = Field(
        default="",
        title="거래상태 (Trading-suspend flag)",
        description=(
            "Trading suspend flag. Code-set not enumerated in available "
            "source; consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    sellonly: str = Field(
        default="",
        title="매매구분 (Trade-side restriction)",
        description=(
            "Trade-side restriction flag. Code-set not enumerated in "
            "available source; consume as returned by LS."
        ),
        examples=["", "0", "1", "2"],
    )
    share: int = Field(
        default=0,
        title="발행주식수 (Issued shares)",
        description="Total issued share count.",
        examples=[0, 3170000000],
    )
    untprc: float = Field(
        default=0.0,
        title="호가단위 (Tick / quote unit)",
        description=(
            "Quote price tick unit. Decimal scale not declared in "
            "available source."
        ),
        examples=[0.0, 0.01],
    )
    bidlotsize: int = Field(
        default=0,
        title="매수주문단위 (Buy lot size)",
        description="Minimum buy-side order lot size (shares).",
        examples=[0, 1],
    )
    asklotsize: int = Field(
        default=0,
        title="매도주문단위 (Sell lot size)",
        description="Minimum sell-side order lot size (shares).",
        examples=[0, 1],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Cumulative volume)",
        description="Cumulative trading volume for the day (shares).",
        examples=[0, 1000000],
    )
    amount: int = Field(
        default=0,
        title="거래대금 (Cumulative trade value)",
        description="Cumulative trade value for the day. Currency unit not declared in available source.",
        examples=[0, 250000000],
    )
    pcls: float = Field(
        default=0.0,
        title="전일종가 (Previous close)",
        description="Previous trading day close price.",
        examples=[0.0, 248.00],
    )
    clos: float = Field(
        default=0.0,
        title="기준가 (Base / reference price)",
        description="Base reference price for the day.",
        examples=[0.0, 248.00],
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
    high52p: str = Field(
        default="",
        title="52주고가 (52-week high price)",
        description=(
            "Highest traded price across the trailing 52 weeks as a string. "
            "Decimal scale not declared in available source."
        ),
        examples=["350.00"],
    )
    low52p: str = Field(
        default="",
        title="52주저가 (52-week low price)",
        description=(
            "Lowest traded price across the trailing 52 weeks as a string."
        ),
        examples=["100.50"],
    )
    shareprc: int = Field(
        default=0,
        title="시가총액 (Market capitalization)",
        description="Market capitalization. Currency unit not declared in available source.",
        examples=[0, 800000000000],
    )
    perv: float = Field(
        default=0.0,
        title="PER (Price-to-earnings ratio)",
        description=(
            "Price-to-earnings ratio. Scale and computation basis not "
            "declared in available source."
        ),
        examples=[0.0, 25.50],
    )
    epsv: float = Field(
        default=0.0,
        title="EPS (Earnings per share)",
        description=(
            "Earnings per share. Currency and scale not declared in "
            "available source."
        ),
        examples=[0.0, 9.80],
    )
    exrate: float = Field(
        default=0.0,
        title="환율 (FX rate)",
        description=(
            "Foreign-exchange rate applied to this issue. Scale and base "
            "currency not declared in available source."
        ),
        examples=[0.0, 1380.00],
    )
    bidlotsize2: int = Field(
        default=0,
        title="매수주문단위2 (Alternate buy lot size)",
        description="Alternate buy-side lot size, as returned by LS.",
        examples=[0, 1],
    )
    asklotsize2: int = Field(
        default=0,
        title="매도주문단위2 (Alternate sell lot size)",
        description="Alternate sell-side lot size, as returned by LS.",
        examples=[0, 1],
    )


class G3104Response(BaseModel):
    """g3104 full response envelope."""

    header: Optional[G3104ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3104OutBlock] = Field(
        None,
        title="기본 응답 블록 (Security-master block)",
        description="Security-master detail block.",
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
