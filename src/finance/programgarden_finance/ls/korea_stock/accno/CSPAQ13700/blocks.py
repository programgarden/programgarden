"""Pydantic models for LS Securities OpenAPI CSPAQ13700 (Cash Account Order Execution History).

CSPAQ13700 returns the cash-equity account's order and execution history
for a target trading day, in three response blocks:
    - ``CSPAQ13700OutBlock1`` (block1): echo-back of the input parameters
      (market scope, side filter, symbol filter, fill filter, target date,
      starting order number, ordering, order pattern).
    - ``CSPAQ13700OutBlock2`` (block2): summary aggregates — total filled
      and ordered quantities and amounts split by buy / sell.
    - ``CSPAQ13700OutBlock3`` (block3): per-order detail rows including
      original order number (for modify / cancel chains), order quantity /
      price, fill quantity / price, fill timing and order metadata.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ13700RequestHeader(BlockRequestHeader):
    """CSPAQ13700 request header. Inherits the standard LS request header schema."""
    pass


class CSPAQ13700ResponseHeader(BlockResponseHeader):
    """CSPAQ13700 response header. Standard LS response header schema."""
    pass


class CSPAQ13700InBlock1(BaseModel):
    """CSPAQ13700InBlock1 — input block for cash account order execution history.

    Defaults select all markets, both sides, all symbols, all orders (filled
    and unfilled), starting from the highest order number on the current
    trading day. Adjust the filters to scope the query.
    """

    OrdMktCode: str = Field(
        default="00",
        title="주문시장코드 (Order market code)",
        description=(
            "Order market scope. Default ``\"00\"`` selects all markets. The "
            "complete enum mapping is not declared in the available LS source — "
            "consume per LS convention."
        ),
        examples=["00", "01", "02"],
    )
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드 (Side filter)",
        description=(
            "Side filter for the query. Default ``\"0\"`` selects both buy and "
            "sell. The complete enum mapping is not declared in the available "
            "LS source — consume per LS convention."
        ),
        examples=["0", "1", "2"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code (``A`` + 6-digit short code) to "
            "filter by, or empty string for all symbols."
        ),
        examples=["", "A005930", "A000660"],
    )
    ExecYn: str = Field(
        default="0",
        title="체결여부 (Fill filter)",
        description=(
            "Fill-state filter. Default ``\"0\"`` selects both filled and "
            "unfilled. The complete enum mapping is not declared in the "
            "available LS source — consume per LS convention."
        ),
        examples=["0", "1", "2"],
    )
    OrdDt: str = Field(
        default="",
        title="주문일자 (Order date)",
        description=(
            "Target trading date in ``YYYYMMDD`` format. Empty string is "
            "treated by LS as the current trading day."
        ),
        examples=["", "20260507", "20260103"],
    )
    SrtOrdNo2: int = Field(
        default=999999999,
        title="시작주문번호2 (Starting order number)",
        description=(
            "Starting order number for paging. Pass ``999999999`` (default) "
            "on the first call to start from the highest order number; on "
            "subsequent calls pass the smallest order number returned in the "
            "previous page minus 1 to fetch older rows. Length 9."
        ),
        examples=[999_999_999, 12_345],
    )
    BkseqTpCode: str = Field(
        default="0",
        title="역순구분코드 (Reverse-order code)",
        description=(
            "Result ordering selector. Default ``\"0\"``. The complete enum "
            "mapping is not declared in the available LS source — consume per "
            "LS convention."
        ),
        examples=["0", "1"],
    )
    OrdPtnCode: str = Field(
        default="00",
        title="주문패턴코드 (Order pattern code)",
        description=(
            "Order pattern filter (e.g., regular / reserved / loan-related). "
            "Default ``\"00\"`` selects all patterns. The complete enum "
            "mapping is not declared in the available LS source — consume per "
            "LS convention."
        ),
        examples=["00", "01"],
    )


class CSPAQ13700Request(BaseModel):
    """CSPAQ13700 full request envelope (header + body + setup options)."""

    header: CSPAQ13700RequestHeader = CSPAQ13700RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ13700",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPAQ13700InBlock1"], CSPAQ13700InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ13700",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPAQ13700OutBlock1(BaseModel):
    """CSPAQ13700OutBlock1 — input echo-back block."""

    OrdMktCode: str = Field(
        default="00",
        title="주문시장코드 (Order market code)",
        description="Echo of the input ``OrdMktCode``.",
        examples=["00", "01"],
    )
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드 (Side filter)",
        description="Echo of the input ``BnsTpCode``.",
        examples=["0", "1", "2"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="Echo of the input ``IsuNo``.",
        examples=["", "A005930"],
    )
    ExecYn: str = Field(
        default="0",
        title="체결여부 (Fill filter)",
        description="Echo of the input ``ExecYn``.",
        examples=["0", "1", "2"],
    )
    OrdDt: str = Field(
        default="",
        title="주문일자 (Order date, YYYYMMDD)",
        description="Echo of the input ``OrdDt``.",
        examples=["", "20260507"],
    )
    SrtOrdNo2: int = Field(
        default=999999999,
        title="시작주문번호2 (Starting order number)",
        description="Echo of the input ``SrtOrdNo2``.",
        examples=[999_999_999, 12_345],
    )
    BkseqTpCode: str = Field(
        default="0",
        title="역순구분코드 (Reverse-order code)",
        description="Echo of the input ``BkseqTpCode``.",
        examples=["0", "1"],
    )
    OrdPtnCode: str = Field(
        default="00",
        title="주문패턴코드 (Order pattern code)",
        description="Echo of the input ``OrdPtnCode``.",
        examples=["00", "01"],
    )


class CSPAQ13700OutBlock2(BaseModel):
    """CSPAQ13700OutBlock2 — order execution summary block.

    Returns aggregate execution / order quantities and amounts split by
    buy / sell side, scoped to the requested filters.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this summary block.",
        examples=[0, 1],
    )
    SellExecAmt: int = Field(
        default=0,
        title="매도체결금액 (Sell fill amount)",
        description=(
            "Total sell-side filled amount for the matching orders. "
            "Currency: KRW."
        ),
        examples=[0, 3_500_000],
    )
    BuyExecAmt: int = Field(
        default=0,
        title="매수체결금액 (Buy fill amount)",
        description=(
            "Total buy-side filled amount for the matching orders. "
            "Currency: KRW."
        ),
        examples=[0, 7_000_000],
    )
    SellExecQty: int = Field(
        default=0,
        title="매도체결수량 (Sell fill quantity)",
        description="Total sell-side filled quantity (shares).",
        examples=[0, 50, 500],
    )
    BuyExecQty: int = Field(
        default=0,
        title="매수체결수량 (Buy fill quantity)",
        description="Total buy-side filled quantity (shares).",
        examples=[0, 100, 1_000],
    )
    SellOrdQty: int = Field(
        default=0,
        title="매도주문수량 (Sell order quantity)",
        description="Total sell-side ordered quantity (shares).",
        examples=[0, 60, 600],
    )
    BuyOrdQty: int = Field(
        default=0,
        title="매수주문수량 (Buy order quantity)",
        description="Total buy-side ordered quantity (shares).",
        examples=[0, 100, 1_200],
    )


class CSPAQ13700OutBlock3(BaseModel):
    """CSPAQ13700OutBlock3 — per-order execution detail row.

    Each row describes one order placed within the requested scope, with
    fill quantity / price, original order number for modify / cancel chains,
    fill timing, price-type metadata, and order channel.
    """

    OrdDt: str = Field(
        default="",
        title="주문일자 (Order date, YYYYMMDD)",
        description="Trading date on which the order was placed.",
        examples=["", "20260507"],
    )
    OrdNo: int = Field(
        default=0,
        title="주문번호 (Order number)",
        description="LS-assigned order number for the trading day.",
        examples=[1, 12_345, 99_999],
    )
    OrgOrdNo: int = Field(
        default=0,
        title="원주문번호 (Original order number)",
        description=(
            "Original order number for modify / cancel chains. 0 for fresh "
            "orders that are not modifications or cancellations."
        ),
        examples=[0, 12_345],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description="LS-prefixed Korean stock code.",
        examples=["", "A005930", "A000660"],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드 (Side code)",
        description=(
            "Side code for the order. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    BnsTpNm: str = Field(
        default="",
        title="매매구분명 (Side display name)",
        description=(
            "Korean display name corresponding to ``BnsTpCode`` (e.g., 매도, "
            "매수)."
        ),
        examples=["", "매수", "매도"],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Quantity ordered (shares).",
        examples=[1, 10, 100],
    )
    OrdPrc: float = Field(
        default=0.0,
        title="주문단가 (Order price)",
        description=(
            "Order price (KRW). May be 0 for market orders. LS may serialize "
            "this value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 70_000.0, 250_000.0],
    )
    ExecQty: int = Field(
        default=0,
        title="체결수량 (Fill quantity)",
        description="Filled quantity for this order (shares).",
        examples=[0, 10, 100],
    )
    ExecPrc: float = Field(
        default=0.0,
        title="체결단가 (Fill price)",
        description=(
            "Average fill price for this order. LS may serialize this value "
            "as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 71_500.0, 248_000.0],
    )
    ExecTrxTime: str = Field(
        default="",
        title="체결처리시각 (Fill processing time)",
        description=(
            "Server-side fill processing timestamp. Format follows LS "
            "convention (HHMMSS or HHMMSSmmm) — consume as returned."
        ),
        examples=["", "093015", "153000123"],
    )
    LastExecTime: str = Field(
        default="",
        title="최종체결시각 (Last fill time)",
        description=(
            "Timestamp of the final fill on this order. Format follows LS "
            "convention — consume as returned."
        ),
        examples=["", "093015", "153000"],
    )
    OrdprcPtnCode: str = Field(
        default="",
        title="주문가유형코드 (Price-type code)",
        description=(
            "Price-type code for the order (limit / market / etc.). The "
            "complete enum mapping is not declared in the available LS source — "
            "consume as returned by LS."
        ),
        examples=["", "00", "03"],
    )
    OrdprcPtnNm: str = Field(
        default="",
        title="주문가유형명 (Price-type display name)",
        description=(
            "Korean display name corresponding to ``OrdprcPtnCode`` (e.g., "
            "지정가, 시장가)."
        ),
        examples=["", "지정가", "시장가"],
    )
    OrdCndiTpCode: str = Field(
        default="",
        title="주문조건구분코드 (Order condition code)",
        description=(
            "Order condition code (e.g., FOK / IOC). The complete enum "
            "mapping is not declared in the available LS source — consume as "
            "returned by LS."
        ),
        examples=["", "0", "1"],
    )
    AllExecQty: int = Field(
        default=0,
        title="전체체결수량 (Total filled quantity)",
        description=(
            "Cumulative filled quantity across all fills on this order "
            "(shares)."
        ),
        examples=[0, 10, 100],
    )
    OrdTime: str = Field(
        default="",
        title="주문시각 (Order time)",
        description=(
            "Order placement timestamp. Format follows LS convention "
            "(HHMMSS or HHMMSSmmm) — consume as returned."
        ),
        examples=["", "093015", "153000"],
    )
    OpDrtnNo: str = Field(
        default="",
        title="운용지시번호 (Operation instruction number)",
        description=(
            "Internal operation instruction number used by LS for institutional "
            "trading workflows. Empty for retail orders."
        ),
        examples=["", "OP12345"],
    )
    RmnOrdQty: int = Field(
        default=0,
        title="잔여주문수량 (Remaining order quantity)",
        description="Remaining unfilled quantity for this order (shares).",
        examples=[0, 10, 50],
    )
    OrdGb: str = Field(
        default="",
        title="주문구분 (Order classification)",
        description=(
            "Order classification flag. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    Rectgb: str = Field(
        default="",
        title="접수구분 (Reception classification)",
        description=(
            "Reception classification flag (channel / venue acknowledgement). "
            "The complete enum mapping is not declared in the available LS "
            "source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )


class CSPAQ13700Response(BaseModel):
    """CSPAQ13700 full API response envelope."""

    header: Optional[CSPAQ13700ResponseHeader] = None
    block1: Optional[CSPAQ13700OutBlock1] = Field(
        default=None,
        title="CSPAQ13700OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters.",
    )
    block2: Optional[CSPAQ13700OutBlock2] = Field(
        default=None,
        title="CSPAQ13700OutBlock2 (Order execution summary)",
        description="Aggregate buy / sell ordered and filled quantities and amounts.",
    )
    block3: List[CSPAQ13700OutBlock3] = Field(
        default_factory=list,
        title="CSPAQ13700OutBlock3 (Per-order detail list)",
        description="List of per-order rows scoped to the requested filters.",
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str = Field(default="", title="Response code")
    rsp_msg: str = Field(default="", title="Response message")
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
