"""Pydantic models for LS Securities OpenAPI t0425 (Korean Stock Order Fill / Unfilled Status).

t0425 returns the current trading day's order activity, with parallel data
sets for aggregates and per-order details:
    - ``T0425OutBlock`` (cont_block): account-level aggregates — total order
      / fill / unfilled quantities, total order amount, total buy / sell
      fill amounts, estimated fees and taxes.
    - ``T0425OutBlock1`` (block): per-order rows including fill quantity /
      price, unfilled remainder, status, original order number, order method,
      session price type and exchange name.

Filtering on the request side is provided by ``chegb`` (all / filled /
unfilled), ``medosu`` (all / sell / buy), and ``expcode`` (specific symbol
or empty for all symbols). ``sortgb`` controls list ordering by order
number (descending vs. ascending).

Continuation paging uses ``cts_ordno`` — feed the value returned in
``T0425OutBlock`` back into the next request's ``T0425InBlock.cts_ordno``.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T0425RequestHeader(BlockRequestHeader):
    """t0425 request header. Inherits the standard LS request header schema."""
    pass


class T0425ResponseHeader(BlockResponseHeader):
    """t0425 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T0425InBlock(BaseModel):
    """t0425InBlock — input block for Korean stock order fill / unfilled status.

    Pass ``cts_ordno=""`` on the first call. To page through additional
    rows, feed back the ``cts_ordno`` returned in ``T0425OutBlock``.
    """

    expcode: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "Six-digit Korean stock code to filter by, or empty string for all "
            "symbols (default). Length 6."
        ),
        examples=["", "005930", "000660"],
    )
    chegb: Literal["0", "1", "2"] = Field(
        default="0",
        title="체결구분 (Fill filter)",
        description=(
            "Fill-state filter. '0' = 전체 (all, default), '1' = 체결 (filled only), "
            "'2' = 미체결 (unfilled only). Length 1."
        ),
        examples=["0", "1", "2"],
    )
    medosu: Literal["0", "1", "2"] = Field(
        default="0",
        title="매매구분 (Side filter)",
        description=(
            "Side filter. '0' = 전체 (all, default), '1' = 매도 (sell), "
            "'2' = 매수 (buy). Length 1."
        ),
        examples=["0", "1", "2"],
    )
    sortgb: Literal["1", "2"] = Field(
        default="1",
        title="정렬순서 (Sort order)",
        description=(
            "List ordering by order number. '1' = 주문번호 역순 (descending, "
            "newest first; default), '2' = 주문번호 순 (ascending, oldest first). "
            "Length 1."
        ),
        examples=["1", "2"],
    )
    cts_ordno: str = Field(
        default="",
        title="주문번호CTS (Continuation key)",
        description=(
            "Continuation key for paging through orders. Pass an empty string "
            "on the first call. On subsequent calls reuse the ``cts_ordno`` "
            "returned in T0425OutBlock to fetch the next page."
        ),
        examples=["", "12345"],
    )


class T0425Request(BaseModel):
    """t0425 full request envelope (header + body + setup options)."""

    header: T0425RequestHeader = T0425RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t0425",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t0425InBlock"], T0425InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t0425",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T0425OutBlock(BaseModel):
    """t0425OutBlock — daily order aggregate + continuation block.

    Returns daily totals across the filtered orders together with the
    continuation key. ``cts_ordno == ""`` indicates no further pages.
    """

    tqty: int = Field(
        default=0,
        title="총주문수량 (Total order quantity)",
        description="Total ordered quantity (sum across all matching orders).",
        examples=[0, 100, 1_000],
    )
    tcheqty: int = Field(
        default=0,
        title="총체결수량 (Total fill quantity)",
        description="Total filled quantity (sum across all matching orders).",
        examples=[0, 80, 1_000],
    )
    tordrem: int = Field(
        default=0,
        title="총미체결수량 (Total unfilled quantity)",
        description="Total unfilled remainder (sum across all matching orders).",
        examples=[0, 20, 500],
    )
    cmss: int = Field(
        default=0,
        title="추정수수료 (Estimated fee)",
        description=(
            "Estimated brokerage fee accumulated for the matching orders. "
            "Currency: KRW."
        ),
        examples=[0, 1_500],
    )
    tamt: int = Field(
        default=0,
        title="총주문금액 (Total order amount)",
        description=(
            "Total order amount (sum of order quantity × order price across "
            "matching orders). Currency: KRW."
        ),
        examples=[0, 7_000_000, 25_000_000],
    )
    tmdamt: int = Field(
        default=0,
        title="총매도체결금액 (Total sell-fill amount)",
        description=(
            "Total sell-side filled amount (sum across matching sell orders). "
            "Currency: KRW."
        ),
        examples=[0, 3_500_000],
    )
    tmsamt: int = Field(
        default=0,
        title="총매수체결금액 (Total buy-fill amount)",
        description=(
            "Total buy-side filled amount (sum across matching buy orders). "
            "Currency: KRW."
        ),
        examples=[0, 7_000_000],
    )
    tax: int = Field(
        default=0,
        title="추정제세금 (Estimated tax)",
        description=(
            "Estimated transaction tax accumulated for the matching orders. "
            "Currency: KRW."
        ),
        examples=[0, 7_500],
    )
    cts_ordno: str = Field(
        default="",
        title="주문번호CTS (Continuation key)",
        description=(
            "Continuation key for paging. Feed this value back into the next "
            "request's ``T0425InBlock.cts_ordno`` to retrieve the following "
            "page. An empty string means no further pages are available."
        ),
        examples=["", "12345"],
    )


class T0425OutBlock1(BaseModel):
    """t0425OutBlock1 — per-order row (fill / unfilled detail).

    Each row describes one order placed during the current trading day, with
    fill quantity / price, unfilled remainder, status, original order number
    (for modify / cancel chains), and exchange / venue metadata.
    """

    ordno: int = Field(
        default=0,
        title="주문번호 (Order number)",
        description="LS-assigned order number for the current trading day.",
        examples=[1, 12_345, 99_999],
    )
    expcode: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Six-digit Korean stock code. Length 6.",
        examples=["005930", "000660", "035720"],
    )
    medosu: str = Field(
        default="",
        title="구분 (Side)",
        description=(
            "Buy / sell side indicator. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS. "
            "Common observations: '1' indicates 매도 (sell) and '2' indicates "
            "매수 (buy) per the example script's display mapping."
        ),
        examples=["1", "2"],
    )
    qty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Quantity ordered (shares).",
        examples=[1, 10, 100],
    )
    price: int = Field(
        default=0,
        title="주문가격 (Order price)",
        description=(
            "Order price (KRW). For market orders, the value reported by LS may "
            "be 0 — consume as returned."
        ),
        examples=[0, 70_000, 250_000],
    )
    cheqty: int = Field(
        default=0,
        title="체결수량 (Fill quantity)",
        description="Filled quantity for this order (shares).",
        examples=[0, 10, 100],
    )
    cheprice: int = Field(
        default=0,
        title="체결가격 (Fill price)",
        description="Average fill price for this order. Currency: KRW.",
        examples=[0, 71_500, 248_000],
    )
    ordrem: int = Field(
        default=0,
        title="미체결잔량 (Unfilled remainder)",
        description="Remaining unfilled quantity for this order (shares).",
        examples=[0, 10, 50],
    )
    cfmqty: int = Field(
        default=0,
        title="확인수량 (Confirmed quantity)",
        description=(
            "Server-confirmed quantity (acknowledgement count). Semantics "
            "beyond the field name are not declared in the available LS source — "
            "consume as returned by LS."
        ),
        examples=[0, 10, 100],
    )
    status: str = Field(
        default="",
        title="상태 (Order status)",
        description=(
            "Order status text. The complete enum mapping is not declared in "
            "the available LS source — consume as returned by LS."
        ),
        examples=["", "접수", "체결"],
    )
    orgordno: int = Field(
        default=0,
        title="원주문번호 (Original order number)",
        description=(
            "Original order number for modify / cancel chains. 0 for fresh "
            "orders that are not modifications or cancellations."
        ),
        examples=[0, 12_345],
    )
    ordgb: str = Field(
        default="",
        title="유형 (Order type)",
        description=(
            "Order type indicator (e.g., new / modify / cancel). The complete "
            "enum mapping is not declared in the available LS source — consume "
            "as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    ordtime: str = Field(
        default="",
        title="주문시간 (Order time)",
        description=(
            "Order placement time, formatted as HHMMSS or HHMMSSmmm. Consume "
            "as returned by LS."
        ),
        examples=["", "093015", "153000123"],
    )
    ordermtd: str = Field(
        default="",
        title="주문매체 (Order channel)",
        description=(
            "Order placement channel (HTS / MTS / OpenAPI / etc.). The complete "
            "enum mapping is not declared in the available LS source — consume "
            "as returned by LS."
        ),
        examples=["", "OpenAPI"],
    )
    sysprocseq: int = Field(
        default=0,
        title="처리순번 (Processing sequence)",
        description=(
            "Server-side processing sequence number. Used internally by LS for "
            "row ordering — consume as returned."
        ),
        examples=[1, 27, 312],
    )
    hogagb: str = Field(
        default="",
        title="호가유형 (Price type)",
        description=(
            "Price-type indicator (limit / market / etc.). The complete enum "
            "mapping is not declared in the available LS source — consume as "
            "returned by LS."
        ),
        examples=["", "00", "03"],
    )
    price1: int = Field(
        default=0,
        title="현재가 (Current price)",
        description=(
            "Most recent traded price for the symbol at the time of the row. "
            "Currency: KRW."
        ),
        examples=[0, 70_000, 250_000],
    )
    orggb: str = Field(
        default="",
        title="주문구분 (Order classification)",
        description=(
            "Order classification flag. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    singb: str = Field(
        default="",
        title="신용구분 (Credit classification)",
        description=(
            "Credit / margin classification flag. The complete enum mapping is "
            "not declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "00", "01"],
    )
    loandt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description=(
            "Origination date of the credit / margin loan associated with this "
            "order, formatted as YYYYMMDD. Empty when no loan applies."
        ),
        examples=["", "20260315"],
    )
    exchname: str = Field(
        default="",
        title="거래소명 (Exchange name)",
        description=(
            "Execution exchange / venue name (e.g., KRX, NXT). The complete enum "
            "mapping is not declared in the available LS source — consume as "
            "returned by LS."
        ),
        examples=["", "KRX", "NXT"],
    )


class T0425Response(BaseModel):
    """t0425 full API response envelope."""

    header: Optional[T0425ResponseHeader] = None
    cont_block: Optional[T0425OutBlock] = Field(
        default=None,
        title="t0425OutBlock (Aggregate + continuation block)",
        description=(
            "Account-level daily aggregates (total order / fill / unfilled "
            "quantities, fees, taxes, total amounts) and the continuation key "
            "``cts_ordno``."
        ),
    )
    block: List[T0425OutBlock1] = Field(
        default_factory=list,
        title="t0425OutBlock1 (Per-order detail list)",
        description=(
            "List of per-order rows for the current trading day, ordered per "
            "the requested ``sortgb``."
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
