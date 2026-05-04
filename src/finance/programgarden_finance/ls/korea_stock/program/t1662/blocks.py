"""Pydantic models for LS Securities OpenAPI t1662 (Korea Stock Program Trading Time-Chart).

t1662 returns time-bucketed KP200 index, BASIS, change-sign, and program-trading
flow (total / arbitrage / non-arbitrage buy, sell, net-buy, plus volume) for the
KOSPI exchange (``gubun='0'``) or KOSDAQ market (``gubun='1'``) in a single
response — there is no cursor-based continuation paging despite the LS REST
header declaring ``tr_cont`` / ``tr_cont_key``.

Key design notes:

- ``T1662Response.block`` is an Object Array (``List[T1662OutBlock]``). The LS
  public spec documents only the per-row field schema. The meaning of an
  individual row, the ordering of the array, and any server-side arithmetic
  identity between fields (e.g., between ``tot1`` / ``tot2`` / ``tot3``,
  between ``cha`` / ``bcha`` axes, or between ``change`` and prior-day
  baselines) are not documented by LS — consume the array as reported.
- ``gubun`` encoding: ``'0'`` = KOSPI exchange (거래소), ``'1'`` = KOSDAQ.
  Identical to t1632 / t1633 / t1636 / t1637; **differs from t1631** ('1'/'2')
  and t1640 ('11'~'23'). Do not copy-paste t1631 / t1640 inputs verbatim.
- ``gubun1`` (amount/qty mode) and ``gubun3`` (day flag) follow LS spec
  enum domains and are modelled as ``Literal`` to reject invalid inputs early.
- ``exchgubun`` is documented in the REST spec but absent from the xingAPI
  FUNCTION_MAP. Modelled as Literal with ``default='K'`` for forward
  compatibility; LS server treats other values as KRX.
- ``sign`` is the only OutBlock enum field with a published mapping
  ('1'=상한, '2'=상승, '3'=보합, '4'=하한, '5'=하락). All other enum / scalar
  semantics follow LS spec wording verbatim.

Field descriptions follow LS official spec wording verbatim. Korean field
labels (한글명) are appended in parentheses so AI chatbots can map between
English descriptions and Korean LS documentation. Inferred formulas, units,
row ordering, ``volume`` unit conventions, or ``change`` baseline that are
not in the LS public spec are intentionally omitted — consume every value
as reported by LS.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1662RequestHeader(BlockRequestHeader):
    """t1662 request header. Inherits the standard LS request header schema."""
    pass


class T1662ResponseHeader(BlockResponseHeader):
    """t1662 response header. No continuation flags are used by t1662 in practice — the LS spec
    declares ``tr_cont`` / ``tr_cont_key`` at the protocol layer but t1662 returns the full
    Object Array in a single response."""
    pass


class T1662InBlock(BaseModel):
    """t1662InBlock — input block for time-chart program-trading query.

    Selects market (``gubun``: 거래소 vs KOSDAQ), amount/qty mode (``gubun1``),
    day axis (``gubun3``: today vs prior day), and exchange filter
    (``exchgubun``).

    WARNING: ``gubun`` encoding matches t1632 / t1633 / t1636 / t1637
    ('0' = 거래소, '1' = KOSDAQ) but **differs** from t1631 ('1' / '2')
    and t1640 ('11' / '12' / '13' / '21' / '22' / '23'). Anti-copy-paste
    Literal guard rejects sibling-TR values.
    """

    gubun: Literal["0", "1"] = Field(
        ...,
        title="구분 (Market division)",
        description=(
            "Market division. '0' = 거래소 (KOSPI exchange / KRX), "
            "'1' = 코스닥 (KOSDAQ). Required. Length 1. "
            "NOTE: encoding matches t1632 / t1633 / t1636 / t1637 but "
            "differs from t1631 ('1' / '2') and t1640 ('11' / '12' / '13' / "
            "'21' / '22' / '23')."
        ),
        examples=["0", "1"],
    )
    gubun1: Literal["0", "1"] = Field(
        ...,
        title="금액수량구분 (Amount/quantity mode)",
        description=(
            "Amount or quantity mode. '0' = 금액 (amount), "
            "'1' = 수량 (quantity). Required. Length 1."
        ),
        examples=["0", "1"],
    )
    gubun3: Literal["0", "1"] = Field(
        ...,
        title="당일전일구분 (Today/prior-day flag)",
        description=(
            "Today / prior-day flag. '0' = 당일 (today), "
            "'1' = 전일 (prior day). Required. Length 1."
        ),
        examples=["0", "1"],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        ...,
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange division code. 'K' = KRX, 'N' = NXT, 'U' = 통합 "
            "(unified). Required. Length 1. "
            "NOTE: this field is documented in the LS REST spec but absent "
            "from the xingAPI FUNCTION_MAP — REST-only. Per LS spec, any "
            "other value is treated as KRX server-side."
        ),
        examples=["K", "N", "U"],
    )


class T1662Request(BaseModel):
    """t1662 full request envelope (header + body + setup options)."""

    header: T1662RequestHeader = T1662RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1662",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1662InBlock"], T1662InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1662",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1662OutBlock(BaseModel):
    """t1662OutBlock — per-time-bucket program-trading row (Object Array).

    Each row reports one time bucket's KP200 index, BASIS, change-sign, change
    value, total / arbitrage / non-arbitrage buy / sell / net-buy aggregates,
    and total volume. Row count and ordering of the array are not documented
    in the LS public spec — consume as reported.

    LS may serialise numeric fields as zero-padded strings (e.g.,
    ``"000000786684"`` for 786684, ``"343.75"`` for 343.75). Pydantic
    auto-coerces these per the field type (int for long-typed fields,
    float for float-typed fields).
    """

    time: str = Field(
        default="",
        title="시간 (Time HHMMSS)",
        description=(
            "Time bucket identifier as reported by LS. Length 6 (HHMMSS, "
            "e.g., '102600'). LS spec does not document array ordering — "
            "consume rows as reported. Defaults to empty string when LS "
            "omits the field (defensive parsing only — not an LS-published "
            "default)."
        ),
        examples=["102600", "090000"],
    )
    k200jisu: float = Field(
        default=0.0,
        title="KP200 (KP200 index value)",
        description=(
            "KP200 index value at this time bucket. Length 6.2. LS may "
            "serialise as a zero-padded string (e.g., '343.75') — Pydantic "
            "auto-coerces to float. Defaults to 0.0 when LS omits the field "
            "(defensive parsing only — not an LS-published default)."
        ),
        examples=[343.75, 342.67],
    )
    sign: Optional[Literal["1", "2", "3", "4", "5"]] = Field(
        default=None,
        title="대비구분 (Change sign)",
        description=(
            "Change-sign indicator. Length 1. "
            "'1' = upper limit (상한), '2' = up (상승), '3' = unchanged (보합), "
            "'4' = lower limit (하한), '5' = down (하락). "
            "Mapping is published by LS spec for t1662 (see LS '---참고---' "
            "section). Defaults to None when LS omits the field — None is a "
            "defensive sentinel meaning 'LS did not report sign for this row' "
            "and is NOT one of the five LS-published values; do not interpret "
            "None as 보합 / unchanged."
        ),
        examples=["2", "3"],
    )
    change: float = Field(
        default=0.0,
        title="대비 (Change)",
        description=(
            "Change value at this time bucket as reported by LS. Length 6.2. "
            "Baseline for the comparison is not documented in the LS public "
            "spec. LS may serialise as a zero-padded string (e.g., "
            "'001.08') — Pydantic auto-coerces to float. Defaults to 0.0 "
            "when LS omits the field (defensive parsing only — not an "
            "LS-published default)."
        ),
        examples=[1.08, 0.00],
    )
    k200basis: float = Field(
        default=0.0,
        title="BASIS (KP200 basis)",
        description=(
            "KP200 basis value at this time bucket. Length 6.2. LS spec "
            "does not document the computation formula — consume as reported. "
            "Defaults to 0.0 when LS omits the field (defensive parsing only "
            "— not an LS-published default)."
        ),
        examples=[0.27, 2.08],
    )
    tot3: int = Field(
        default=0,
        title="전체순매수 (Total net-buy)",
        description=(
            "Total net-buy at this time bucket. Length 12. Server-computed "
            "by LS — formula not published; consume as reported. Defaults "
            "to 0 when LS omits the field (defensive parsing only — not an "
            "LS-published default)."
        ),
        examples=[27896, -7637, 0],
    )
    tot1: int = Field(
        default=0,
        title="전체매수 (Total buy)",
        description=(
            "Total buy at this time bucket. Length 12. Defaults to 0 when "
            "LS omits the field (defensive parsing only — not an LS-published "
            "default)."
        ),
        examples=[786684, 12327, 0],
    )
    tot2: int = Field(
        default=0,
        title="전체매도 (Total sell)",
        description=(
            "Total sell at this time bucket. Length 12. Defaults to 0 when "
            "LS omits the field (defensive parsing only — not an LS-published "
            "default)."
        ),
        examples=[758788, 19964, 0],
    )
    cha3: int = Field(
        default=0,
        title="차익순매수 (Arbitrage net-buy)",
        description=(
            "Arbitrage net-buy at this time bucket. Length 12. Server-computed "
            "by LS — formula not published; consume as reported. Defaults to "
            "0 when LS omits the field (defensive parsing only — not an "
            "LS-published default)."
        ),
        examples=[12081, 0],
    )
    cha1: int = Field(
        default=0,
        title="차익매수 (Arbitrage buy)",
        description=(
            "Arbitrage buy at this time bucket. Length 12. Defaults to 0 when "
            "LS omits the field (defensive parsing only — not an LS-published "
            "default)."
        ),
        examples=[17718, 0],
    )
    cha2: int = Field(
        default=0,
        title="차익매도 (Arbitrage sell)",
        description=(
            "Arbitrage sell at this time bucket. Length 12. Defaults to 0 when "
            "LS omits the field (defensive parsing only — not an LS-published "
            "default)."
        ),
        examples=[5637, 0],
    )
    bcha3: int = Field(
        default=0,
        title="비차익순매수 (Non-arbitrage net-buy)",
        description=(
            "Non-arbitrage net-buy at this time bucket. Length 12. "
            "Server-computed by LS — formula not published; consume as reported. "
            "Defaults to 0 when LS omits the field (defensive parsing only "
            "— not an LS-published default)."
        ),
        examples=[15815, -7637, 0],
    )
    bcha1: int = Field(
        default=0,
        title="비차익매수 (Non-arbitrage buy)",
        description=(
            "Non-arbitrage buy at this time bucket. Length 12. Defaults to 0 "
            "when LS omits the field (defensive parsing only — not an "
            "LS-published default)."
        ),
        examples=[768966, 12327, 0],
    )
    bcha2: int = Field(
        default=0,
        title="비차익매도 (Non-arbitrage sell)",
        description=(
            "Non-arbitrage sell at this time bucket. Length 12. Defaults to 0 "
            "when LS omits the field (defensive parsing only — not an "
            "LS-published default)."
        ),
        examples=[753151, 19964, 0],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Volume)",
        description=(
            "Volume at this time bucket. Length 12. Unit conventions are not "
            "documented in the LS public spec. Defaults to 0 when LS omits "
            "the field (defensive parsing only — not an LS-published default)."
        ),
        examples=[24, 0],
    )


class T1662Response(BaseModel):
    """t1662 full API response envelope (Object Array, no continuation marker)."""

    header: Optional[T1662ResponseHeader] = None
    block: List[T1662OutBlock] = Field(
        default_factory=list,
        title="t1662OutBlock (Time-chart program-trading rows)",
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
