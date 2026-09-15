"""Pydantic models for LS Securities OpenAPI CSPAQ12300 (BEP Price / Cash Account Balance Details).

CSPAQ12300 returns the cash-equity account balance with BEP (break-even
price) figures, in three response blocks:
    - ``CSPAQ12300OutBlock1`` (block1): echo-back of the input parameters
      (balance creation classification, fee-application code, D+2 query
      mode, price classification).
    - ``CSPAQ12300OutBlock2`` (block2): NOT PROVIDED by this API. LS may
      serialize placeholder zero/empty values; none is usable account evidence.
      Every field carries this restriction in its description and JSON schema.
    - ``CSPAQ12300OutBlock3`` (block3): per-symbol balance rows including
      sell / buy averages, current price, holding average, valuation, PnL,
      sellable quantity, credit balance and loan / maturity dates.

Source: the LS field table and all-block2-unavailable clarification supplied by
the owner on 2026-09-15; see docs/cspaq12300_contract.md. Field descriptions
follow LS official spec wording. Korean field labels
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

    Defaults select all balances, no valuation fees, all D+2 quantities and
    average unit price. The official example includes RecCnt=1 even though
    that field is absent from its input table; retain this discrepancy.
    """

    RecCnt: int = Field(
        default=1,
        title="Record count",
        description="The supplied official request example sends 1; absent from its input field table.",
        examples=[1],
    )
    BalCreTp: Literal["0", "1", "9"] = Field(
        default="0",
        title="잔고생성구분 (Balance creation classification)",
        description=(
            "Balance creation classification: '0' = all, '1' = cash equity, "
            "'9' = futures substitute collateral. Required. Length 1."
        ),
        examples=["0", "1", "9"],
    )
    CmsnAppTpCode: Literal["0", "1"] = Field(
        default="0",
        title="수수료적용구분코드 (Fee application code)",
        description=(
            "Valuation fees: '0' = exclude commission, '1' = include "
            "commission. Required. Length 1."
        ),
        examples=["0", "1"],
    )
    D2balBaseQryTp: Literal["0", "1"] = Field(
        default="0",
        title="D2잔고기준조회구분 (D+2 balance query mode)",
        description=(
            "D+2 balance filter: '0' = all rows, '1' = D+2 balance at least "
            "zero. This is not a settlement-versus-fill basis switch. "
            "Required. Length 1."
        ),
        examples=["0", "1"],
    )
    UprcTpCode: Literal["0", "1"] = Field(
        default="0",
        title="단가구분코드 (Price classification code)",
        description=(
            "Unit price basis: '0' = average price, '1' = break-even (BEP) "
            "price. Required. Length 1."
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


def _unavailable_summary_field(default, label: str, length: str, *, deprecated: bool = False):
    """Keep the LS all-block2 omission visible on every field's schema."""
    return Field(
        default=default,
        title=f"{label} (not provided)",
        description=(
            f"{label}. Not provided by LS CSPAQ12300: every OutBlock2 field is "
            "unavailable. Returned zeros and empty strings are placeholders, "
            "not measured account values. Never use this field for balances or PnL."
        ),
        deprecated=deprecated,
        json_schema_extra={
            "ls_availability": "not_provided",
            "ls_source_length": length,
            "ls_source_required": not deprecated,
            "ls_source_declared": not deprecated,
        },
    )


class CSPAQ12300OutBlock2(BaseModel):
    """Unavailable account summary; all fields are broker placeholders.

    The official table lists these fields as required, but the owner confirms
    this entire block is not provided. Preserve its wire shape for compatibility
    without presenting any of its numeric values as observed account data.
    """

    RecCnt: int = _unavailable_summary_field(0, "Record count", "5")
    BrnNm: str = _unavailable_summary_field("", "Branch name", "40")
    AcntNm: str = _unavailable_summary_field("", "Account name", "40")
    MnyOrdAbleAmt: int = _unavailable_summary_field(0, "Cash orderable amount", "16")
    MnyoutAbleAmt: int = _unavailable_summary_field(0, "Withdrawable amount", "16")
    SeOrdAbleAmt: int = _unavailable_summary_field(0, "Exchange orderable amount", "16")
    KdqOrdAbleAmt: int = _unavailable_summary_field(0, "KOSDAQ orderable amount", "16")
    HtsOrdAbleAmt: int = _unavailable_summary_field(0, "HTS orderable amount", "16")
    MgnRat100pctOrdAbleAmt: int = _unavailable_summary_field(0, "100 percent margin orderable amount", "16")
    BalEvalAmt: int = _unavailable_summary_field(0, "Balance valuation", "16")
    PchsAmt: int = _unavailable_summary_field(0, "Purchase amount", "16")
    RcvblAmt: int = _unavailable_summary_field(0, "Receivable amount", "16")
    PnlRat: float = _unavailable_summary_field(0.0, "Profit and loss ratio", "18.6")
    InvstOrgAmt: int = _unavailable_summary_field(0, "Investment principal", "20")
    InvstPlAmt: int = _unavailable_summary_field(0, "Investment profit and loss", "16")
    CrdtPldgOrdAmt: int = _unavailable_summary_field(0, "Credit collateral order amount", "16")
    Dps: int = _unavailable_summary_field(0, "Cash deposit", "16")
    D1Dps: int = _unavailable_summary_field(0, "D+1 cash deposit", "16")
    D2Dps: int = _unavailable_summary_field(0, "D+2 cash deposit", "16")
    OrdDt: str = _unavailable_summary_field("", "Order date", "8")
    MnyMgn: int = _unavailable_summary_field(0, "Cash margin", "16")
    SubstMgn: int = _unavailable_summary_field(0, "Substitute margin", "16")
    SubstAmt: int = _unavailable_summary_field(0, "Substitute amount", "16")
    PrdayBuyExecAmt: int = _unavailable_summary_field(0, "Previous-day buy execution amount", "16")
    PrdaySellExecAmt: int = _unavailable_summary_field(0, "Previous-day sell execution amount", "16")
    CrdayBuyExecAmt: int = _unavailable_summary_field(0, "Current-day buy execution amount", "16")
    CrdaySellExecAmt: int = _unavailable_summary_field(0, "Current-day sell execution amount", "16")
    EvalPnlSum: int = _unavailable_summary_field(0, "Total valuation profit and loss", "15")
    DpsastTotamt: int = _unavailable_summary_field(0, "Total deposited assets", "16")
    Evrprc: int = _unavailable_summary_field(0, "Expenses", "19")
    RuseAmt: int = _unavailable_summary_field(0, "Reusable amount", "16")
    EtclndAmt: int = _unavailable_summary_field(0, "Other loan amount", "16")
    PrcAdjstAmt: int = _unavailable_summary_field(0, "Provisional settlement amount", "16")
    D1CmsnAmt: int = _unavailable_summary_field(0, "D+1 commission", "16")
    D2CmsnAmt: int = _unavailable_summary_field(0, "D+2 commission", "16")
    D1EvrTax: int = _unavailable_summary_field(0, "D+1 taxes", "16")
    D2EvrTax: int = _unavailable_summary_field(0, "D+2 taxes", "16")
    D1SettPrergAmt: int = _unavailable_summary_field(0, "D+1 scheduled settlement", "16")
    D2SettPrergAmt: int = _unavailable_summary_field(0, "D+2 scheduled settlement", "16")
    PrdayKseMnyMgn: int = _unavailable_summary_field(0, "Previous-day KSE cash margin", "16")
    PrdayKseSubstMgn: int = _unavailable_summary_field(0, "Previous-day KSE substitute margin", "16")
    PrdayKseCrdtMnyMgn: int = _unavailable_summary_field(0, "Previous-day KSE credit cash margin", "16")
    PrdayKseCrdtSubstMgn: int = _unavailable_summary_field(0, "Previous-day KSE credit substitute margin", "16")
    CrdayKseMnyMgn: int = _unavailable_summary_field(0, "Current-day KSE cash margin", "16")
    CrdayKseSubstMgn: int = _unavailable_summary_field(0, "Current-day KSE substitute margin", "16")
    CrdayKseCrdtMnyMgn: int = _unavailable_summary_field(0, "Current-day KSE credit cash margin", "16")
    CrdayKseCrdtSubstMgn: int = _unavailable_summary_field(0, "Current-day KSE credit substitute margin", "16")
    PrdayKdqMnyMgn: int = _unavailable_summary_field(0, "Previous-day KOSDAQ cash margin", "16")
    PrdayKdqSubstMgn: int = _unavailable_summary_field(0, "Previous-day KOSDAQ substitute margin", "16")
    PrdayKdqCrdtMnyMgn: int = _unavailable_summary_field(0, "Previous-day KOSDAQ credit cash margin", "16")
    PrdayKdqCrdtSubstMgn: int = _unavailable_summary_field(0, "Previous-day KOSDAQ credit substitute margin", "16")
    CrdayKdqMnyMgn: int = _unavailable_summary_field(0, "Current-day KOSDAQ cash margin", "16")
    CrdayKdqSubstMgn: int = _unavailable_summary_field(0, "Current-day KOSDAQ substitute margin", "16")
    CrdayKdqCrdtMnyMgn: int = _unavailable_summary_field(0, "Current-day KOSDAQ credit cash margin", "16")
    CrdayKdqCrdtSubstMgn: int = _unavailable_summary_field(0, "Current-day KOSDAQ credit substitute margin", "16")
    PrdayFrbrdMnyMgn: int = _unavailable_summary_field(0, "Previous-day Freeboard cash margin", "16")
    PrdayFrbrdSubstMgn: int = _unavailable_summary_field(0, "Previous-day Freeboard substitute margin", "16")
    CrdayFrbrdMnyMgn: int = _unavailable_summary_field(0, "Current-day Freeboard cash margin", "16")
    CrdayFrbrdSubstMgn: int = _unavailable_summary_field(0, "Current-day Freeboard substitute margin", "16")
    PrdayCrbmkMnyMgn: int = _unavailable_summary_field(0, "Previous-day OTC cash margin", "16")
    PrdayCrbmkSubstMgn: int = _unavailable_summary_field(0, "Previous-day OTC substitute margin", "16")
    CrdayCrbmkMnyMgn: int = _unavailable_summary_field(0, "Current-day OTC cash margin", "16")
    CrdayCrbmkSubstMgn: int = _unavailable_summary_field(0, "Current-day OTC substitute margin", "16")
    DpspdgQty: int = _unavailable_summary_field(0, "Deposited collateral quantity", "16")
    BuyAdjstAmtD2: int = _unavailable_summary_field(0, "D+2 buy settlement amount", "16")
    SellAdjstAmtD2: int = _unavailable_summary_field(0, "D+2 sell settlement amount", "16")
    RepayRqrdAmtD1: int = _unavailable_summary_field(0, "D+1 required repayment", "16")
    RepayRqrdAmtD2: int = _unavailable_summary_field(0, "D+2 required repayment", "16")
    LoanAmt: int = _unavailable_summary_field(0, "Loan amount", "16")

    # Retained only for compatibility; the supplied block2 field is EvalPnlSum.
    EvalPnl: int = _unavailable_summary_field(
        0, "Legacy evaluation PnL (absent from the supplied source)", "unknown", deprecated=True
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
        title="Sell price",
        description=(
            "Broker-reported sell price, source length 21.4. The supplied "
            "label does not establish an average-cost or realized-PnL basis."
        ),
        examples=[0.0, 71_500.0, 248_000.0],
    )
    BuyPrc: float = Field(
        default=0.0,
        title="Buy price",
        description=(
            "Broker-reported buy price, source length 21.4. Use AvrUprc with "
            "the explicit request basis for average or BEP unit price."
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
            "Per-share cost on the requested basis: UprcTpCode=0 selects "
            "average unit price and 1 selects BEP. Preserve the basis alongside "
            "the value; do not label a BEP response as average purchase price."
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
            "Raw broker PnL fraction, retained without rescaling in this model. "
            "For the average-cost, commission-excluded request (UprcTpCode=0, "
            "CmsnAppTpCode=0), the owner example 0.378333 matches 22700/60000. "
            "A 2026-09-15 live observation -0.003759 matches -30/7980. "
            "The evidence collector multiplies by 100 only when explicit "
            "EvalPnl/PchsAmt confirms this fraction within six-decimal rounding."
        ),
        examples=[0.0, 0.378333],
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
        title="Legacy maturity field",
        description="Absent from the supplied source. Use explicitly observed DueDt; no alias is inferred.",
        deprecated=True,
        examples=["", "20261231"],
    )
    SellQty: int = Field(
        default=0,
        title="매도수량 (Sell quantity)",
        description="Legacy field absent from the supplied source. Do not infer an alias to a dated execution quantity.",
        deprecated=True,
        examples=[0, 50, 500],
    )
    BuyQty: int = Field(
        default=0,
        title="매수수량 (Buy quantity)",
        description="Legacy field absent from the supplied source. Do not infer an alias to a dated execution quantity.",
        deprecated=True,
        examples=[0, 100, 1_000],
    )

    SecBalPtnCode: str = Field(
        default="",
        title="Securities balance type code",
        description="Securities balance type code. Source length 2; verify model_fields_set before use.",
    )
    SecBalPtnNm: str = Field(
        default="",
        title="Securities balance type name",
        description="Securities balance type name. Source length 40; verify model_fields_set before use.",
    )
    CrdayBuyExecQty: int = Field(
        default=0,
        title="Current-day buy execution quantity",
        description="Current-day buy execution quantity. Source length 16; verify model_fields_set before use.",
    )
    CrdaySellExecQty: int = Field(
        default=0,
        title="Current-day sell execution quantity",
        description="Current-day sell execution quantity. Source length 16; verify model_fields_set before use.",
    )
    SellPnlAmt: int = Field(
        default=0,
        title="Sell profit and loss amount",
        description="Sell profit and loss amount. Source length 16; verify model_fields_set before use.",
    )
    DueDt: str = Field(
        default="",
        title="Maturity date",
        description="Maturity date. Source length 8; verify model_fields_set before use.",
    )
    PrdaySellExecPrc: float = Field(
        default=0.0,
        title="Previous-day sell execution price",
        description="Previous-day sell execution price. Source length 13.2; verify model_fields_set before use.",
    )
    PrdaySellQty: int = Field(
        default=0,
        title="Previous-day sell quantity",
        description="Previous-day sell quantity. Source length 16; verify model_fields_set before use.",
    )
    PrdayBuyExecPrc: float = Field(
        default=0.0,
        title="Previous-day buy execution price",
        description="Previous-day buy execution price. Source length 13.2; verify model_fields_set before use.",
    )
    PrdayBuyQty: int = Field(
        default=0,
        title="Previous-day buy quantity",
        description="Previous-day buy quantity. Source length 16; verify model_fields_set before use.",
    )
    SellOrdQty: int = Field(
        default=0,
        title="Sell order quantity",
        description="Sell order quantity. Source length 16; verify model_fields_set before use.",
    )
    CrdayBuyExecAmt: int = Field(
        default=0,
        title="Current-day buy execution amount",
        description="Current-day buy execution amount. Source length 16; verify model_fields_set before use.",
    )
    CrdaySellExecAmt: int = Field(
        default=0,
        title="Current-day sell execution amount",
        description="Current-day sell execution amount. Source length 16; verify model_fields_set before use.",
    )
    PrdayBuyExecAmt: int = Field(
        default=0,
        title="Previous-day buy execution amount",
        description="Previous-day buy execution amount. Source length 16; verify model_fields_set before use.",
    )
    PrdaySellExecAmt: int = Field(
        default=0,
        title="Previous-day sell execution amount",
        description="Previous-day sell execution amount. Source length 16; verify model_fields_set before use.",
    )
    MnyOrdAbleAmt: int = Field(
        default=0,
        title="Cash orderable amount",
        description="Cash orderable amount. Source length 16; verify model_fields_set before use.",
    )
    OrdAbleAmt: int = Field(
        default=0,
        title="Orderable amount",
        description="Orderable amount. Source length 16; verify model_fields_set before use.",
    )
    SellUnercQty: int = Field(
        default=0,
        title="Unfilled sell quantity",
        description="Unfilled sell quantity. Source length 16; verify model_fields_set before use.",
    )
    SellUnsttQty: int = Field(
        default=0,
        title="Unsettled sell quantity",
        description="Unsettled sell quantity. Source length 16; verify model_fields_set before use.",
    )
    BuyUnercQty: int = Field(
        default=0,
        title="Unfilled buy quantity",
        description="Unfilled buy quantity. Source length 16; verify model_fields_set before use.",
    )
    BuyUnsttQty: int = Field(
        default=0,
        title="Unsettled buy quantity",
        description="Unsettled buy quantity. Source length 16; verify model_fields_set before use.",
    )
    UnsttQty: int = Field(
        default=0,
        title="Unsettled quantity",
        description="Unsettled quantity. Source length 16; verify model_fields_set before use.",
    )
    UnercQty: int = Field(
        default=0,
        title="Unfilled quantity",
        description="Unfilled quantity. Source length 16; verify model_fields_set before use.",
    )
    PrdayCprc: float = Field(
        default=0.0,
        title="Previous-day closing price",
        description="Previous-day closing price. Source length 15.2; verify model_fields_set before use.",
    )
    PchsAmt: int = Field(
        default=0,
        title="Purchase amount",
        description="Purchase amount. Source length 16; verify model_fields_set before use.",
    )
    RegMktCode: str = Field(
        default="",
        title="Registered market code",
        description="Registered market code. Source length 2; verify model_fields_set before use.",
    )
    LoanDtlClssCode: str = Field(
        default="",
        title="Detailed loan classification code",
        description="Detailed loan classification code. Source length 2; verify model_fields_set before use.",
    )
    DpspdgLoanQty: int = Field(
        default=0,
        title="Deposited collateral loan quantity",
        description="Deposited collateral loan quantity. Source length 16; verify model_fields_set before use.",
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
            "Not provided by LS. The entire block is unavailable even when "
            "its fields contain explicit zero/empty placeholders."
        ),
    )
    block2_status: Literal["not_provided"] = Field(
        default="not_provided",
        description="All CSPAQ12300OutBlock2 fields are unavailable, regardless of their wire values.",
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
    _positions_blocks_present: bool = PrivateAttr(default=False)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
