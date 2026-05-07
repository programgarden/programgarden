"""Pydantic models for LS Securities OpenAPI CSPAQ12200 (Cash Account Deposit / Orderable / Total Valuation).

CSPAQ12200 returns the comprehensive asset snapshot for a Korean cash
equity account: cash and substitute deposits, orderable / withdrawable
amounts, margin (cash and substitute), the deposit ladder (D / D+1 / D+2),
balance valuation, deposited assets total, invested principal / PnL /
return rate, accumulated invested amount, receivables, credit-collateral
re-use, dispose-restricted amount, exchange / KOSDAQ orderable amounts,
two margin-rate buckets (35% / 50%), credit orderable amount, two daily
settlement amounts (previous-day / current-day buy / sell settlements),
overdue repayment requirements (D+1 / D+2), credit loan amounts (D+1 /
D+2), receivables total, collateral total, deposited assets grand total
and credit-set guarantee amount.

⚠ Field semantic change (2026-04-11 LS Securities, 12:00 KST):
    ``MgnRat100pctOrdAbleAmt`` now exposes the **미수주문가능금액**
    (orderable amount eligible for 미수 / credit ordering); the legacy
    증거금률 100% 주문가능 금액 semantic was migrated to the newly added
    ``RcvblUablOrdAbleAmt`` (미수불가주문가능금액). Callers that previously
    read ``MgnRat100pctOrdAbleAmt`` for 증거금률 100% must migrate to
    ``RcvblUablOrdAbleAmt``.

Two response blocks are returned:
    - ``CSPAQ12200OutBlock1`` (block1): echo-back of the input parameters
      together with the resolved managing branch and account number.
    - ``CSPAQ12200OutBlock2`` (block2): the full asset snapshot described
      above.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ12200RequestHeader(BlockRequestHeader):
    """CSPAQ12200 request header. Inherits the standard LS request header schema."""
    pass


class CSPAQ12200ResponseHeader(BlockResponseHeader):
    """CSPAQ12200 response header. Standard LS response header schema."""
    pass


class CSPAQ12200InBlock1(BaseModel):
    """CSPAQ12200InBlock1 — input block for cash account deposit / orderable / total valuation.

    The single ``BalCreTp`` flag scopes the snapshot to a specific balance
    creation source.
    """

    BalCreTp: Literal["0", "1", "2", "3", "4", "5", "6"] = Field(
        default="0",
        title="잔고생성구분 (Balance creation classification)",
        description=(
            "Source classification for the asset snapshot. "
            "'0' = 주식잔고 (cash equity balance, default), '1' = 기타 (other), "
            "'2' = 재투자잔고 (reinvestment balance), '3' = 유통대주 "
            "(circulating short-loan), '4' = 자기융자 (self credit), "
            "'5' = 유통대주 (circulating short-loan), '6' = 자기대주 "
            "(self short-loan). Length 1."
        ),
        examples=["0", "1", "4"],
    )


class CSPAQ12200Request(BaseModel):
    """CSPAQ12200 full request envelope (header + body + setup options)."""

    header: CSPAQ12200RequestHeader = CSPAQ12200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ12200",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPAQ12200InBlock1"], CSPAQ12200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ12200",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPAQ12200OutBlock1(BaseModel):
    """CSPAQ12200OutBlock1 — input echo-back block.

    Returns the resolved managing branch and account number alongside the
    input parameters.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this echo block.",
        examples=[0, 1],
    )
    MgmtBrnNo: str = Field(
        default="",
        title="관리지점번호 (Managing branch number)",
        description="Branch number managing this account.",
        examples=["", "001"],
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


class CSPAQ12200OutBlock2(BaseModel):
    """CSPAQ12200OutBlock2 — comprehensive asset snapshot block.

    Returns the full account-level asset state across cash, substitute
    collateral, margin requirements, daily settlement ladders, credit
    receivables and credit-collateral metrics.

    See module docstring for the 2026-04-11 semantic migration of
    ``MgnRat100pctOrdAbleAmt`` and the new ``RcvblUablOrdAbleAmt`` field.
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
    MnyoutAbleAmt: int = Field(
        default=0,
        title="현금출금가능금액 (Cash withdrawable amount)",
        description="Cash amount available for withdrawal. Currency: KRW.",
        examples=[0, 5_000_000, 100_000_000],
    )
    SubstOrdAbleAmt: int = Field(
        default=0,
        title="대용주문가능금액 (Substitute orderable amount)",
        description=(
            "Substitute-collateral amount available for placing buy orders. "
            "Currency: KRW."
        ),
        examples=[0, 2_000_000, 50_000_000],
    )
    Dps: int = Field(
        default=0,
        title="예수금 (Cash deposit)",
        description="Cash deposit balance. Currency: KRW.",
        examples=[0, 5_000_000, 100_000_000],
    )
    SubstAmt: int = Field(
        default=0,
        title="대용금액 (Substitute collateral amount)",
        description=(
            "Substitute (non-cash collateral) amount available against margin "
            "requirements. Currency: KRW."
        ),
        examples=[0, 2_000_000, 50_000_000],
    )
    MgnMny: int = Field(
        default=0,
        title="증거금현금 (Cash margin)",
        description=(
            "Cash component of the margin requirement currently posted. "
            "Currency: KRW."
        ),
        examples=[0, 1_000_000, 10_000_000],
    )
    MgnSubst: int = Field(
        default=0,
        title="증거금대용 (Substitute margin)",
        description=(
            "Substitute (non-cash collateral) component of the margin "
            "requirement currently posted. Currency: KRW."
        ),
        examples=[0, 500_000, 5_000_000],
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
    BalEvalAmt: int = Field(
        default=0,
        title="잔고평가금액 (Balance valuation)",
        description=(
            "Total mark-to-market valuation across all holdings. Currency: KRW."
        ),
        examples=[0, 51_500_000, 1_350_000_000],
    )
    DpsastSum: int = Field(
        default=0,
        title="예탁자산합계 (Deposited assets total)",
        description=(
            "Sum of deposited assets across cash, substitute collateral and "
            "balance valuation. Currency: KRW."
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
        title="투자손익금액 (Invested PnL amount)",
        description=(
            "Net invested profit and loss across the account. Sign convention "
            "follows LS server output. Currency: KRW."
        ),
        examples=[0, 5_000_000, -1_500_000],
    )
    PnlRat: float = Field(
        default=0.0,
        title="손익율 (Return rate)",
        description=(
            "Return rate of the account in percent. LS may serialize this "
            "value as a string; Pydantic auto-coerces to float."
        ),
        examples=[0.0, 6.25, -1.84],
    )
    InvstAsm: int = Field(
        default=0,
        title="투자누계금액 (Cumulative invested amount)",
        description=(
            "Cumulative invested amount over the account lifetime. "
            "Currency: KRW."
        ),
        examples=[0, 200_000_000],
    )
    RcvblAmt: int = Field(
        default=0,
        title="미수금액 (Receivable / credit balance)",
        description=(
            "Outstanding 미수 (missed-payment / credit) amount owed by the "
            "account. Currency: KRW."
        ),
        examples=[0, 1_000_000],
    )
    CrdtPldgRuseAmt: int = Field(
        default=0,
        title="신용담보재사용금액 (Credit collateral re-use amount)",
        description=(
            "Amount of credit collateral re-used to support additional credit "
            "positions. Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    DpslRestrcAmt: int = Field(
        default=0,
        title="처분제한금액 (Dispose-restricted amount)",
        description=(
            "Amount currently restricted from disposal (e.g., locked for "
            "settlement or regulatory hold). Currency: KRW."
        ),
        examples=[0, 1_000_000],
    )
    RcvblUablOrdAbleAmt: int = Field(
        default=0,
        title="미수불가주문가능금액 (Order-able amount disallowing 미수 / credit ordering)",
        description=(
            "Order-able amount that disallows 미수 (missed-payment / credit) "
            "usage. Added by LS Securities on 2026-04-11. From 2026-04-11 "
            "12:00 KST onward, this field carries the legacy 증거금률 100% "
            "주문가능 금액 (100% margin-rate order-able amount) that was "
            "previously exposed by ``MgnRat100pctOrdAbleAmt``. Callers that "
            "previously read ``MgnRat100pctOrdAbleAmt`` for 증거금률 100% "
            "semantics must migrate to this field. Currency: KRW. Length 16. "
            "Pydantic auto-coerces."
        ),
        examples=[306, 0, 100_000],
    )
    MnyoutAbleAmt2: int = Field(
        default=0,
        title="현금출금가능금액2 (Cash withdrawable amount 2)",
        description=(
            "Alternate cash-withdrawable amount under a different settlement "
            "model. The exact computation difference versus ``MnyoutAbleAmt`` "
            "is not declared in the available LS source — consume as returned "
            "by LS. Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    SeOrdAbleAmt: int = Field(
        default=0,
        title="거래소주문가능금액 (Exchange orderable amount)",
        description=(
            "Orderable amount applicable on the KRX main board. Currency: KRW."
        ),
        examples=[0, 5_000_000, 100_000_000],
    )
    KdqOrdAbleAmt: int = Field(
        default=0,
        title="코스닥주문가능금액 (KOSDAQ orderable amount)",
        description=(
            "Orderable amount applicable on the KOSDAQ market. Currency: KRW."
        ),
        examples=[0, 4_500_000, 90_000_000],
    )
    MgnRat100pctOrdAbleAmt: int = Field(
        default=0,
        title="미수주문가능금액 (Order-able amount eligible for 미수 / credit ordering)",
        description=(
            "Order-able amount eligible for 미수주문 (missed-payment / credit "
            "ordering). Field semantic was changed by LS Securities on "
            "2026-04-11 12:00 KST: until 2026-04-10 this field held 증거금률 "
            "100% 주문가능 금액 (100% margin-rate order-able amount). From "
            "2026-04-11 onward, the legacy 증거금률 100% value is exposed by "
            "``RcvblUablOrdAbleAmt`` instead. Callers needing the 증거금률 "
            "100% semantic must migrate to ``RcvblUablOrdAbleAmt``. The Korean "
            "field title was also updated upstream to reflect the new "
            "semantic. Currency: KRW. Length 16. Pydantic auto-coerces."
        ),
        examples=[306, 0, 100_000],
    )
    CrdtOrdAbleAmt: int = Field(
        default=0,
        title="신용주문가능금액 (Credit orderable amount)",
        description=(
            "Orderable amount available under credit (margin loan) financing. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )
    MgnRat35ordAbleAmt: int = Field(
        default=0,
        title="증거금률35%주문가능금액 (35% margin-rate orderable)",
        description=(
            "Orderable amount under a 35% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 14_000_000],
    )
    MgnRat50ordAbleAmt: int = Field(
        default=0,
        title="증거금률50%주문가능금액 (50% margin-rate orderable)",
        description=(
            "Orderable amount under a 50% margin-rate bucket. Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )
    PrdaySellAdjstAmt: int = Field(
        default=0,
        title="전일매도정산금액 (Previous-day sell settlement)",
        description=(
            "Sell-side settlement amount carried over from the previous "
            "trading day. Currency: KRW."
        ),
        examples=[0, 3_500_000],
    )
    PrdayBuyAdjstAmt: int = Field(
        default=0,
        title="전일매수정산금액 (Previous-day buy settlement)",
        description=(
            "Buy-side settlement amount carried over from the previous "
            "trading day. Currency: KRW."
        ),
        examples=[0, 7_000_000],
    )
    CrdaySellAdjstAmt: int = Field(
        default=0,
        title="금일매도정산금액 (Today sell settlement)",
        description=(
            "Sell-side settlement amount accrued during the current trading "
            "day. Currency: KRW."
        ),
        examples=[0, 2_500_000],
    )
    CrdayBuyAdjstAmt: int = Field(
        default=0,
        title="금일매수정산금액 (Today buy settlement)",
        description=(
            "Buy-side settlement amount accrued during the current trading "
            "day. Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    D1ovdRepayRqrdAmt: int = Field(
        default=0,
        title="D1연체변제소요금액 (D+1 overdue repayment required)",
        description=(
            "Amount required to repay overdue obligations on T+1. "
            "Currency: KRW."
        ),
        examples=[0, 1_000_000],
    )
    D2ovdRepayRqrdAmt: int = Field(
        default=0,
        title="D2연체변제소요금액 (D+2 overdue repayment required)",
        description=(
            "Amount required to repay overdue obligations on T+2. "
            "Currency: KRW."
        ),
        examples=[0, 1_500_000],
    )
    D1MloanAmt: int = Field(
        default=0,
        title="D1융자금액 (D+1 margin loan)",
        description="Outstanding margin loan amount on T+1. Currency: KRW.",
        examples=[0, 5_000_000],
    )
    D2MloanAmt: int = Field(
        default=0,
        title="D2융자금액 (D+2 margin loan)",
        description="Outstanding margin loan amount on T+2. Currency: KRW.",
        examples=[0, 5_000_000],
    )
    RcvblSumAmt: int = Field(
        default=0,
        title="미수합계금액 (Receivables total)",
        description=(
            "Total receivable / credit balance across all classifications. "
            "Currency: KRW."
        ),
        examples=[0, 1_500_000],
    )
    PldgSumAmt: int = Field(
        default=0,
        title="담보합계금액 (Collateral total)",
        description=(
            "Total collateral posted across all classifications. Currency: KRW."
        ),
        examples=[0, 50_000_000],
    )
    DpsastTotamt: int = Field(
        default=0,
        title="예탁자산총금액 (Deposited assets grand total)",
        description=(
            "Grand total of deposited assets across cash, substitute "
            "collateral, balance valuation and ancillary balances. "
            "Currency: KRW."
        ),
        examples=[0, 150_000_000],
    )
    Imreq: int = Field(
        default=0,
        title="신용설정보증금 (Credit-set guarantee amount)",
        description=(
            "Guarantee amount required to maintain credit line entitlement. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )


class CSPAQ12200Response(BaseModel):
    """CSPAQ12200 full API response envelope."""

    header: Optional[CSPAQ12200ResponseHeader] = None
    block1: Optional[CSPAQ12200OutBlock1] = Field(
        default=None,
        title="CSPAQ12200OutBlock1 (Input echo-back)",
        description=(
            "Echo-back of the input parameters with resolved managing branch "
            "and account number."
        ),
    )
    block2: Optional[CSPAQ12200OutBlock2] = Field(
        default=None,
        title="CSPAQ12200OutBlock2 (Comprehensive asset snapshot)",
        description=(
            "Account-level asset snapshot: cash and substitute deposits, "
            "orderable / withdrawable amounts, margin, deposit ladder, "
            "balance valuation, deposited assets, invested PnL and return "
            "rate, credit receivables, exchange / KOSDAQ orderable amounts, "
            "margin-rate buckets, daily settlement ladders, overdue "
            "repayment, margin loan and credit-set guarantee."
        ),
    )
    status_code: Optional[int] = Field(default=None, title="HTTP status code")
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(default=None, title="Error message")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
