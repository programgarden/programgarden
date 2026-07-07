"""Pydantic models for LS Securities OpenAPI t8409 (업종차트(N분) / sector N-minute chart).

t8409 returns an **N-minute chart** for one market sector / index. The
response is a two-block chart envelope:
    - ``t8409OutBlock`` (``cont_block``) — metadata + continuation cursor:
      previous-day and today's sector index OHLC, previous-day volume, today's
      cumulative traded value, the continuation cursors (``cts_date`` /
      ``cts_time``), session start/end times and the record count. Present only
      while more data is available.
    - ``t8409OutBlock1`` (``block``) — list of N-minute bars (one row per bar),
      each carrying the bar date/time, the bar OHLC, the traded volume and the
      traded value.

Bar interval is selected via ``T8409InBlock.ncnt``: '0' = 30 seconds,
'1' = 1-minute, 'n' = n-minute.

Pagination is via the ``cts_date`` / ``cts_time`` continuation cursors (feed
the previous response's ``cont_block.cts_date`` / ``cont_block.cts_time`` back
into the next request's InBlock).

REST endpoint: ``POST /indtp/chart`` (``KOREA_STOCK_INDTP_CHART_URL``) — the
**same** endpoint as t8408 (업종차트 틱/n틱). This is a **distinct** endpoint
from the 업종(sector) market-data TRs (t1511 / t1514 / t1516), which route to
``/indtp/market-data``.

AI-chatbot field-disambiguation note (IMPORTANT — read before mapping fields):
    Every OHLC value in this TR is a **sector INDEX level (index points),
    NOT a KRW price**. The previous-day OHLC (``jisiga`` / ``jihigh`` /
    ``jilow`` / ``jiclose``), today's OHLC (``disiga`` / ``dihigh`` /
    ``dilow`` / ``diclose``) and each bar's OHLC (``open`` / ``high`` /
    ``low`` / ``close``) are all index points. Do **not** interpret them as
    won prices.

Unit cross-check note (IMPORTANT — value / volume units are NOT declared by LS):
    LS does not formally declare the units of the traded-value fields
    (``disvalue`` / ``value``) or the volume fields (``jivolume`` /
    ``jdiff_vol``). They were cross-checked from the LS sample response:
    ``value ÷ jdiff_vol`` yields ~10,000–14,000, i.e. a plausible KOSPI
    volume-weighted average price in KRW per share, only when
    ``value`` is in **millions of KRW (백만원)** and ``jdiff_vol`` is in
    **thousands of shares (천주)**. That scale also reproduces a ~7.5 trillion
    KRW / day KOSPI turnover and a ~570-million-share prev-day volume, matching
    2023-06 KOSPI figures. The same units apply to ``disvalue`` (백만원) and
    ``jivolume`` (천주). These are cross-checked, **not** formally declared by
    LS spec — descriptions say so.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas``):
    - Index OHLC fields are typed ``float``. LS may serialize these values as
      JSON strings ("2610.97"); Pydantic v2 auto-coerces them to ``float``.
    - LS declares an OHLC scale of 10.2 for the index fields.
    - ``stime`` / ``etime`` are 'HHMMSS' placeholders declared currently
      unused per LS spec; not guessed here (no-inference).
    - ``dshmin`` carries the LS label '분(minutes)'; its exact semantics are
      not further declared by LS spec (declared length 2 only) — not guessed.
    - ``cts_time`` declared length is 10; treat continuation cursors as opaque
      LS-defined tokens.
    - OutBlock / OutBlock1 ``examples`` are the literal values from the LS REST
      sample response (shcode '001', date 20230605).

Added by LS Securities on 2026-06-04.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ...models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8409RequestHeader(BlockRequestHeader):
    """t8409 request header. Inherits the standard LS request header schema."""
    pass


class T8409ResponseHeader(BlockResponseHeader):
    """t8409 response header. Inherits the standard LS response header schema."""
    pass


class T8409InBlock(BaseModel):
    """t8409InBlock — input block for the sector N-minute-chart query (all fields required)."""

    shcode: str = Field(
        ...,
        title="단축코드 (Sector code)",
        description=(
            "Sector / index code (3 digits). LS example '001' = KOSPI "
            "composite. The full sector-code table is not enumerated in the "
            "available source; consume codes published by LS."
        ),
        examples=["001"],
    )
    ncnt: int = Field(
        ...,
        title="단위 (Bar interval)",
        description=(
            "Bar interval code. '0' = 30 seconds (30초), '1' = 1-minute (1분), "
            "'2' = 2-minute, …, 'n' = n-minute. Declared length 4."
        ),
        examples=[0, 1, 5],
    )
    qrycnt: int = Field(
        ...,
        title="요청건수 (Requested row count)",
        description=(
            "Number of rows to request per page. Max 2000 (compressed) / "
            "500 (non-compressed). Declared length 4."
        ),
        examples=[5, 500],
    )
    nday: str = Field(
        ...,
        title="조회영업일수 (Business-day query mode)",
        description=(
            "'0' = unused; '>= 1' = number of business days to query. "
            "Declared length 1."
        ),
        examples=["0", "1"],
    )
    sdate: str = Field(
        default=" ",
        title="시작일자 (Start date)",
        description=(
            "Start date in 'YYYYMMDD' format. Default a single space ' ' (LS "
            "spec). When set, queries ``qrycnt`` rows back from ``edate``; set "
            "for range filtering."
        ),
        examples=[" ", "20230605"],
    )
    stime: str = Field(
        default="",
        title="시작시간 (Start time)",
        description="Start time 'HHMMSS' placeholder. Currently unused per LS spec.",
        examples=[""],
    )
    edate: str = Field(
        ...,
        title="종료일자 (End date)",
        description=(
            "End date in 'YYYYMMDD' format. First-query reference date (less "
            "than or equal to). '99999999' or today."
        ),
        examples=["99999999", "20230605"],
    )
    etime: str = Field(
        default="",
        title="종료시간 (End time)",
        description="End time 'HHMMSS' placeholder. Currently unused per LS spec.",
        examples=[""],
    )
    cts_date: str = Field(
        default=" ",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor (date). Empty (a single space ' ') on the "
            "first request; on follow-ups pass back the previous response's "
            "``cont_block.cts_date``. Treat as an opaque LS-defined token."
        ),
        examples=[" "],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description=(
            "Continuation cursor (time). Declared length 10. Empty on the "
            "first request; on follow-ups pass back the previous response's "
            "``cont_block.cts_time``. Treat as an opaque LS-defined token."
        ),
        examples=[""],
    )
    comp_yn: Literal["N", "Y"] = Field(
        default="N",
        title="압축여부 (Compression flag)",
        description=(
            "'N' = non-compressed (비압축), 'Y' = compressed (압축)."
        ),
        examples=["N", "Y"],
    )


class T8409Request(BaseModel):
    """t8409 request envelope."""

    header: T8409RequestHeader = T8409RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8409",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t8409InBlock"], T8409InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8409"
    )


class T8409OutBlock(BaseModel):
    """t8409OutBlock — metadata + continuation cursor block (present only when more data exists)."""

    shcode: str = Field(
        default="",
        title="단축코드 (Sector code)",
        description="Echoed 3-digit sector code ('001' = KOSPI composite).",
        examples=["001"],
    )
    jisiga: float = Field(
        default=0.0,
        title="전일시가 (Previous-day sector index open)",
        description=(
            "Previous-day sector index OPEN — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2586.27],
    )
    jihigh: float = Field(
        default=0.0,
        title="전일고가 (Previous-day sector index high)",
        description=(
            "Previous-day sector index HIGH — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2601.38],
    )
    jilow: float = Field(
        default=0.0,
        title="전일저가 (Previous-day sector index low)",
        description=(
            "Previous-day sector index LOW — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2583.88],
    )
    jiclose: float = Field(
        default=0.0,
        title="전일종가 (Previous-day sector index close)",
        description=(
            "Previous-day sector index CLOSE — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2601.36],
    )
    jivolume: int = Field(
        default=0,
        title="전일거래량 (Previous-day volume)",
        description=(
            "Previous-day sector traded volume in thousands of shares (천주). "
            "Declared length 12. Unit cross-checked from the LS sample "
            "response; not formally declared by LS spec."
        ),
        examples=[569620],
    )
    disiga: float = Field(
        default=0.0,
        title="당일시가 (Today sector index open)",
        description=(
            "Today's sector index OPEN — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2617.43],
    )
    dihigh: float = Field(
        default=0.0,
        title="당일고가 (Today sector index high)",
        description=(
            "Today's sector index HIGH — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2617.58],
    )
    dilow: float = Field(
        default=0.0,
        title="당일저가 (Today sector index low)",
        description=(
            "Today's sector index LOW — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2610.40],
    )
    diclose: float = Field(
        default=0.0,
        title="당일종가 (Today sector index close)",
        description=(
            "Today's sector index CLOSE / last — index points, NOT a KRW "
            "price. LS scale 10.2. LS may serialize this value as a string; "
            "Pydantic auto-coerces to float."
        ),
        examples=[2610.85],
    )
    disvalue: int = Field(
        default=0,
        title="당일거래대금 (Today sector traded value)",
        description=(
            "Today's cumulative sector traded value in millions of KRW "
            "(백만원). Declared length 12. Unit cross-checked from the LS "
            "sample response (value ÷ volume ⇒ ~10k–14k KRW/share average); "
            "not formally declared by LS spec."
        ),
        examples=[3886266],
    )
    cts_date: str = Field(
        default="",
        title="연속일자 (Continuation date)",
        description=(
            "Continuation cursor (date). Feed back into "
            "``T8409InBlock.cts_date`` on the next request. Opaque token."
        ),
        examples=["20230605", ""],
    )
    cts_time: str = Field(
        default="",
        title="연속시간 (Continuation time)",
        description=(
            "Continuation cursor (time). Declared length 10. Feed back into "
            "``T8409InBlock.cts_time`` on the next request. Opaque token."
        ),
        examples=["102300", ""],
    )
    s_time: str = Field(
        default="",
        title="업종시작시간 (Sector session start time)",
        description="Sector session start time in 'HHMMSS' format.",
        examples=["090000"],
    )
    e_time: str = Field(
        default="",
        title="업종종료시간 (Sector session end time)",
        description="Sector session end time in 'HHMMSS' format.",
        examples=["153000"],
    )
    dshmin: str = Field(
        default="",
        title="동시호가처리시간 (Single-price auction window length)",
        description=(
            "Per LS label '분(minutes)'; exact semantics not further declared "
            "by LS spec; declared length 2 only."
        ),
        examples=["10"],
    )
    rec_count: int = Field(
        default=0,
        title="레코드카운트 (Record count)",
        description="Number of rows in OutBlock1. Declared length 7.",
        examples=[5, 500],
    )


class T8409OutBlock1(BaseModel):
    """t8409OutBlock1 — one N-minute bar in the sector chart."""

    date: str = Field(
        default="",
        title="날짜 (Date)",
        description="Bar date in 'YYYYMMDD' format.",
        examples=["20230605"],
    )
    time: str = Field(
        default="",
        title="시간 (Time)",
        description="Bar time in 'HHMMSS' format.",
        examples=["102400"],
    )
    open: float = Field(
        default=0.0,
        title="시가 (Sector index open)",
        description=(
            "Bar OPEN of the sector index — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2611.42],
    )
    high: float = Field(
        default=0.0,
        title="고가 (Sector index high)",
        description=(
            "Bar HIGH of the sector index — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2611.59],
    )
    low: float = Field(
        default=0.0,
        title="저가 (Sector index low)",
        description=(
            "Bar LOW of the sector index — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2610.75],
    )
    close: float = Field(
        default=0.0,
        title="종가 (Sector index close)",
        description=(
            "Bar CLOSE of the sector index — index points, NOT a KRW price. "
            "LS scale 10.2. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[2610.97],
    )
    jdiff_vol: int = Field(
        default=0,
        title="거래량 (Volume)",
        description=(
            "Traded volume for the bar in thousands of shares (천주). Declared "
            "length 12. Unit cross-checked from the LS sample response; not "
            "formally declared by LS spec."
        ),
        examples=[1673, 0],
    )
    value: int = Field(
        default=0,
        title="거래대금 (Trade value)",
        description=(
            "Traded value for the bar in millions of KRW (백만원). Declared "
            "length 12. Unit cross-checked from the LS sample response "
            "(value ÷ volume ⇒ ~10k–14k KRW/share average); not formally "
            "declared by LS spec."
        ),
        examples=[19176, 0],
    )


class T8409Response(BaseModel):
    """t8409 response envelope."""

    header: Optional[T8409ResponseHeader] = None
    cont_block: Optional[T8409OutBlock] = Field(
        None,
        title="메타/연속 데이터 (Metadata + continuation block)",
        description=(
            "Metadata (previous-day / today index OHLC, previous-day volume, "
            "today's cumulative traded value, session times, record count) and "
            "the continuation cursors (``cts_date`` / ``cts_time``); present "
            "only when more data is available."
        ),
    )
    block: List[T8409OutBlock1] = Field(
        default_factory=list,
        title="N분 차트 행 (N-minute bar rows)",
        description="List of N-minute bars (one per bar) for the sector index chart.",
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
