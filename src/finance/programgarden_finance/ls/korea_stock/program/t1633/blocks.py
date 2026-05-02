"""Pydantic models for LS Securities OpenAPI t1633 (Korea Stock Program Trading Period Trend).

t1633 returns daily / weekly / monthly program-trading flow (KP200 jisu,
sign, change, total / arbitrage / non-arbitrage buy, sell, net-buy, and
volume) over an [fdate, tdate] period for the KOSPI exchange
(``gubun='0'``) or KOSDAQ market (``gubun='1'``).

Key design notes:

- ``T1633Response.cont_block`` — continuation marker only (date + idx).
  Carries no market data of its own. Use ``cont_block.date`` in the next
  request's ``date`` field when ``tr_cont='Y'``. Unlike t1632 which pages
  by date + time, t1633 pages by **date alone** — there is no ``time``
  cursor.
- ``T1633Response.block`` — Object Array of period-bucketed rows
  (one row per day / week / month depending on ``gubun3``). The LS
  public spec documents only the per-row field schema. The meaning of
  an individual row, the ordering of the array, and any server-side
  arithmetic identity between fields (e.g., between ``tot1`` / ``tot2``
  / ``tot3``) are not documented by LS — consume the array as reported.
- ``gubun`` encoding: ``'0'`` = KOSPI exchange (거래소), ``'1'`` = KOSDAQ.
  This matches t1632 but is **OPPOSITE of t1631** which uses ``'1'`` for
  거래소 and ``'2'`` for KOSDAQ. Do not copy-paste t1631 inputs verbatim
  into this TR.
- ``gubun2`` / ``gubun3`` enum domains differ from t1632:
    - t1632 fixes both at ``Literal['1']``.
    - t1633 ``gubun2`` accepts ``'0'`` (수치) and ``'1'`` (누적).
    - t1633 ``gubun3`` accepts ``'1'`` (일), ``'2'`` (주), ``'3'`` (월).
- ``gubun4`` is unique to t1633 (Default ``'0'`` vs ``'1'`` 직전대비증감).
- ``fdate`` / ``tdate`` are required period bounds (YYYYMMDD, 8 numeric
  digits) — enforced via ``pattern=r"^\\d{8}$"`` to reject typos and
  non-numeric inputs immediately.
- First request must send ``date=' '`` (single space) per the LS official
  example payload — modelled as the default value.
- The ``sign`` row field has a per-xingAPI documented enum
  (1=상한 / 2=상승 / 3=보합 / 4=하한 / 5=하락). The LS REST spec does
  not officially restate this code domain — modelled as ``str`` to match
  whatever the REST API returns; the xingAPI mapping is included in the
  description as a hint only.
- Inferred formulas, units, or row ordering that are not in the LS public
  spec are intentionally omitted — consume every value as reported by LS.

Field descriptions follow LS official spec wording verbatim. Korean field
labels (한글명) are appended in parentheses so AI chatbots can map between
English descriptions and Korean LS documentation.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1633RequestHeader(BlockRequestHeader):
    """t1633 request header. Inherits the standard LS request header schema."""
    pass


class T1633ResponseHeader(BlockResponseHeader):
    """t1633 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T1633InBlock(BaseModel):
    """t1633InBlock — input block for period-based program-trading trend query.

    Selects the market (``gubun``: 거래소 vs KOSDAQ), the amount/quantity
    mode (``gubun1``), the value-vs-cumulative mode (``gubun2``), the
    period unit (``gubun3``: daily / weekly / monthly), the period bounds
    (``fdate`` / ``tdate``), the prior-period change flag (``gubun4``),
    the continuation date cursor (``date``), and the exchange filter
    (``exchgubun``).

    WARNING: ``gubun`` encoding matches t1632 ('0' = KOSPI exchange,
    '1' = KOSDAQ) but is **OPPOSITE of t1631** ('1' = KOSPI exchange,
    '2' = KOSDAQ). ``gubun2`` and ``gubun3`` enum domains also differ
    from t1632 (which fixes both at ``Literal['1']``) — see field
    descriptions for details.
    """

    gubun: Literal["0", "1"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. '0' = 거래소 (KOSPI exchange / KRX), "
            "'1' = 코스닥 (KOSDAQ). Required. "
            "NOTE: encoding matches t1632 but is OPPOSITE to t1631 — "
            "t1631 uses '1' for 거래소 and '2' for KOSDAQ. "
            "Do not copy-paste t1631 inputs here."
        ),
        examples=["0", "1"],
    )
    gubun1: Literal["0", "1"] = Field(
        ...,
        title="금액수량구분 (Amount/quantity mode)",
        description=(
            "Amount or quantity mode. '0' = 금액 (amount), "
            "'1' = 수량 (quantity). Required."
        ),
        examples=["0", "1"],
    )
    gubun2: Literal["0", "1"] = Field(
        default="0",
        title="수치누적구분 (Value/cumulative mode)",
        description=(
            "Value or cumulative mode. '0' = 수치 (raw value), "
            "'1' = 누적 (cumulative). Both values are valid per LS spec. "
            "Differs from t1632 which fixes this field at Literal['1']. "
            "Defaults to '0'."
        ),
        examples=["0", "1"],
    )
    gubun3: Literal["1", "2", "3"] = Field(
        default="1",
        title="일주월구분 (Period unit)",
        description=(
            "Period unit selector. '1' = 일 (daily), '2' = 주 (weekly), "
            "'3' = 월 (monthly). All three values valid per LS spec. "
            "Differs from t1632 which fixes this field at Literal['1']. "
            "Defaults to '1'."
        ),
        examples=["1", "2", "3"],
    )
    fdate: str = Field(
        ...,
        title="from일자 (From-date YYYYMMDD)",
        description=(
            "From-date period bound. YYYYMMDD format, 8 numeric digits. "
            "Strict pattern (^\\d{8}$) rejects typos and non-numeric inputs "
            "(e.g., '2023-01-01', '202301', 'abcdefgh') immediately. Required."
        ),
        examples=["20230101", "20230619", "19990101"],
        pattern=r"^\d{8}$",
    )
    tdate: str = Field(
        ...,
        title="to일자 (To-date YYYYMMDD)",
        description=(
            "To-date period bound. YYYYMMDD format, 8 numeric digits. "
            "Strict pattern (^\\d{8}$) rejects typos and non-numeric inputs "
            "immediately. Must form a valid range with ``fdate`` (server-side "
            "validation by LS — not enforced client-side). Required."
        ),
        examples=["20230619", "20231231", "20240101"],
        pattern=r"^\d{8}$",
    )
    gubun4: Literal["0", "1"] = Field(
        default="0",
        title="직전대비증감구분 (Prior-period change mode)",
        description=(
            "Prior-period change mode. '0' = Default (raw value), "
            "'1' = 직전대비증감 (change from prior period). t1632 has no "
            "equivalent field. Defaults to '0'."
        ),
        examples=["0", "1"],
    )
    date: str = Field(
        default=" ",
        title="날짜CTS (Date continuation cursor)",
        description=(
            "Date continuation cursor. Length 8 (YYYYMMDD) for subsequent "
            "pages, or a single space ' ' for the first request. "
            "Per the LS official example payload, the first request uses "
            "exactly one space character (NOT empty string). For subsequent "
            "pages use the value from ``T1633OutBlock.date`` (the "
            "continuation marker returned in the previous response). "
            "Unlike t1632 which pages by date + time, t1633 pages by date "
            "alone — there is no ``time`` cursor."
        ),
        examples=[" ", "20230102", "20230619"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = 통합 "
            "(unified). Per LS spec, any other value is treated as KRX "
            "server-side. Defaults to 'K'."
        ),
        examples=["K", "N", "U"],
    )


class T1633Request(BaseModel):
    """t1633 full request envelope (header + body + setup options)."""

    header: T1633RequestHeader = T1633RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1633",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1633InBlock"], T1633InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1633",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1633OutBlock(BaseModel):
    """t1633OutBlock — continuation marker for tr_cont paging.

    Unlike ``T1631OutBlock`` (which carries market-wide order aggregates),
    this block is a **pagination cursor only**. Pass ``date`` into the
    next request's ``T1633InBlock.date`` field when ``tr_cont='Y'``.

    Has only 2 fields (``date`` + ``idx``) — fewer than t1632's 4-field
    cont block (which adds ``time`` + ``ex_gubun``).
    """

    date: str = Field(
        default="",
        title="날짜CTS (Date continuation cursor)",
        description=(
            "Date continuation cursor. Length 8 (YYYYMMDD). Used to "
            "request the next page when ``tr_cont='Y'``. Empty string "
            "when not continuing."
        ),
        examples=["20230102", ""],
    )
    idx: int = Field(
        default=0,
        title="IDX (Continuation index)",
        description=(
            "Internal continuation index returned by LS. Length 4. "
            "Scale and exact role are not documented by LS — consume as "
            "reported. Not fed back into subsequent requests (t1633 pages "
            "by ``date`` only)."
        ),
        examples=[115, 0],
    )


class T1633OutBlock1(BaseModel):
    """t1633OutBlock1 — period-bucketed program-trading trend rows.

    Object Array. The LS public spec documents only the per-row field
    schema. The meaning of an individual row, the ordering of the array,
    and any server-side arithmetic identity between fields (e.g., between
    ``tot1`` / ``tot2`` / ``tot3``, or between ``cha1`` / ``cha2`` /
    ``cha3``, or between ``bcha1`` / ``bcha2`` / ``bcha3``) are not
    documented by LS — consume the array as reported.

    Differs from ``T1632OutBlock1``:
      - uses ``date`` instead of ``time``;
      - uses ``jisu`` instead of ``k200jisu``;
      - has no BASIS field (``k200basis``);
      - has an additional ``volume`` field.
    """

    date: str = Field(
        default="",
        title="일자 (Trade date YYYYMMDD)",
        description="Trade date for this row. Length 8 (YYYYMMDD).",
        examples=["20230619", "20230616"],
    )
    jisu: float = Field(
        default=0.0,
        title="KP200 (KP200 index value)",
        description=(
            "KP200 index value for this period bucket. Length 6.2 (LS "
            "scale). LS may serialise this as a zero-padded string "
            "(e.g., '329.85') — Pydantic auto-coerces to float."
        ),
        examples=[329.85, 345.17, 1006.59],
    )
    sign: str = Field(
        default="",
        title="대비구분 (Change sign)",
        description=(
            "Change direction indicator. Length 1. Per the xingAPI "
            "companion documentation: '1' = 상한 (limit-up), "
            "'2' = 상승 (up), '3' = 보합 (unchanged), "
            "'4' = 하한 (limit-down), '5' = 하락 (down). Whether the "
            "LS REST API returns the same code domain is not officially "
            "restated in the REST spec — consume the raw value as "
            "reported and validate against this xingAPI mapping "
            "defensively."
        ),
        examples=["2", "5", "3"],
    )
    change: float = Field(
        default=0.0,
        title="대비 (Change from prior)",
        description=(
            "Change from the prior period. Length 6.2 (LS scale). LS may "
            "serialise this as a zero-padded string (e.g., '016.32') — "
            "Pydantic auto-coerces to float."
        ),
        examples=[16.32, 1.98, 0.0, -2.30],
    )
    tot3: int = Field(
        default=0,
        title="전체순매수 (Total net-buy)",
        description=(
            "Total net-buy for this period bucket. Length 12. The LS "
            "spec does not publish a server-side computation formula — "
            "consume as reported."
        ),
        examples=[6441, 391, 0],
    )
    tot1: int = Field(
        default=0,
        title="전체매수 (Total buy)",
        description="Total buy for this period bucket. Length 12.",
        examples=[6921, 917, 0],
    )
    tot2: int = Field(
        default=0,
        title="전체매도 (Total sell)",
        description="Total sell for this period bucket. Length 12.",
        examples=[480, 526, 0],
    )
    cha3: int = Field(
        default=0,
        title="차익순매수 (Arbitrage net-buy)",
        description=(
            "Arbitrage net-buy for this period bucket. Length 12. The LS "
            "spec does not publish a server-side computation formula — "
            "consume as reported."
        ),
        examples=[0, 109],
    )
    cha1: int = Field(
        default=0,
        title="차익매수 (Arbitrage buy)",
        description="Arbitrage buy for this period bucket. Length 12.",
        examples=[0, 109],
    )
    cha2: int = Field(
        default=0,
        title="차익매도 (Arbitrage sell)",
        description="Arbitrage sell for this period bucket. Length 12.",
        examples=[0],
    )
    bcha3: int = Field(
        default=0,
        title="비차익순매수 (Non-arbitrage net-buy)",
        description=(
            "Non-arbitrage net-buy for this period bucket. Length 12. "
            "The LS spec does not publish a server-side computation "
            "formula — consume as reported."
        ),
        examples=[6441, 282, 0],
    )
    bcha1: int = Field(
        default=0,
        title="비차익매수 (Non-arbitrage buy)",
        description="Non-arbitrage buy for this period bucket. Length 12.",
        examples=[6921, 808, 0],
    )
    bcha2: int = Field(
        default=0,
        title="비차익매도 (Non-arbitrage sell)",
        description="Non-arbitrage sell for this period bucket. Length 12.",
        examples=[480, 526, 0],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description=(
            "Trading volume for this period bucket. Length 12. Unit and "
            "exact aggregation scope (e.g., whether ``volume`` matches "
            "``tot1 + tot2`` or any other identity) are not published by "
            "LS — consume as reported. t1632 has no equivalent field."
        ),
        examples=[245, 153589, 0],
    )


class T1633Response(BaseModel):
    """t1633 full API response envelope."""

    header: Optional[T1633ResponseHeader] = None
    cont_block: Optional[T1633OutBlock] = Field(
        default=None,
        title="t1633OutBlock (Continuation marker)",
        description=(
            "Continuation cursor for tr_cont paging. Present when the "
            "response contains data. Use ``cont_block.date`` in the next "
            "request when ``tr_cont='Y'``."
        ),
    )
    block: List[T1633OutBlock1] = Field(
        default_factory=list,
        title="t1633OutBlock1 (Period-bucketed program-trading trend rows)",
        description=(
            "Result rows as reported by LS. Row meaning and array "
            "ordering are not documented in the LS public spec."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
