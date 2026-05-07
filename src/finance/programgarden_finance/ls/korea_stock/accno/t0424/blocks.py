"""Pydantic models for LS Securities OpenAPI t0424 (Korean Stock Account Balance v2).

t0424 returns the cash-equity account balance with two parallel data sets:
    - ``T0424OutBlock`` (cont_block): aggregate snapshot of the whole account —
      estimated net asset, realized PnL, total purchase amount, estimated D+2
      cash, total valuation, and total unrealized PnL.
    - ``T0424OutBlock1`` (block): per-symbol holding rows including balance
      quantity, average / BEP cost, today's and previous-day buy / sell flow,
      and per-row valuation, unrealized PnL and return rate.

Pricing is configurable on the request side via ``prcgb`` (average cost vs.
BEP cost) and ``chegb`` (settlement-based vs. trade-based balance). The
``charge`` flag toggles whether transaction costs (fees, taxes, credit
interest) are included in the returned figures.

Continuation paging uses ``cts_expcode`` — feed the value returned in
``T0424OutBlock`` back into the next request's ``T0424InBlock.cts_expcode``.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T0424RequestHeader(BlockRequestHeader):
    """t0424 request header. Inherits the standard LS request header schema."""
    pass


class T0424ResponseHeader(BlockResponseHeader):
    """t0424 response header. Carries continuation flags (``tr_cont`` / ``tr_cont_key``)."""
    pass


class T0424InBlock(BaseModel):
    """t0424InBlock — input block for Korean stock account balance v2.

    Pass ``cts_expcode=""`` on the first call. To page through additional
    holdings, feed back the ``cts_expcode`` returned in ``T0424OutBlock``.
    """

    prcgb: Literal["1", "2"] = Field(
        ...,
        title="단가구분 (Price basis)",
        description=(
            "Price basis used to populate per-symbol cost fields. "
            "'1' = 평균단가 (average cost), '2' = BEP단가 (break-even price). "
            "Required. Length 1."
        ),
        examples=["1", "2"],
    )
    chegb: Literal["0", "2"] = Field(
        ...,
        title="체결구분 (Balance basis)",
        description=(
            "Balance basis. '0' = 결제기준잔고 (settlement-based balance, T+2), "
            "'2' = 체결기준잔고 (trade-based balance, including unsettled fills). "
            "Required. Length 1."
        ),
        examples=["0", "2"],
    )
    dangb: Literal["0", "1"] = Field(
        default="0",
        title="단일가구분 (Session selector)",
        description=(
            "Session selector for the snapshot. '0' = 정규장 (regular session, default), "
            "'1' = 시간외단일가 (after-hours single-price session). Length 1."
        ),
        examples=["0", "1"],
    )
    charge: Literal["0", "1"] = Field(
        default="0",
        title="제비용포함여부 (Cost-inclusion flag)",
        description=(
            "Whether transaction costs (fees, taxes, credit interest) are included "
            "in the returned valuation / PnL figures. '0' = exclude costs (default), "
            "'1' = include costs. Length 1."
        ),
        examples=["0", "1"],
    )
    cts_expcode: str = Field(
        default="",
        title="CTS_종목번호 (Continuation key)",
        description=(
            "Continuation key for paging through holdings. Pass an empty string "
            "on the first call. On subsequent calls reuse the ``cts_expcode`` "
            "returned in T0424OutBlock to fetch the next page."
        ),
        examples=["", "A005930"],
    )


class T0424Request(BaseModel):
    """t0424 full request envelope (header + body + setup options)."""

    header: T0424RequestHeader = T0424RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t0424",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: Dict[Literal["t0424InBlock"], T0424InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t0424",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class T0424OutBlock(BaseModel):
    """t0424OutBlock — account-level aggregate + continuation block.

    Returns the whole-account snapshot (estimated net asset, realized PnL,
    total purchase amount, etc.) together with the IDXCTS-style continuation
    key. ``cts_expcode == ""`` indicates no further pages.
    """

    sunamt: int = Field(
        default=0,
        title="추정순자산 (Estimated net asset)",
        description=(
            "Estimated net asset value across the whole account. Currency: KRW. "
            "Computed by LS — consume as returned."
        ),
        examples=[0, 12_345_678, 98_765_432_100],
    )
    dtsunik: int = Field(
        default=0,
        title="실현손익 (Realized PnL)",
        description=(
            "Realized profit and loss accumulated for the account. Currency: KRW. "
            "Sign convention is not declared in the available LS source — consume "
            "as returned."
        ),
        examples=[0, 1_500_000, -500_000],
    )
    mamt: int = Field(
        default=0,
        title="매입금액 (Total purchase amount)",
        description=(
            "Total purchase amount across all holdings. Currency: KRW."
        ),
        examples=[0, 50_000_000, 1_200_000_000],
    )
    sunamt1: int = Field(
        default=0,
        title="추정D2예수금 (Estimated D+2 cash deposit)",
        description=(
            "Estimated cash deposit available on settlement date T+2. Currency: KRW."
        ),
        examples=[0, 10_000_000, 500_000_000],
    )
    cts_expcode: str = Field(
        default="",
        title="CTS_종목번호 (Continuation key)",
        description=(
            "Continuation key for paging. Feed this value back into the next "
            "request's ``T0424InBlock.cts_expcode`` to retrieve the following "
            "page. An empty string means no further pages are available."
        ),
        examples=["", "A005930"],
    )
    tappamt: int = Field(
        default=0,
        title="평가금액 (Total valuation)",
        description=(
            "Total mark-to-market valuation across all holdings. Currency: KRW."
        ),
        examples=[0, 51_500_000, 1_350_000_000],
    )
    tdtsunik: int = Field(
        default=0,
        title="평가손익 (Total unrealized PnL)",
        description=(
            "Total unrealized profit and loss across all holdings (valuation "
            "minus purchase amount, optionally net of costs per ``charge`` flag). "
            "Currency: KRW."
        ),
        examples=[0, 1_500_000, -3_200_000],
    )


class T0424OutBlock1(BaseModel):
    """t0424OutBlock1 — per-symbol holding row.

    Each row describes one held symbol with balance quantity, average / BEP
    cost, today's / previous-day buy and sell flow, and the row-level
    valuation, unrealized PnL and return rate.
    """

    expcode: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "Six-digit Korean stock code (e.g., '005930' for Samsung Electronics). "
            "Length 6."
        ),
        examples=["005930", "000660", "035720"],
    )
    jangb: str = Field(
        default="",
        title="잔고구분 (Balance classification)",
        description=(
            "Balance classification flag. The complete enum mapping is not "
            "declared in the available LS source — consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    janqty: int = Field(
        default=0,
        title="잔고수량 (Balance quantity)",
        description="Holding quantity for this symbol (shares).",
        examples=[10, 100, 1_000],
    )
    mdposqt: int = Field(
        default=0,
        title="매도가능수량 (Sellable quantity)",
        description=(
            "Quantity available for sell-side orders. May be less than ``janqty`` "
            "when part of the position is locked (pending settlement, collateral, "
            "etc.)."
        ),
        examples=[10, 100, 950],
    )
    pamt: int = Field(
        default=0,
        title="평균단가 (Average / BEP price)",
        description=(
            "Per-share cost basis. When the request specifies ``prcgb='1'`` this "
            "is the average cost; when ``prcgb='2'`` this is the break-even price. "
            "Currency: KRW."
        ),
        examples=[3685, 70_000, 250_000],
    )
    mamt: int = Field(
        default=0,
        title="매입금액 (Purchase amount)",
        description="Purchase amount for this holding. Currency: KRW.",
        examples=[368_500, 7_000_000, 25_000_000],
    )
    sinamt: int = Field(
        default=0,
        title="대출금액 (Loan amount)",
        description=(
            "Outstanding credit / margin loan amount associated with this holding. "
            "Currency: KRW. Zero for cash-only positions."
        ),
        examples=[0, 5_000_000],
    )
    lastdt: str = Field(
        default="",
        title="만기일자 (Loan maturity date)",
        description=(
            "Maturity date of the credit / margin loan, formatted as YYYYMMDD. "
            "Empty when no loan applies."
        ),
        examples=["", "20261231"],
    )
    msat: int = Field(
        default=0,
        title="당일매수금액 (Today buy amount)",
        description="Buy amount filled on the current trading day. Currency: KRW.",
        examples=[0, 1_000_000, 5_000_000],
    )
    mpms: int = Field(
        default=0,
        title="당일매수단가 (Today buy price)",
        description="Average buy price filled on the current trading day. Currency: KRW.",
        examples=[0, 70_000, 250_000],
    )
    mdat: int = Field(
        default=0,
        title="당일매도금액 (Today sell amount)",
        description="Sell amount filled on the current trading day. Currency: KRW.",
        examples=[0, 800_000, 3_500_000],
    )
    mpmd: int = Field(
        default=0,
        title="당일매도단가 (Today sell price)",
        description="Average sell price filled on the current trading day. Currency: KRW.",
        examples=[0, 71_500, 248_000],
    )
    jsat: int = Field(
        default=0,
        title="전일매수금액 (Previous-day buy amount)",
        description="Buy amount filled on the previous trading day. Currency: KRW.",
        examples=[0, 2_000_000, 10_000_000],
    )
    jpms: int = Field(
        default=0,
        title="전일매수단가 (Previous-day buy price)",
        description="Average buy price filled on the previous trading day. Currency: KRW.",
        examples=[0, 69_500, 248_000],
    )
    jdat: int = Field(
        default=0,
        title="전일매도금액 (Previous-day sell amount)",
        description="Sell amount filled on the previous trading day. Currency: KRW.",
        examples=[0, 1_500_000, 4_500_000],
    )
    jpmd: int = Field(
        default=0,
        title="전일매도단가 (Previous-day sell price)",
        description="Average sell price filled on the previous trading day. Currency: KRW.",
        examples=[0, 70_500, 252_000],
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
    loandt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description=(
            "Origination date of the credit / margin loan, formatted as "
            "YYYYMMDD. Empty when no loan applies."
        ),
        examples=["", "20260315"],
    )
    hname: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name. Length 20.",
        examples=["삼성전자", "SK하이닉스", "카카오"],
    )
    marketgb: str = Field(
        default="",
        title="시장구분 (Market division)",
        description=(
            "Market division code (e.g., KOSPI / KOSDAQ). The complete enum "
            "mapping is not declared in the available LS source — consume as "
            "returned by LS."
        ),
        examples=["", "1", "2"],
    )
    jonggb: str = Field(
        default="",
        title="종목구분 (Symbol classification)",
        description=(
            "Symbol classification flag (common / preferred / ETF / etc.). The "
            "complete enum mapping is not declared in the available LS source — "
            "consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )
    janrt: float = Field(
        default=0.0,
        title="보유비중 (Holding ratio)",
        description=(
            "Holding ratio of this symbol versus the whole account, expressed in "
            "percent. LS may serialize this value as a string; Pydantic auto-coerces "
            "to float."
        ),
        examples=[0.0, 12.34, 45.67],
    )
    price: int = Field(
        default=0,
        title="현재가 (Current price)",
        description="Most recent traded price. Currency: KRW.",
        examples=[3685, 70_000, 250_000],
    )
    appamt: int = Field(
        default=0,
        title="평가금액 (Valuation)",
        description=(
            "Mark-to-market valuation of this holding (price × quantity, "
            "optionally net of costs per ``charge`` flag). Currency: KRW."
        ),
        examples=[0, 7_000_000, 25_000_000],
    )
    dtsunik: int = Field(
        default=0,
        title="평가손익 (Unrealized PnL)",
        description=(
            "Unrealized profit and loss for this holding (valuation minus "
            "purchase amount). Sign convention follows LS server output. "
            "Currency: KRW."
        ),
        examples=[0, 250_000, -120_000],
    )
    sunikrt: float = Field(
        default=0.0,
        title="수익율 (Return rate)",
        description=(
            "Return rate of this holding in percent. LS may serialize this value "
            "as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 3.57, -1.84],
    )
    fee: int = Field(
        default=0,
        title="수수료 (Fee)",
        description="Brokerage fee accrued for this holding. Currency: KRW.",
        examples=[0, 1_500],
    )
    tax: int = Field(
        default=0,
        title="제세금 (Tax)",
        description=(
            "Securities transaction tax and other taxes accrued for this "
            "holding. Currency: KRW."
        ),
        examples=[0, 7_500],
    )
    sininter: int = Field(
        default=0,
        title="신용이자 (Credit interest)",
        description=(
            "Credit / margin loan interest accrued for this holding. Currency: KRW. "
            "Zero for cash-only positions."
        ),
        examples=[0, 12_000],
    )


class T0424Response(BaseModel):
    """t0424 full API response envelope."""

    header: Optional[T0424ResponseHeader] = None
    cont_block: Optional[T0424OutBlock] = Field(
        default=None,
        title="t0424OutBlock (Aggregate + continuation block)",
        description=(
            "Account-level aggregates (estimated net asset, realized PnL, total "
            "purchase amount, total valuation, total unrealized PnL, estimated D+2 "
            "cash) and the continuation key ``cts_expcode``."
        ),
    )
    block: List[T0424OutBlock1] = Field(
        default_factory=list,
        title="t0424OutBlock1 (Per-symbol holding list)",
        description="List of per-symbol holding rows for the account.",
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
