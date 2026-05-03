"""Pydantic models for LS Securities OpenAPI t1637 (Per-Symbol Program-Trading Time Series).

t1637 returns the program-trading flow for a single Korean stock as a
time series. Two display modes are selected by ``gubun2``:

    - gubun2 == "0": time-bucketed series within a trading day
      (continuation cursor = ``time``).
    - gubun2 == "1": daily series across multiple trading days
      (continuation cursor = ``date``).

Per-row payload includes price, change, percent change, volume, plus
buy / sell / net-buy amount and quantity (LS field naming — see the
``T1637OutBlock1`` docstring), and the exchange-specific short code.

The TR supports tr_cont continuation paging via the date / time cursor
defined in the LS spec (see the ``T1637InBlock.cts_idx`` field description
for the spec wording on the chart-query marker).

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are placed first inside ``Field(title=...)`` so AI chatbots can
map between Korean LS documentation and the English description.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1637RequestHeader(BlockRequestHeader):
    """t1637 request header. Inherits the standard LS request header schema."""
    pass


class T1637ResponseHeader(BlockResponseHeader):
    """t1637 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T1637InBlock(BaseModel):
    """t1637InBlock — input block for per-symbol program-trading time series.

    Continuation paging:
        - First page: send ``date=""`` and ``time=""``.
        - Subsequent pages: feed back the cursor from the previous response's
          ``T1637OutBlock1`` last row — ``time`` for ``gubun2='0'`` (time mode)
          or ``date`` for ``gubun2='1'`` (daily mode). Per LS spec ``cts_idx``
          is NOT used for continuation paging.
    """

    gubun1: Literal["0", "1"] = Field(
        ...,
        title="수량금액구분 (Quantity/amount selector)",
        description=(
            "Quantity-vs-amount selector for the result rows. "
            "'0' = quantity / 수량, '1' = amount / 금액. Required."
        ),
        examples=["0", "1"],
    )
    gubun2: Literal["0", "1"] = Field(
        ...,
        title="시간일별구분 (Time/daily selector)",
        description=(
            "Time-bucketed vs daily selector for the result rows. "
            "'0' = time-bucketed within a trading day / 시간, "
            "'1' = daily across multiple trading days / 일자. "
            "Also determines the continuation cursor (time vs date). Required."
        ),
        examples=["0", "1"],
    )
    shcode: str = Field(
        ...,
        title="종목코드 (Stock code)",
        description=(
            "Six-digit Korean stock code (e.g., '005930' for Samsung Electronics, "
            "'000660' for SK Hynix, '001200' for the LS Securities example). "
            "Required. Length 6."
        ),
        examples=["005930", "000660", "001200"],
    )
    date: str = Field(
        default="",
        title="일자 (Date cursor)",
        description=(
            "Continuation cursor used in daily mode (gubun2='1'). On the first "
            "request send an empty string; on subsequent pages set this to the "
            "``date`` value from the LAST row of the previous response's "
            "``T1637OutBlock1`` per LS spec. Format YYYYMMDD. Length 8."
        ),
        examples=["", "20230605", "20260502"],
    )
    time: str = Field(
        default="",
        title="시간 (Time cursor)",
        description=(
            "Continuation cursor used in time mode (gubun2='0'). On the first "
            "request send an empty string; on subsequent pages set this to the "
            "``time`` value from the LAST row of the previous response's "
            "``T1637OutBlock1`` per LS spec. Format HHMMSS. Length 6."
        ),
        examples=["", "102700", "090100"],
    )
    cts_idx: int = Field(
        default=9999,
        title="IDXCTS (Chart query marker)",
        description=(
            "IDXCTS marker (Number, length 4). The LS spec describes this field as "
            "``IDXCTS(9999:차트)`` with the directive '차트 조회시에만 9999로 입력' "
            "(set to 9999 for chart queries). The LS spec defines the ``date`` and "
            "``time`` fields as the continuation cursors (see their descriptions); "
            "this SDK fixes ``cts_idx`` at 9999 by default. The LS official example "
            "payload also sends cts_idx=9999. Default 9999."
        ),
        examples=[9999],
    )
    exchgubun: Literal["K", "N", "U"] = Field(
        default="K",
        title="거래소구분코드 (Exchange division code)",
        description=(
            "Exchange filter. 'K' = KRX (default), 'N' = NXT, 'U' = unified KRX+NXT. "
            "Other values are treated as KRX per LS spec."
        ),
        examples=["K", "N", "U"],
    )


class T1637Request(BaseModel):
    """t1637 full request envelope (header + body + setup options)."""

    header: T1637RequestHeader = T1637RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1637",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t1637InBlock"], T1637InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1637",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T1637OutBlock(BaseModel):
    """t1637OutBlock — IDXCTS block.

    LS returns an ``IDXCTS`` value here. The LS spec lists the field as
    ``IDXCTS`` (Number, length 4) without further detail, and the LS official
    example response returns ``cts_idx=0`` regardless of the request value
    (i.e., not an echo). The LS spec defines the date / time cursors in
    ``T1637OutBlock1`` as the continuation cursors — this field is not used
    by this SDK for paging.
    """

    cts_idx: int = Field(
        default=0,
        title="IDXCTS",
        description=(
            "IDXCTS (Number, length 4). The LS spec lists this field as "
            "``IDXCTS`` without further detail, and the LS official example "
            "response returns ``cts_idx=0`` regardless of the request value "
            "(i.e., not an echo). The LS spec defines the date / time cursors "
            "in ``T1637OutBlock1`` as the continuation cursors — this field is "
            "not used by this SDK for paging."
        ),
        examples=[0, 9999],
    )


class T1637OutBlock1(BaseModel):
    """t1637OutBlock1 — per-symbol program-trading time-series row.

    Note on LS field naming (counter-intuitive):
        - ``svalue`` / ``svolume`` are the **net-buy** amount/quantity.
        - ``stksvalue`` / ``stksvolume`` are the **buy** amount/quantity.
        - ``offervalue`` / ``offervolume`` are the **sell** amount/quantity.

    Row ordering (date / time DESC vs ASC) is not documented by LS. The LS
    official example response shows DESC ordering (newest first), but do not
    rely on this — the continuation cursor logic should treat the LAST row
    of each page as the cursor seed per LS spec.
    """

    date: str = Field(
        default="",
        title="일자 (Date)",
        description="Trading date in YYYYMMDD format. Length 8.",
        examples=["20230605", "20260502"],
    )
    time: str = Field(
        default="",
        title="시간 (Time)",
        description="Trading time in HHMMSS format. Length 6.",
        examples=["102700", "090100"],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Current price. Length 8.",
        examples=[3685, 3645, 70000],
    )
    sign: str = Field(
        default="",
        title="대비구분 (Price change sign)",
        description=(
            "Price change sign code (LS standard). '1' = upper limit, '2' = up, "
            "'3' = unchanged, '4' = lower limit, '5' = down. May be empty in the "
            "LS official example response."
        ),
        examples=["", "2", "5"],
    )
    change: int = Field(
        default=0,
        title="대비 (Price change)",
        description="Price change versus previous close. Length 8.",
        examples=[0, 25, -20],
    )
    diff: float = Field(
        default=0.0,
        title="등락율 (Percent change)",
        description=(
            "Percent price change versus previous close in % (LS scale 6.2). "
            "LS may serialize this value as a string (e.g., '0' or '-0.27'); "
            "Pydantic auto-coerces to float."
        ),
        examples=[0.0, 0.68, -0.27],
    )
    volume: int = Field(
        default=0,
        title="거래량 (Trading volume)",
        description="Total trading volume. Length 12.",
        examples=[0, 76162, 322192],
    )
    svalue: int = Field(
        default=0,
        title="순매수금액 (Program net-buy amount)",
        description=(
            "Program net-buy amount. A positive value indicates net buy; "
            "a negative value indicates net sell. Length 15."
        ),
        examples=[188914, -74311, 0],
    )
    offervalue: int = Field(
        default=0,
        title="매도금액 (Program sell amount)",
        description="Program sell amount. Length 15.",
        examples=[0, 800_000_000],
    )
    stksvalue: int = Field(
        default=0,
        title="매수금액 (Program buy amount)",
        description="Program buy amount. Length 15.",
        examples=[0, 1_000_000_000],
    )
    svolume: int = Field(
        default=0,
        title="순매수수량 (Program net-buy quantity)",
        description="Program net-buy quantity. Length 12.",
        examples=[49935, -20307, 0],
    )
    offervolume: int = Field(
        default=0,
        title="매도수량 (Program sell quantity)",
        description="Program sell quantity. Length 12.",
        examples=[0, 8_000],
    )
    stksvolume: int = Field(
        default=0,
        title="매수수량 (Program buy quantity)",
        description="Program buy quantity. Length 12.",
        examples=[0, 10_000],
    )
    shcode: str = Field(
        default="",
        title="종목코드 (Stock code)",
        description=(
            "Stock code as returned by LS. The LS official example response shows "
            "a leading 'A' prefix (e.g., 'A00120'); the format may differ from the "
            "6-digit input ``shcode``. Length 6."
        ),
        examples=["A00120", "005930"],
    )
    ex_shcode: str = Field(
        default="",
        title="거래소별단축코드 (Exchange-specific short code)",
        description=(
            "Exchange-specific short code per LS spec (LS field name "
            "거래소별단축코드). Length 10. The LS spec does not document the "
            "format, and this field is not present in the LS official example "
            "response."
        ),
        examples=["", "A001200"],
    )


class T1637Response(BaseModel):
    """t1637 full API response envelope."""

    header: Optional[T1637ResponseHeader] = None
    cont_block: Optional[T1637OutBlock] = Field(
        default=None,
        title="t1637OutBlock (IDXCTS block)",
        description=(
            "LS-returned IDXCTS value (see ``T1637OutBlock``). Continuation "
            "paging is driven by the date / time cursors in ``block`` per LS "
            "spec, not by this field."
        ),
    )
    block: List[T1637OutBlock1] = Field(
        default_factory=list,
        title="t1637OutBlock1 (Per-symbol program-trading time-series rows)",
        description=(
            "Time-series rows per the requested mode (gubun2). The LS official "
            "example response is sorted by time DESC (newest first), but row "
            "ordering is not documented by LS — treat the LAST row as the "
            "continuation cursor seed per LS spec."
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
