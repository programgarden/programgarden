"""Pydantic models for LS Securities OpenAPI CSPAQ12300 (BEP Price / Cash Account Balance Details).

CSPAQ12300 returns the cash-equity account balance with BEP (break-even
price) figures, in three response blocks:
    - ``CSPAQ12300OutBlock1`` (block1): echo-back of the input parameters
      (balance creation classification, fee-application code, D+2 query
      mode, price classification).
    - ``CSPAQ12300OutBlock2`` (block2): account-level summary — branch and
      account names, cash orderable amount, balance valuation, purchase
      amount, evaluation PnL and return rate, deposited assets total,
      invested principal and PnL, and the deposit ladder (D, D+1, D+2).
    - ``CSPAQ12300OutBlock3`` (block3): per-symbol balance rows including
      sell / buy averages, current price, holding average, valuation, PnL,
      sellable quantity, credit balance and loan / maturity dates.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ12300RequestHeader(BlockRequestHeader):
    """CSPAQ12300 request header. Inherits the standard LS request header schema."""
    pass


class CSPAQ12300ResponseHeader(BlockResponseHeader):
    """CSPAQ12300 response header. Standard LS response header schema."""
    pass


class CSPAQ12300InBlock1(BaseModel):
    """CSPAQ12300InBlock1 — input block for BEP price / cash account balance.

    All fields default to ``"0"`` which selects the standard balance view.
    Adjust the classification flags to scope the query to a specific
    balance-creation source, fee-application mode, D+2 view or price basis.
    """

    BalCreTp: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        default="0",
        title="잔고생성구분 (Balance creation classification)",
        description=(
            "Source classification for the returned balance rows. "
            "'0' = 주식잔고 (cash equity balance, default), '1' = 기타 (other), "
            "'2' = 재투자잔고 (reinvestment balance), '3' = 유통대주 "
            "(circulating short-loan), '4' = 자기융자 (self credit), "
            "'5' = 유통대주 (circulating short-loan), '6' = 자기대주 "
            "(self short-loan). Length 1."
        ),
        examples=["0", "1", "4"],
    )
    CmsnAppTpCode: str = Field(
        default="0",
        title="수수료적용구분코드 (Fee application code)",
        description=(
            "Fee-application classification code controlling whether the "
            "returned valuations are net of fees. The complete enum mapping is "
            "not declared in the available LS source — consume per LS "
            "convention. Default ``\"0\"``."
        ),
        examples=["0", "1"],
    )
    D2balBaseQryTp: str = Field(
        default="0",
        title="D2잔고기준조회구분 (D+2 balance query mode)",
        description=(
            "Selector for the D+2 balance view (settlement-date basis vs. "
            "trade-date basis). The complete enum mapping is not declared in "
            "the available LS source — consume per LS convention. "
            "Default ``\"0\"``."
        ),
        examples=["0", "1"],
    )
    UprcTpCode: str = Field(
        default="0",
        title="단가구분코드 (Price classification code)",
        description=(
            "Price-basis classification used to populate the per-row average "
            "and BEP price fields. The complete enum mapping is not declared "
            "in the available LS source — consume per LS convention. "
            "Default ``\"0\"``."
        ),
        examples=["0", "1"],
    )


class CSPAQ12300Request(BaseModel):
    """CSPAQ12300 full request envelope (header + body + setup options)."""

    header: CSPAQ12300RequestHeader = CSPAQ12300RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ12300",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPAQ12300InBlock1"], CSPAQ12300InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ12300",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPAQ12300OutBlock1(BaseModel):
    """CSPAQ12300OutBlock1 — input echo-back block.

    Returns the resolved account context together with the input parameters
    as observed by the server.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this echo block.",
        examples=[0, 1],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description=(
            "Resolved account number associated with the authenticated session. "
            "Length 11."
        ),
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password marker)",
        description=(
            "Account password placeholder. Always returned redacted by the "
            "server — never the plaintext password."
        ),
        examples=[""],
    )
    BalCreTp: str = Field(
        default="0",
        title="잔고생성구분 (Balance creation classification)",
        description="Echo of the input ``BalCreTp``.",
        examples=["0", "1"],
    )
    CmsnAppTpCode: str = Field(
        default="0",
        title="수수료적용구분코드 (Fee application code)",
        description="Echo of the input ``CmsnAppTpCode``.",
        examples=["0", "1"],
    )
    D2balBaseQryTp: str = Field(
        default="0",
        title="D2잔고기준조회구분 (D+2 balance query mode)",
        description="Echo of the input ``D2balBaseQryTp``.",
        examples=["0", "1"],
    )
    UprcTpCode: str = Field(
        default="0",
        title="단가구분코드 (Price classification code)",
        description="Echo of the input ``UprcTpCode``.",
        examples=["0", "1"],
    )


class CSPAQ12300OutBlock2(BaseModel):
    """CSPAQ12300OutBlock2 — account summary block.

    Returns the account-level snapshot: branch / account display names,
    cash orderable amount, total balance valuation and purchase amount,
    evaluation PnL and return rate, deposited assets total, invested
    principal and PnL, and the cash deposit ladder (D, D+1, D+2).
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this block.",
        examples=[0, 1],
    )
    BrnNm: str = Field(
        default="",
        title="지점명 (Branch name)",
        description="Korean display name of the managing branch.",
        examples=["", "본점", "강남지점"],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account display name)",
        description="Korean display name of the account.",
        examples=["", "홍길동"],
    )
    MnyOrdAbleAmt: int = Field(
        default=0,
        title="현금주문가능금액 (Cash orderable amount)",
        description="Cash amount available for placing buy orders. Currency: KRW.",
        examples=[0, 5_000_000, 100_000_000],
    )
    BalEvalAmt: int = Field(
        default=0,
        title="잔고평가금액 (Balance valuation)",
        description=(
            "Total mark-to-market valuation across all holdings. Currency: KRW."
        ),
        examples=[0, 51_500_000, 1_350_000_000],
    )
    PchsAmt: int = Field(
        default=0,
        title="매입금액 (Purchase amount)",
        description=(
            "Total purchase amount across all holdings. Currency: KRW."
        ),
        examples=[0, 50_000_000, 1_200_000_000],
    )
    EvalPnl: int = Field(
        default=0,
        title="평가손익 (Evaluation PnL)",
        description=(
            "Unrealized profit and loss across all holdings (valuation minus "
            "purchase amount). Currency: KRW."
        ),
        examples=[0, 1_500_000, -3_200_000],
    )
    PnlRat: float = Field(
        default=0.0,
        title="손익율 (Return rate)",
        description=(
            "Return rate of the account in percent. LS may serialize this "
            "value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 3.57, -1.84],
    )
    DpsastTotamt: int = Field(
        default=0,
        title="예탁자산총액 (Deposited assets total)",
        description=(
            "Sum of deposited assets across cash, securities valuation and "
            "deposits. Currency: KRW."
        ),
        examples=[0, 100_000_000],
    )
    InvstOrgAmt: int = Field(
        default=0,
        title="투자원금 (Invested principal)",
        description="Net invested principal across the account. Currency: KRW.",
        examples=[0, 80_000_000],
    )
    InvstPlAmt: int = Field(
        default=0,
        title="투자손익 (Invested PnL)",
        description=(
            "Net invested profit and loss across the account. Sign convention "
            "follows LS server output. Currency: KRW."
        ),
        examples=[0, 5_000_000, -1_500_000],
    )
    Dps: int = Field(
        default=0,
        title="예수금 (Cash deposit / D)",
        description="Same-day cash deposit balance. Currency: KRW.",
        examples=[0, 5_000_000],
    )
    D1Dps: int = Field(
        default=0,
        title="D1예수금 (D+1 cash deposit)",
        description="Cash deposit balance available on T+1. Currency: KRW.",
        examples=[0, 5_500_000],
    )
    D2Dps: int = Field(
        default=0,
        title="D2예수금 (D+2 cash deposit)",
        description="Cash deposit balance available on T+2. Currency: KRW.",
        examples=[0, 6_000_000],
    )


class CSPAQ12300OutBlock3(BaseModel):
    """CSPAQ12300OutBlock3 — per-symbol balance row.

    Each row describes one held symbol with sell / buy averages, current
    price, holding average, balance valuation, evaluation PnL and return
    rate, sellable quantity, credit balance and credit loan / maturity dates.
    """

    IsuNo: str = Field(
        default="",
        title="종목번호 (Stock code)",
        description=(
            "LS-prefixed Korean stock code (``A`` + 6-digit short code), "
            "e.g., ``A005930`` for Samsung Electronics."
        ),
        examples=["", "A005930", "A000660"],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Stock display name)",
        description="Korean stock display name.",
        examples=["", "삼성전자", "SK하이닉스"],
    )
    BalQty: int = Field(
        default=0,
        title="잔고수량 (Balance quantity)",
        description="Holding quantity for this symbol (shares).",
        examples=[10, 100, 1_000],
    )
    BnsBaseBalQty: int = Field(
        default=0,
        title="매매기준잔고수량 (Trade-basis balance quantity)",
        description=(
            "Holding quantity on a trade-basis (post-fill, pre-settlement) "
            "view. May differ from ``BalQty`` for unsettled trades."
        ),
        examples=[10, 100, 1_000],
    )
    SellPrc: float = Field(
        default=0.0,
        title="매도단가 (Average sell price)",
        description=(
            "Average sell price for trades reflected in this row. LS may "
            "serialize this value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 71_500.0, 248_000.0],
    )
    BuyPrc: float = Field(
        default=0.0,
        title="매수단가 (Average buy price)",
        description=(
            "Average buy price for trades reflected in this row. LS may "
            "serialize this value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 70_000.0, 250_000.0],
    )
    NowPrc: float = Field(
        default=0.0,
        title="현재가 (Current price)",
        description="Most recent traded price. Currency: KRW.",
        examples=[0.0, 70_000.0, 250_000.0],
    )
    AvrUprc: float = Field(
        default=0.0,
        title="평균단가 (Holding average price)",
        description=(
            "Per-share holding cost basis (depends on ``UprcTpCode`` selected "
            "on input). LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[0.0, 69_500.0, 250_000.0],
    )
    BalEvalAmt: int = Field(
        default=0,
        title="잔고평가금액 (Balance valuation)",
        description=(
            "Mark-to-market valuation of this holding. Currency: KRW."
        ),
        examples=[0, 7_000_000, 25_000_000],
    )
    EvalPnl: int = Field(
        default=0,
        title="평가손익 (Evaluation PnL)",
        description=(
            "Unrealized profit and loss for this holding (valuation minus "
            "purchase). Sign convention follows LS server output. "
            "Currency: KRW."
        ),
        examples=[0, 250_000, -120_000],
    )
    PnlRat: float = Field(
        default=0.0,
        title="손익율 (Return rate)",
        description=(
            "Return rate of this holding in percent. LS may serialize this "
            "value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 3.57, -1.84],
    )
    SellAbleQty: int = Field(
        default=0,
        title="매도가능수량 (Sellable quantity)",
        description=(
            "Quantity available for sell-side orders. May be less than "
            "``BalQty`` when part of the position is locked."
        ),
        examples=[10, 100, 950],
    )
    CrdtAmt: int = Field(
        default=0,
        title="신용금액 (Credit balance)",
        description=(
            "Outstanding credit / margin balance associated with this "
            "holding. Currency: KRW. Zero for cash-only positions."
        ),
        examples=[0, 5_000_000],
    )
    LoanDt: str = Field(
        default="",
        title="대출일 (Loan origination date)",
        description=(
            "Origination date of the credit / margin loan, formatted as "
            "YYYYMMDD. Empty when no loan applies."
        ),
        examples=["", "20260315"],
    )
    Expdt: str = Field(
        default="",
        title="만기일 (Loan maturity date)",
        description=(
            "Maturity date of the credit / margin loan, formatted as "
            "YYYYMMDD. Empty when no loan applies."
        ),
        examples=["", "20261231"],
    )
    SellQty: int = Field(
        default=0,
        title="매도수량 (Sell quantity)",
        description="Cumulative sell quantity reflected in this row (shares).",
        examples=[0, 50, 500],
    )
    BuyQty: int = Field(
        default=0,
        title="매수수량 (Buy quantity)",
        description="Cumulative buy quantity reflected in this row (shares).",
        examples=[0, 100, 1_000],
    )


class CSPAQ12300Response(BaseModel):
    """CSPAQ12300 full API response envelope."""

    header: Optional[CSPAQ12300ResponseHeader] = None
    block1: Optional[CSPAQ12300OutBlock1] = Field(
        default=None,
        title="CSPAQ12300OutBlock1 (Input echo-back)",
        description="Echo-back of the input parameters with resolved account context.",
    )
    block2: Optional[CSPAQ12300OutBlock2] = Field(
        default=None,
        title="CSPAQ12300OutBlock2 (Account summary)",
        description=(
            "Account-level summary: branch / account names, cash orderable "
            "amount, valuation, PnL, deposited assets and the deposit ladder."
        ),
    )
    block3: List[CSPAQ12300OutBlock3] = Field(
        default_factory=list,
        title="CSPAQ12300OutBlock3 (Per-symbol balance list)",
        description="List of per-symbol holding rows for the account.",
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
