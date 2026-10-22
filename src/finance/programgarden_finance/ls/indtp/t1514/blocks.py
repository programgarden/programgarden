"""Pydantic models for LS Securities OpenAPI t1514 (업종기간별추이 / sector period trend).

t1514 returns a **time series** for one market sector / index: for each
period (daily / weekly / monthly) it reports the sector index OHLC, the
previous-day change, traded volume / value, the market-breadth counts
(advancing / unchanged / declining / limit-up / limit-down issue counts),
foreign & institutional net-buy volume, the trading weight and the sector
dividend yield. Pagination is via the ``cts_date`` continuation cursor.

REST endpoint: ``POST /indtp/market-data`` (``KOREA_STOCK_INDTP_URL``),
shared with the other 업종(sector) TRs (t1511 / t1516).

The response carries:
    - ``t1514OutBlock`` (``block``) — continuation cursor only (``cts_date``).
      Set on the response **only when more data is available**; feed it back
      into ``T1514InBlock.cts_date`` on the next request.
    - ``t1514OutBlock1`` (``block1``) — list of period rows (one per date).

AI-chatbot field-disambiguation note (IMPORTANT — read before mapping fields):
    Several fields whose Korean labels look price-like are actually
    **market-breadth issue counts for the sector, NOT prices**:
        - ``high`` (상승)  = number of *advancing* issues in the sector
        - ``unchg`` (보합) = number of *unchanged* issues
        - ``low`` (하락)   = number of *declining* issues
        - ``up`` (상한)    = number of *limit-up* issues
        - ``down`` (하한)  = number of *limit-down* issues
        - ``totjo`` (종목수) = total number of issues in the sector
    The sector's actual index level / OHLC lives in ``jisu`` (현재/종가
    지수), ``openjisu`` (시가), ``highjisu`` (고가), ``lowjisu`` (저가) —
    note the ``...jisu`` suffix. Do **not** confuse ``high``/``low`` (counts)
    with ``highjisu``/``lowjisu`` (index high/low).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English; the Korean source label is appended in parentheses for AI
      chatbot Korean↔English mapping.
    - ``sign`` direction code ('1'..'5') mirrors the LS convention used in
      neighbouring sector TRs (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).
    - ``gubun1`` is declared "미사용항목 (unused)" by LS — send a single space.
    - ``gubun2`` period-type maps 1=일(daily) / 2=주(weekly) / 3=월(monthly);
      the LS source also lists a "분" (period) type whose numeric code is NOT
      enumerated in the available source — not guessed here (no-inference).
    - The distinction between ``value1`` (거래대금1) and ``value2``
      (거래대금2), and the currency unit of both, are NOT declared in the
      available source; consume as returned by LS.
    - ``rate`` (거래비중) meaning depends on the request's ``rate_gbn``
      (1=거래량비중 / 2=거래대금비중) — see that field.
    - ``frgsvolume`` (외인순매수) / ``orgsvolume`` (기관순매수) sign
      convention (positive = net buy / negative = net sell) is NOT declared
      in the available source; consume as returned by LS.
    - ``diff_vol`` (거래증가율) baseline (vs prior day vs average vs session)
      is NOT declared in the available source.
    - Decimal scale of the ``...jisu`` index fields and the time ordering of
      ``OutBlock1`` rows are NOT declared in the available source; consume as
      returned by LS.
    - OutBlock1 ``examples`` are the literal values from the LS REST sample
      response (upcode '001', date 20230605).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ...models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1514RequestHeader(BlockRequestHeader):
    """t1514 request header. Inherits the standard LS request header schema."""
    pass


class T1514ResponseHeader(BlockResponseHeader):
    """t1514 response header. Inherits the standard LS response header schema."""
    pass


class T1514InBlock(BaseModel):
    """t1514InBlock — input block for the sector period-trend query."""

    upcode: str = Field(
        ...,
        title="업종코드 (Sector code)",
        description=(
            "Market sector / index code (3 digits). E.g. '001' = KOSPI "
            "composite (코스피 종합). The full sector-code table is not "
            "enumerated in the available source; consume codes published by LS."
        ),
        examples=["001", "002"],
    )
    gubun1: str = Field(
        default=" ",
        title="구분1 (Reserved — unused)",
        description="Declared '미사용항목 (unused)' by LS. Always send a single space ' '.",
        examples=[" "],
    )
    gubun2: str = Field(
        default="1",
        title="구분2 (Period type)",
        description=(
            "Period type for the trend series. '1' = 일 (daily), '2' = 주 "
            "(weekly), '3' = 월 (monthly). The LS source also lists a '분' "
            "(period) type whose numeric code is not enumerated in the "
            "available source."
        ),
        examples=["1", "2", "3"],
    )
    cts_date: str = Field(
        default="",
        title="CTS_일자 (Continuation date)",
        description=(
            "Continuation cursor for paged queries. Empty (or a single space) "
            "on the first request; on follow-ups, pass back the ``cts_date`` "
            "returned in the previous response's ``block``. Treat as an opaque "
            "LS-defined token."
        ),
        examples=["", "20230605"],
    )
    cnt: int = Field(
        default=20,
        title="조회건수 (Requested row count)",
        description="Number of period rows to request per page.",
        examples=[1, 20],
    )
    rate_gbn: Literal["1", "2"] = Field(
        default="1",
        title="비중구분 (Weight basis)",
        description=(
            "Basis used to compute the ``rate`` (거래비중) output field. "
            "'1' = 거래량비중 (volume weight), '2' = 거래대금비중 (trading-value "
            "weight)."
        ),
        examples=["1", "2"],
    )


class T1514Request(BaseModel):
    """t1514 request envelope."""

    header: T1514RequestHeader = T1514RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1514",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1514InBlock"], T1514InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1514"
    )


class T1514OutBlock(BaseModel):
    """t1514OutBlock — continuation cursor block (present only when more data exists)."""

    cts_date: str = Field(
        default="",
        title="CTS_일자 (Continuation date)",
        description=(
            "Continuation key. Populated by LS only when a further page is "
            "available; pass it back as ``T1514InBlock.cts_date`` to fetch the "
            "next page. Empty when there is no more data."
        ),
        examples=["20230605", ""],
    )


class T1514OutBlock1(BaseModel):
    """t1514OutBlock1 — one period row in the sector trend series."""

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Period date in 'YYYYMMDD' format.",
        examples=["20230605"],
    )
    jisu: float = Field(
        default=0.0,
        title="지수 (Sector index value)",
        description="Sector index level for this period — the period close (the live/current index value for an in-session row). Decimal scale not declared in the available source; consume as returned by LS.",
        examples=[2610.62],
    )
    sign: str = Field(
        default="",
        title="전일대비구분 (Previous-day direction code)",
        description="Direction code per LS convention ('1'..'5'; 1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락).",
        examples=["2", "3", "5"],
    )
    change: float = Field(
        default=0.0,
        title="전일대비 (Previous-day delta)",
        description="Magnitude of index change versus the previous day's close (per LS label 전일대비). Pair with ``sign`` for direction.",
        examples=[9.26, 0.0],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Change percent)",
        description="Percent change of the sector index versus the previous day's close.",
        examples=[0.36, -0.50],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Trading volume)",
        description="Traded volume of the sector for this period.",
        examples=[263165],
    )
    diff_vol: float = Field(
        default=0.0,
        title="거래증가율 (Volume-growth percent)",
        description="Volume-growth percent. Baseline (vs prior period vs average vs session) not declared in the available source; consume as returned by LS.",
        examples=[46.20, -5.30],
    )
    value1: int = Field(
        default=0,
        title="거래대금1 (Trading value 1)",
        description="Sector trading value (variant 1). Distinction from ``value2`` and currency unit not declared in the available source; consume as returned by LS.",
        examples=[3884240],
    )
    high: int = Field(
        default=0,
        title="상승 (Advancing-issue count)",
        description="Number of ADVANCING issues in the sector for this period — a breadth count, NOT a price.",
        examples=[606],
    )
    unchg: int = Field(
        default=0,
        title="보합 (Unchanged-issue count)",
        description="Number of UNCHANGED issues in the sector for this period — a breadth count, NOT a price.",
        examples=[91],
    )
    low: int = Field(
        default=0,
        title="하락 (Declining-issue count)",
        description="Number of DECLINING issues in the sector for this period — a breadth count, NOT a price.",
        examples=[253],
    )
    uprate: float = Field(
        default=0.0,
        title="상승종목비율 (Advancing-issue ratio)",
        description="Percent of issues in the sector that advanced this period.",
        examples=[63.79],
    )
    frgsvolume: int = Field(
        default=0,
        title="외인순매수 (Foreign net buy)",
        description="Foreign-investor net-buy volume for the sector. Sign convention (positive = net buy / negative = net sell) not declared in the available source; consume as returned by LS.",
        examples=[351, -120, 0],
    )
    openjisu: float = Field(
        default=0.0,
        title="시가 (Sector index open)",
        description="Sector index OPEN level for this period. Decimal scale not declared in the available source.",
        examples=[2617.43],
    )
    highjisu: float = Field(
        default=0.0,
        title="고가 (Sector index high)",
        description="Sector index HIGH level for this period (intraperiod high of the index, NOT an issue count).",
        examples=[2617.58],
    )
    lowjisu: float = Field(
        default=0.0,
        title="저가 (Sector index low)",
        description="Sector index LOW level for this period (intraperiod low of the index, NOT an issue count).",
        examples=[2610.40],
    )
    value2: int = Field(
        default=0,
        title="거래대금2 (Trading value 2)",
        description="Sector trading value (variant 2). Distinction from ``value1`` and currency unit not declared in the available source; consume as returned by LS.",
        examples=[3884240],
    )
    up: int = Field(
        default=0,
        title="상한 (Limit-up issue count)",
        description="Number of LIMIT-UP issues in the sector for this period — a breadth count, NOT a price.",
        examples=[0, 5],
    )
    down: int = Field(
        default=0,
        title="하한 (Limit-down issue count)",
        description="Number of LIMIT-DOWN issues in the sector for this period — a breadth count, NOT a price.",
        examples=[0, 3],
    )
    totjo: int = Field(
        default=0,
        title="종목수 (Total issue count)",
        description="Total number of issues in the sector for this period — a breadth count, NOT a price.",
        examples=[950],
    )
    orgsvolume: int = Field(
        default=0,
        title="기관순매수 (Institutional net buy)",
        description="Institutional net-buy volume for the sector. Sign convention not declared in the available source; consume as returned by LS.",
        examples=[1210, -800, 0],
    )
    upcode: str = Field(
        default="",
        title="업종코드 (Sector code)",
        description="Sector code echoed back for this row (matches the requested ``upcode``).",
        examples=["001"],
    )
    rate: float = Field(
        default=0.0,
        title="거래비중 (Trading weight percent)",
        description="Sector trading-weight percent. Basis depends on the request's ``rate_gbn`` (1=거래량비중 / 2=거래대금비중).",
        examples=[0.00, 12.50],
    )
    divrate: float = Field(
        default=0.0,
        title="업종배당수익률 (Sector dividend yield)",
        description="Sector dividend yield (percent).",
        examples=[0.00, 1.85],
    )


class T1514Response(BaseModel):
    """t1514 response envelope."""

    header: Optional[T1514ResponseHeader] = None
    block: Optional[T1514OutBlock] = Field(
        None,
        title="연속 데이터 (Continuation block)",
        description="Continuation cursor (``cts_date``); present only when more data is available.",
    )
    block1: List[T1514OutBlock1] = Field(
        default_factory=list,
        title="기간별 추이 (Period rows)",
        description="List of period rows (one per date) for the sector trend series.",
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
