"""Pydantic models for LS Securities OpenAPI t1632 (Korea Stock Program Trading Time-Bucketed Trend).

t1632 returns time-bucketed KP200 index, BASIS, and program-trading flow
(total / arbitrage / non-arbitrage buy, sell, and net-buy) for the
KOSPI exchange (``gubun='0'``) or KOSDAQ market (``gubun='1'``).

Key design notes:

- ``T1632Response.cont_block`` — continuation marker only (date + time + idx
  + ex_gubun). Carries no market data of its own. Use ``cont_block.date``
  and ``cont_block.time`` in the next request's ``date`` / ``time`` fields
  when ``tr_cont='Y'``.
- ``T1632Response.block`` — Object Array of time-bucketed rows. The LS
  public spec documents only the per-row field schema. The meaning of an
  individual row, the ordering of the array, and any server-side arithmetic
  identity between fields (e.g., between ``tot1`` / ``tot2`` / ``tot3``)
  are not documented by LS — consume the array as reported.
- ``gubun`` encoding: ``'0'`` = KOSPI exchange (거래소), ``'1'`` = KOSDAQ.
  **This differs from t1631** which uses ``'1'`` for 거래소 and ``'2'`` for
  KOSDAQ. Do not copy-paste t1631 inputs verbatim into this TR.
- ``gubun2`` / ``gubun3``: The LS spec documents only a single valid value
  (``'1'``) for each. They are modelled as ``Literal["1"]`` with
  ``default='1'`` to reject invalid inputs early.
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


class T1632RequestHeader(BlockRequestHeader):
    """t1632 request header. Inherits the standard LS request header schema."""
    pass


class T1632ResponseHeader(BlockResponseHeader):
    """t1632 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T1632InBlock(BaseModel):
    """t1632InBlock — input block for time-bucketed program-trading trend query.

    Selects the market (``gubun``: 거래소 vs KOSDAQ), the amount/quantity
    mode (``gubun1``), fixed classification fields (``gubun2`` / ``gubun3``),
    the continuation date/time cursor (``date`` / ``time``), and the exchange
    filter (``exchgubun``).

    WARNING: ``gubun`` encoding is **inverted relative to t1631**.
    t1632 uses ``'0'`` for KOSPI (거래소) and ``'1'`` for KOSDAQ.
    t1631 uses ``'1'`` for 거래소 and ``'2'`` for KOSDAQ.
    Do not copy-paste t1631 InBlock inputs into this TR.
    """

    gubun: Literal["0", "1"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. '0' = 거래소 (KOSPI exchange / KRX), "
            "'1' = 코스닥 (KOSDAQ). Required. "
            "NOTE: encoding is OPPOSITE to t1631 — t1631 uses '1' for 거래소 "
            "and '2' for KOSDAQ. Do not copy-paste t1631 inputs here."
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
    gubun2: Literal["1"] = Field(
        default="1",
        title="직전대비증감 (Prior-period change flag)",
        description=(
            "Prior-period change flag. The LS spec documents only '1' "
            "(직전대비증감) as a valid value — modelled as Literal['1'] to "
            "reject any other value immediately. Defaults to '1'."
        ),
        examples=["1"],
    )
    gubun3: Literal["1"] = Field(
        default="1",
        title="전일구분 (Prior-day flag)",
        description=(
            "Prior-day flag. The LS spec documents only '1' (전일분) as a "
            "valid value — modelled as Literal['1'] to reject any other value "
            "immediately. Defaults to '1'."
        ),
        examples=["1"],
    )
    date: str = Field(
        default="",
        title="일자 (Date cursor)",
        description=(
            "Date cursor for continuation paging. Length 8 (YYYYMMDD). "
            "Send empty string for the first request. For subsequent pages "
            "use the value from ``T1632OutBlock.date`` (the continuation "
            "marker returned in the previous response)."
        ),
        examples=["", "20230602"],
    )
    time: str = Field(
        default="",
        title="시간 (Time cursor)",
        description=(
            "Time cursor for continuation paging. Length 8 (LS spec). "
            "Send empty string for the first request. For subsequent pages "
            "use the value from ``T1632OutBlock.time``."
        ),
        examples=["", "175811"],
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


class T1632Request(BaseModel):
    """t1632 full request envelope (header + body + setup options)."""

    header: T1632RequestHeader = T1632RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1632",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1632InBlock"], T1632InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1632",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1632OutBlock(BaseModel):
    """t1632OutBlock — continuation marker for tr_cont paging.

    Unlike ``T1631OutBlock`` (which carries market-wide order aggregates),
    this block is a **pagination cursor only**. Pass ``date`` and ``time``
    into the next request's ``T1632InBlock.date`` / ``T1632InBlock.time``
    fields when ``tr_cont='Y'``.

    ``ex_gubun`` is declared Required in the LS spec but absent from the
    LS official example response payload — modelled with ``default=""`` so
    that the example payload validates without error.
    """

    date: str = Field(
        default="",
        title="날짜CTS (Date continuation cursor)",
        description=(
            "Date continuation cursor. Length 8. Used to request the next "
            "page when ``tr_cont='Y'``. Empty string when not continuing."
        ),
        examples=["20230602", ""],
    )
    time: str = Field(
        default="",
        title="시간CTS (Time continuation cursor)",
        description=(
            "Time continuation cursor. Length 8 (LS spec). Used alongside "
            "``date`` to request the next page when ``tr_cont='Y'``."
        ),
        examples=["175811", ""],
    )
    idx: int = Field(
        default=0,
        title="IDX (Continuation index)",
        description=(
            "Internal continuation index returned by LS. Length 4. "
            "Scale is not documented by LS — consume as reported."
        ),
        examples=[19, 0],
    )
    ex_gubun: str = Field(
        default="",
        title="거래소별구분코드 (Exchange-specific division code)",
        description=(
            "Exchange-specific division code. Length 2. Declared Required "
            "in the LS spec but absent from the LS official example payload. "
            "Live LS responses populate this with a single character "
            "(observed: '0' for KOSPI/거래소). Defaults to empty string for "
            "missing-field compatibility."
        ),
        examples=["0", ""],
    )


class T1632OutBlock1(BaseModel):
    """t1632OutBlock1 — time-bucketed program-trading trend rows.

    Object Array. The LS public spec documents only the per-row field
    schema. The meaning of an individual row, the ordering of the array,
    and any server-side arithmetic identity between fields (e.g., between
    ``tot1`` / ``tot2`` / ``tot3``, or between ``cha1`` / ``cha2`` /
    ``cha3``, or between ``bcha1`` / ``bcha2`` / ``bcha3``) are not
    documented by LS — consume the array as reported.
    """

    time: str = Field(
        default="",
        title="시간 (Time)",
        description=(
            "Time of the bucket as reported by LS. The LS spec declares "
            "length 8, but the official example response contains 6-character "
            "values (e.g., '180518') — no length validation is applied."
        ),
        examples=["180518", "175928"],
    )
    k200jisu: float = Field(
        default=0.0,
        title="KP200 (KP200 index value)",
        description=(
            "KP200 index value for this time bucket. Length 6.2 (LS spec). "
            "LS may serialise this as a zero-padded string (e.g., '342.67') "
            "— Pydantic coerces automatically."
        ),
        examples=[342.67, 1006.59],
    )
    sign: str = Field(
        default="",
        title="대비구분 (Change sign)",
        description=(
            "Change direction indicator. Length 1. The LS spec for t1632 "
            "does not publish an enum mapping for this field — consume the "
            "raw value as reported by LS without assuming any symbol mapping."
        ),
        examples=["2"],
    )
    change: float = Field(
        default=0.0,
        title="대비 (Change from prior)",
        description=(
            "Change from the prior period. Length 6.2 (LS spec). LS may "
            "serialise as a zero-padded string (e.g., '004.59') — Pydantic "
            "coerces automatically."
        ),
        examples=[4.59, 7.56, 0.0, -2.30],
    )
    k200basis: float = Field(
        default=0.0,
        title="BASIS (KP200 basis)",
        description=(
            "KP200 basis value for this time bucket. Length 6.2 (LS spec). "
            "The LS spec does not document the computation formula for this "
            "value — consume as reported."
        ),
        examples=[0.28, -1.34],
    )
    tot3: int = Field(
        default=0,
        title="전체순매수 (Total net-buy)",
        description=(
            "Total net-buy for this time bucket. Length 12. The LS spec "
            "does not publish a server-side computation formula — consume "
            "as reported."
        ),
        examples=[0],
    )
    tot1: int = Field(
        default=0,
        title="전체매수 (Total buy)",
        description="Total buy for this time bucket. Length 12.",
        examples=[0],
    )
    tot2: int = Field(
        default=0,
        title="전체매도 (Total sell)",
        description="Total sell for this time bucket. Length 12.",
        examples=[0],
    )
    cha3: int = Field(
        default=0,
        title="차익순매수 (Arbitrage net-buy)",
        description=(
            "Arbitrage net-buy for this time bucket. Length 12. The LS spec "
            "does not publish a server-side computation formula — consume "
            "as reported."
        ),
        examples=[0],
    )
    cha1: int = Field(
        default=0,
        title="차익매수 (Arbitrage buy)",
        description="Arbitrage buy for this time bucket. Length 12.",
        examples=[0],
    )
    cha2: int = Field(
        default=0,
        title="차익매도 (Arbitrage sell)",
        description="Arbitrage sell for this time bucket. Length 12.",
        examples=[0],
    )
    bcha3: int = Field(
        default=0,
        title="비차익순매수 (Non-arbitrage net-buy)",
        description=(
            "Non-arbitrage net-buy for this time bucket. Length 12. The LS "
            "spec does not publish a server-side computation formula — "
            "consume as reported."
        ),
        examples=[0],
    )
    bcha1: int = Field(
        default=0,
        title="비차익매수 (Non-arbitrage buy)",
        description="Non-arbitrage buy for this time bucket. Length 12.",
        examples=[0],
    )
    bcha2: int = Field(
        default=0,
        title="비차익매도 (Non-arbitrage sell)",
        description="Non-arbitrage sell for this time bucket. Length 12.",
        examples=[0],
    )


class T1632Response(BaseModel):
    """t1632 full API response envelope."""

    header: Optional[T1632ResponseHeader] = None
    cont_block: Optional[T1632OutBlock] = Field(
        default=None,
        title="t1632OutBlock (Continuation marker)",
        description=(
            "Continuation cursor for tr_cont paging. Present when the "
            "response contains data. Use ``cont_block.date`` and "
            "``cont_block.time`` in the next request when ``tr_cont='Y'``."
        ),
    )
    block: List[T1632OutBlock1] = Field(
        default_factory=list,
        title="t1632OutBlock1 (Time-bucketed program-trading trend rows)",
        description=(
            "Result rows as reported by LS. Row meaning and array ordering "
            "are not documented in the LS public spec."
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
