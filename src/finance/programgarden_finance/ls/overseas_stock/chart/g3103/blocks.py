"""Pydantic models for LS Securities OpenAPI g3103 (Overseas Stock day/week/month single-row chart).

g3103 returns a single chart row for the requested period type (day / week /
month) on a given overseas-stock symbol. The response carries:

    - ``OutBlock`` — input echo of the request fields.
    - ``OutBlock1`` — list of chart rows (period close / open / high / low /
      sign / change-vs-prev / volume).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1`` rows
      are NOT declared in the source available to this codebase. Where the
      Korean spec ends with "등" (etc.), the description states "consume as
      returned by LS" rather than inventing additional enum values.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_g3103.py``
      where present.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3103RequestHeader(BlockRequestHeader):
    """g3103 request header. Inherits the standard LS request header schema."""
    pass


class G3103ResponseHeader(BlockResponseHeader):
    """g3103 response header. Inherits the standard LS response header schema."""
    pass


class G3103InBlock(BaseModel):
    """g3103InBlock — input block for the day/week/month single-row chart query."""

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
    exchcd: str = Field(
        ...,
        title="거래소코드 (Exchange code)",
        description=(
            "Exchange code. '82' = NASDAQ (나스닥). Other LS-defined codes "
            "may appear; consume as returned by LS."
        ),
        examples=["82"],
    )
    symbol: str = Field(
        ...,
        title="종목코드 (Symbol / ticker)",
        description="Ticker symbol of the issue (e.g., 'TSLA', 'AAPL').",
        examples=["TSLA", "AAPL"],
    )
    gubun: Literal["2", "3", "4"] = Field(
        ...,
        title="주기구분 (Period type)",
        description="Period type. '2' = daily (일봉), '3' = weekly (주봉), '4' = monthly (월봉).",
        examples=["2", "3", "4"],
    )
    date: str = Field(
        ...,
        title="조회일자 (Query date)",
        description="Query reference date in YYYYMMDD format.",
        examples=["20231001", "20250120"],
    )


class G3103Request(BaseModel):
    """g3103 full request envelope (header + body + setup options)."""

    header: G3103RequestHeader = Field(
        G3103RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="g3103",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["g3103InBlock"], G3103InBlock] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'g3103InBlock'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=2,
            on_rate_limit="wait",
            rate_limit_key="g3103"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class G3103OutBlock(BaseModel):
    """g3103OutBlock — input echo block.

    LS echoes the InBlock inputs back in OutBlock. Use this only for
    verification / continuation handling — the actual chart rows live in
    ``OutBlock1``.
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
    exchcd: str = Field(
        default="",
        title="거래소코드 (Exchange code)",
        description="Echoed exchange code. '82' = NASDAQ.",
        examples=["82"],
    )
    symbol: str = Field(
        default="",
        title="종목코드 (Symbol / ticker)",
        description="Echoed ticker symbol.",
        examples=["TSLA"],
    )
    gubun: Literal["2", "3", "4"] = Field(
        default="2",
        title="주기구분 (Period type)",
        description="Echoed period type. '2' = daily, '3' = weekly, '4' = monthly.",
        examples=["2", "3", "4"],
    )
    date: str = Field(
        default="",
        title="조회일자 (Query date)",
        description="Echoed query reference date in YYYYMMDD format.",
        examples=["20231001"],
    )


class G3103OutBlock1(BaseModel):
    """g3103OutBlock1 — chart row for the requested period.

    Decimal scale, currency unit, and time ordering of consecutive rows are
    not declared in the source available to this codebase — consume as
    returned by LS. The ``floatpoint`` field describes the decimal-place
    convention LS uses for the price string.
    """

    chedate: str = Field(
        default="",
        title="영업일자 (Business / trading date)",
        description="Trading date for the chart row in YYYYMMDD format.",
        examples=["20231001", "20250120"],
    )
    price: str = Field(
        default="",
        title="현재가 (Current / close price)",
        description=(
            "Period price as a string. Decimal scale not declared in "
            "available source; the ``floatpoint`` field on this row indicates "
            "the LS-reported decimal-place count."
        ),
        examples=["1500.00", "150.25"],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Change-vs-previous sign)",
        description=(
            "Sign indicator vs. previous period. '+' = up (상승), '-' = down "
            "(하락). Other LS-defined codes may appear; consume as returned "
            "by LS."
        ),
        examples=["+", "-"],
    )
    diff: str = Field(
        default="",
        title="전일대비 (Change-vs-previous)",
        description=(
            "Absolute change vs. previous period. LS may return this as a "
            "numeric string. Decimal scale not declared in available source."
        ),
        examples=["10.00", "0.5"],
    )
    rate: float = Field(
        default=0.0,
        title="등락률 (Change rate)",
        description=(
            "Percent change vs. previous period. Decimal scale not declared "
            "in available source."
        ),
        examples=[0.0, 0.67],
    )
    volume: int = Field(
        default=0,
        title="누적거래량 (Cumulative volume)",
        description="Cumulative trading volume for the period (shares).",
        examples=[0, 1000000],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Open price)",
        description="Opening price of the period. Decimal scale not declared in available source.",
        examples=[0.0, 1480.00],
    )
    high: float = Field(
        default=0.0,
        title="고가 (High price)",
        description="Highest traded price of the period.",
        examples=[0.0, 1520.00],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Low price)",
        description="Lowest traded price of the period.",
        examples=[0.0, 1470.00],
    )
    floatpoint: str = Field(
        default="",
        title="소숫점자릿수 (Decimal places)",
        description="Number of decimal places LS applies to the price string.",
        examples=["4", "2"],
    )


class G3103Response(BaseModel):
    """g3103 full response envelope."""

    header: Optional[G3103ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block: Optional[G3103OutBlock] = Field(
        None,
        title="기본 응답 블록 (Input echo block)",
        description="Input echo block (mirrors the InBlock inputs).",
    )
    block1: List[G3103OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트 (Chart rows)",
        description="List of chart rows. Time ordering: consume as returned by LS.",
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
