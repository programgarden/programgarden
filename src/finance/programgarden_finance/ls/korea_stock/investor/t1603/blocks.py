"""Pydantic models for LS Securities OpenAPI t1603 (intraday investor trading detail / 시간대별투자자매매추이상세).

t1603 returns a per-time-bucket detail (buy / sell quantity + buy /
sell value + net-buy quantity + net-buy value) time series for a
single investor category within a single market segment. Unlike t1602,
which collapses each time bucket into a single net-buy column per
investor, t1603 expands one investor category into six detail columns
per bucket. The response carries:

    - ``OutBlock`` (``cont_block``) — continuation cursors
      (``cts_time`` + ``cts_idx``) plus the exchange-specific sector
      code echo.
    - ``OutBlock1`` (``block``) — list of per-time-bucket detail rows.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Decimal scale, currency unit, and time ordering of ``OutBlock1``
      rows are NOT declared in the source available to this codebase;
      consume as returned by LS.
    - Sign convention on ``svolume`` (순매수수량) and ``svalue`` (순매수
      금액) columns is NOT declared in the available source — [+, -, 0]
      examples preserve symmetry.
    - ``cts_time`` (initial: single space per source) and ``cts_idx``
      (initial: 0) are LS continuation cursors; pass back verbatim on
      follow-up requests.
    - ``market`` enum on this TR is offset by one from t1602 (no KP200
      slot here): '1' = 코스피, '2' = 코스닥, '3' = 선물, …
    - ``examples`` for ``InBlock`` come from
      ``src/finance/example/korea_stock/run_t1603.py``
      (``market='1'``, ``gubun1='8'``, ``gubun2='0'`` — ``gubun1='8'``
      maps to '종금' per source enum, not '외국인').
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1603RequestHeader(BlockRequestHeader):
    """t1603 request header. Inherits the standard LS request header schema."""
    pass


class T1603ResponseHeader(BlockResponseHeader):
    """t1603 response header. Inherits the standard LS response header schema."""
    pass


class T1603InBlock(BaseModel):
    """t1603InBlock — input block for the intraday investor-trading detail query."""

    market: Literal["1", "2", "3", "4", "5", "6", "7"] = Field(
        ...,
        title="시장구분 (Market segment)",
        description=(
            "Market segment. '1' = KOSPI (코스피), '2' = KOSDAQ (코스닥), "
            "'3' = futures (선물), '4' = call options (콜옵션), '5' = put "
            "options (풋옵션), '6' = ELW, '7' = ETF. Note: enum slot for "
            "KP200 is absent here — different from t1602."
        ),
        examples=["1", "2", "3"],
    )
    gubun1: Literal["1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C"] = Field(
        ...,
        title="투자자구분 (Investor category)",
        description=(
            "Investor category to query. '1' = individual (개인), '2' = "
            "foreign (외인), '3' = institutional aggregate (기관계), "
            "'4' = securities (증권), '5' = investment trust (투신), "
            "'6' = bank (은행), '7' = insurance (보험), '8' = merchant "
            "bank (종금), '9' = pension / fund (기금), 'A' = state (국가), "
            "'B' = other (기타), 'C' = private fund (사모펀드)."
        ),
        examples=["1", "2", "8"],
    )
    gubun2: Literal["0", "1"] = Field(
        ...,
        title="전일분구분 (Today / previous-day mode)",
        description="Time scope. '0' = today (당일), '1' = previous day (전일).",
        examples=["0", "1"],
    )
    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description=(
            "Continuation cursor for paged queries. Empty (or single space) "
            "on the first request; on follow-ups, pass back the ``cts_time`` "
            "returned in the previous response. Treat as opaque LS-defined token."
        ),
        examples=[""],
    )
    cts_idx: int = Field(
        default=0,
        title="연속키 인덱스 (Continuation index cursor)",
        description="Continuation index. 0 on the first request; pass back the previous response's ``cts_idx`` on follow-ups.",
        examples=[0],
    )
    cnt: int = Field(
        default=20,
        title="조회건수 (Requested row count)",
        description="Number of rows to request per page.",
        examples=[20, 100],
    )
    upcode: str = Field(
        default="",
        title="업종코드 (Sector code)",
        description="Sector / index code; empty queries the full market segment.",
        examples=["", "001"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description="Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = unified.",
        examples=["K", "N", "U"],
    )


class T1603Request(BaseModel):
    """t1603 request envelope."""

    header: T1603RequestHeader = T1603RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1603",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1603InBlock"], T1603InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1603"
    )


class T1603OutBlock(BaseModel):
    """t1603OutBlock — continuation block for the intraday investor-trading detail response."""

    cts_idx: int = Field(
        default=0,
        title="연속키 인덱스 (Continuation index cursor)",
        description="Continuation index for the next paged request.",
        examples=[0, 20, 40],
    )
    cts_time: str = Field(
        default="",
        title="연속키 시간 (Continuation time cursor)",
        description="Continuation time cursor for the next paged request. Empty when no further data.",
        examples=[""],
    )
    ex_upcode: str = Field(
        default="",
        title="거래소별업종코드 (Exchange-specific sector code)",
        description="Exchange-specific sector code echoed for the queried request.",
        examples=["001"],
    )


class T1603OutBlock1(BaseModel):
    """t1603OutBlock1 — per-time-bucket investor-trading detail row.

    The unit of quantity / value columns is determined by the LS
    convention: ``msvolume`` / ``mdvolume`` / ``svolume`` are share
    counts, ``msvalue`` / ``mdvalue`` / ``svalue`` are trade values
    (currency unit not declared in available source).
    """

    time: str = Field(
        default="",
        title="시간 (Time bucket)",
        description="Time bucket label, in 'HHMM' or 'HHMMSS' format per LS convention.",
        examples=["0900", "1000"],
    )
    tjjcode: str = Field(
        default="",
        title="투자자구분 (Investor category code)",
        description="Investor category code echoed for the queried request.",
        examples=["8000"],
    )
    msvolume: int = Field(
        default=0,
        title="매수수량 (Buy quantity)",
        description="Buy quantity for the time bucket, in shares.",
        examples=[150000],
    )
    mdvolume: int = Field(
        default=0,
        title="매도수량 (Sell quantity)",
        description="Sell quantity for the time bucket, in shares.",
        examples=[140000],
    )
    msvalue: int = Field(
        default=0,
        title="매수금액 (Buy value)",
        description="Buy value for the time bucket. Currency unit not declared in available source.",
        examples=[11700000000],
    )
    mdvalue: int = Field(
        default=0,
        title="매도금액 (Sell value)",
        description="Sell value for the time bucket. Currency unit not declared in available source.",
        examples=[10920000000],
    )
    svolume: int = Field(
        default=0,
        title="순매수수량 (Net-buy quantity)",
        description="Net-buy quantity = buy − sell. Sign convention not declared in available source.",
        examples=[10000, -8000, 0],
    )
    svalue: int = Field(
        default=0,
        title="순매수금액 (Net-buy value)",
        description="Net-buy value = buy − sell. Sign convention not declared in available source.",
        examples=[780000000, -500000000, 0],
    )


class T1603Response(BaseModel):
    """t1603 response envelope."""

    header: Optional[T1603ResponseHeader] = None
    cont_block: Optional[T1603OutBlock] = Field(
        None,
        title="연속 데이터 (Continuation block)",
        description="Continuation cursors (cts_time, cts_idx) for paged queries.",
    )
    block: List[T1603OutBlock1] = Field(
        default_factory=list,
        title="시간대별 상세 리스트 (Time-bucket detail list)",
        description="Per-time-bucket investor-trading detail rows.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code returned for the request.",
    )
    rsp_cd: str = ""
    rsp_msg: str = ""
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
