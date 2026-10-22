"""Pydantic models for LS Securities OpenAPI g3101 (Overseas Stock current price snapshot).

g3101 returns a single-row snapshot of the latest market quote for one
overseas-stock symbol — current price, change vs. previous, OHLC,
cumulative volume / amount, 52-week range, PER / EPS, etc.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and ``sign`` enum codes are NOT
      enumerated in the source available to this codebase. Where the
      Korean spec uses generic phrasing, the description states "consume
      as returned by LS" rather than inventing additional codes.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3101.py``
      (delaygb='R', keysymbol='82TSLA', exchcd='82', symbol='TSLA') plus
      neutral placeholder numerics.
"""

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3101RequestHeader(BlockRequestHeader):
    """g3101 request header. Inherits the standard LS request header schema."""
    pass


class G3101ResponseHeader(BlockResponseHeader):
    """g3101 response header. Inherits the standard LS response header schema."""
    pass


class G3101InBlock(BaseModel):
    """g3101InBlock — input block for the current-price snapshot query."""

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
            "(e.g., '82TSLA' = NASDAQ + TSLA). Length not declared in "
            "available source."
        ),
        examples=["82TSLA", "82AAPL"],
    )
    exchcd: Literal["81", "82"] = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description=(
            "Exchange code. '81' = NYSE / AMEX (뉴욕/아멕스), '82' = NASDAQ "
            "(나스닥)."
        ),
        examples=["82", "81"],
    )
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA', 'AAPL').",
        examples=["TSLA", "AAPL"],
    )


class G3101Request(BaseModel):
    """g3101 full request envelope (header + body + setup options)."""

    header: G3101RequestHeader = Field(
        G3101RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3101",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: Dict[Literal["g3101InBlock"], G3101InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3101InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3101"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3101OutBlock(BaseModel):
    """g3101OutBlock — current-price snapshot response.

    Decimal scale and currency unit are not declared in the source
    available to this codebase. The ``floatpoint`` field describes the
    decimal-place convention LS uses for the price strings.
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
        description=(
            "Echoed exchange code. '81' = NYSE / AMEX (뉴욕/아멕스), '82' = "
            "NASDAQ (나스닥)."
        ),
        examples=["82", "81"],
    )
    exchange: str = Field(
        default="",
        title="거래소ID (Exchange ID)",
        description="LS internal exchange identifier string.",
        examples=["NASDAQ", "NYSE"],
    )
    suspend: Literal["Y", "N"] = Field(
        default="N",
        title="거래상태 (Trading suspend flag)",
        description="Trading suspend flag. 'Y' = suspended (정지), 'N' = normal (보통).",
        examples=["N", "Y"],
    )
    sellonly: Literal[0, 1, 2] = Field(
        default=0,
        title="매매구분 (Trade-side restriction)",
        description=(
            "Trade-side restriction. 0 = both sides allowed (매매가능), "
            "1 = sell-only (매도만가능), 2 = no trading (매매불가)."
        ),
        examples=[0, 1, 2],
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
    induname: str = Field(
        default="",
        title="업종한글명 (Industry name in Korean)",
        description="Industry / sector name in Korean.",
        examples=["자동차"],
    )
    low52p: str = Field(
        default="",
        title="52주최저가 (52-week low price)",
        description=(
            "Lowest traded price across the trailing 52 weeks as a string. "
            "Decimal scale not declared in available source."
        ),
        examples=["100.50"],
    )
    floatpoint: str = Field(
        default="",
        title="소숫점자릿수 (Decimal places)",
        description="Number of decimal places LS applies to the price strings.",
        examples=["4", "2"],
    )
    currency: str = Field(
        default="",
        title="외환코드 (Currency code)",
        description="ISO-style currency code for the price quotation.",
        examples=["USD"],
    )
    price: str = Field(
        default="",
        title="현재가 (Current price)",
        description=(
            "Latest traded price as a string. Decimal scale not declared in "
            "available source; the ``floatpoint`` field on this block "
            "indicates the LS-reported decimal-place count."
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
    high52p: str = Field(
        default="",
        title="52주최고가 (52-week high price)",
        description=(
            "Highest traded price across the trailing 52 weeks as a string."
        ),
        examples=["350.00"],
    )
    uplimit: str = Field(
        default="",
        title="상한가 (Upper limit price)",
        description="Upper price limit for the trading day. May be empty when LS does not enforce a limit.",
        examples=["", "275.50"],
    )
    dnlimit: str = Field(
        default="",
        title="하한가 (Lower limit price)",
        description="Lower price limit for the trading day. May be empty when LS does not enforce a limit.",
        examples=["", "224.50"],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Open price)",
        description="Opening price of the day. Decimal scale not declared in available source.",
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
    perv: str = Field(
        default="",
        title="PER (Price-to-earnings ratio)",
        description=(
            "Price-to-earnings ratio as a string. Scale and computation "
            "basis not declared in available source."
        ),
        examples=["25.50"],
    )
    epsv: str = Field(
        default="",
        title="EPS (Earnings per share)",
        description=(
            "Earnings per share as a string. Currency and scale not "
            "declared in available source."
        ),
        examples=["9.80"],
    )


class G3101Response(BaseModel):
    """g3101 full response envelope."""

    header: Optional[G3101ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3101OutBlock] = Field(
        None,
        title="기본 응답 블록 (Snapshot block)",
        description="Current-price snapshot block.",
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
