"""Pydantic models for LS Securities OpenAPI CSPAQ22200 (Cash Account Deposit / Orderable / Total Valuation v2).

CSPAQ22200 is a sibling of ``CSPAQ12200``: it returns a comprehensive
asset snapshot for a Korean cash equity account with focus on the credit
collateral side — credit-collateral order amount, credit collateral
posted (cash and substitute), credit-set guarantee, original / sub
collateral totals, post-change collateral ratio, required and shortfall
collateral amounts, and the sell-side collateralized loan amount.

⚠ Field semantic change (2026-04-11 LS Securities, 12:00 KST):
    ``MgnRat100pctOrdAbleAmt`` now exposes the **미수주문가능금액**
    (orderable amount eligible for 미수 / credit ordering); the legacy
    증거금률 100% 주문가능 금액 semantic was migrated to the newly added
    ``RcvblUablOrdAbleAmt`` (미수불가주문가능금액). Callers that previously
    read ``MgnRat100pctOrdAbleAmt`` for 증거금률 100% must migrate to
    ``RcvblUablOrdAbleAmt``.

Two response blocks are returned:
    - ``CSPAQ22200OutBlock1`` (block1): minimal echo-back (managing branch
      number is currently unused).
    - ``CSPAQ22200OutBlock2`` (block2): the asset / collateral snapshot
      described above.

Field descriptions follow LS official spec wording. Korean field labels
(한글명) are appended in parentheses so AI chatbots can map between English
descriptions and Korean LS documentation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAQ22200RequestHeader(BlockRequestHeader):
    """CSPAQ22200 request header. Inherits the standard LS request header schema."""
    pass


class CSPAQ22200ResponseHeader(BlockResponseHeader):
    """CSPAQ22200 response header. Standard LS response header schema."""
    pass


class CSPAQ22200InBlock1(BaseModel):
    """CSPAQ22200InBlock1 — input block for cash account deposit / orderable / total valuation v2.

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


class CSPAQ22200Request(BaseModel):
    """CSPAQ22200 full request envelope (header + body + setup options)."""

    header: CSPAQ22200RequestHeader = CSPAQ22200RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAQ22200",
        tr_cont="N",
        tr_cont_key="",
        mac_address="",
    )
    body: dict[Literal["CSPAQ22200InBlock1"], CSPAQ22200InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAQ22200",
    )
    """Pre-execution setup options (rate limit, retry behavior)."""


class CSPAQ22200OutBlock1(BaseModel):
    """CSPAQ22200OutBlock1 — minimal input echo-back block.

    Note: the ``MgmtBrnNo`` field is currently unused upstream and may be
    returned as an empty string.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Number of records returned. Always 1 for this echo block.",
        examples=[0, 1],
    )
    MgmtBrnNo: str = Field(
        default="",
        title="관리지점번호 (Managing branch number, unused)",
        description=(
            "Managing branch number. Currently unused upstream — typically "
            "returned as an empty string."
        ),
        examples=[""],
    )
    BalCreTp: str = Field(
        default="0",
        title="잔고생성구분 (Balance creation classification)",
        description="Echo of the input ``BalCreTp``.",
        examples=["0", "1"],
    )


class CSPAQ22200OutBlock2(BaseModel):
    """CSPAQ22200OutBlock2 — asset / credit-collateral snapshot block.

    Returns the cash-equity account snapshot with emphasis on the credit
    collateral side: orderable amounts, credit collateral posted (cash and
    substitute), credit-set guarantee, sub / original collateral totals,
    post-change collateral ratio, required and shortfall collateral
    amounts, and the sell-side collateralized loan.

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
    SubstOrdAbleAmt: int = Field(
        default=0,
        title="대용주문가능금액 (Substitute orderable amount)",
        description=(
            "Substitute-collateral amount available for placing buy orders. "
            "Currency: KRW."
        ),
        examples=[0, 2_000_000, 50_000_000],
    )
    SeOrdAbleAmt: int = Field(
        default=0,
        title="거래소금액 (Exchange amount)",
        description=(
            "Orderable amount applicable on the KRX main board. Currency: KRW."
        ),
        examples=[0, 5_000_000, 100_000_000],
    )
    KdqOrdAbleAmt: int = Field(
        default=0,
        title="코스닥금액 (KOSDAQ amount)",
        description=(
            "Orderable amount applicable on the KOSDAQ market. Currency: KRW."
        ),
        examples=[0, 4_500_000, 90_000_000],
    )
    CrdtPldgOrdAmt: int = Field(
        default=0,
        title="신용담보주문금액 (Credit-collateral order amount)",
        description=(
            "Order amount available against credit collateral postings. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
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
    CrdtOrdAbleAmt: int = Field(
        default=0,
        title="신용주문가능금액 (Credit orderable amount)",
        description=(
            "Orderable amount available under credit (margin loan) financing. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
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
    RcvblAmt: int = Field(
        default=0,
        title="미수금액 (Receivable / credit balance)",
        description=(
            "Outstanding 미수 (missed-payment / credit) amount owed by the "
            "account. Currency: KRW."
        ),
        examples=[0, 1_000_000],
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
    MloanAmt: int = Field(
        default=0,
        title="융자금액 (Margin loan amount)",
        description="Outstanding margin loan amount. Currency: KRW.",
        examples=[0, 5_000_000],
    )
    ChgAfPldgRat: float = Field(
        default=0.0,
        title="변경후담보비율 (Post-change collateral ratio)",
        description=(
            "Collateral ratio after the latest collateral adjustment, in "
            "percent. LS may serialize this value as a string; Pydantic "
            "auto-coerces to float."
        ),
        examples=[0.0, 140.0, 170.0],
    )
    RqrdPldgAmt: int = Field(
        default=0,
        title="소요담보금액 (Required collateral amount)",
        description=(
            "Collateral amount required to maintain the credit positions. "
            "Currency: KRW."
        ),
        examples=[0, 10_000_000],
    )
    PdlckAmt: int = Field(
        default=0,
        title="담보부족금액 (Collateral shortfall)",
        description=(
            "Collateral shortfall versus the required amount. 0 when "
            "sufficient collateral is posted. Currency: KRW."
        ),
        examples=[0, 500_000],
    )
    OrgPldgSumAmt: int = Field(
        default=0,
        title="원담보합계금액 (Original collateral total)",
        description=(
            "Total of original (primary) collateral postings. Currency: KRW."
        ),
        examples=[0, 50_000_000],
    )
    SubPldgSumAmt: int = Field(
        default=0,
        title="부담보합계금액 (Sub collateral total)",
        description=(
            "Total of sub-classification collateral postings. Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    CrdtPldgAmtMny: int = Field(
        default=0,
        title="신용담보금현금 (Credit collateral cash)",
        description=(
            "Cash component of credit collateral currently posted. "
            "Currency: KRW."
        ),
        examples=[0, 5_000_000],
    )
    CrdtPldgSubstAmt: int = Field(
        default=0,
        title="신용담보대용금액 (Credit collateral substitute)",
        description=(
            "Substitute (non-cash) component of credit collateral currently "
            "posted. Currency: KRW."
        ),
        examples=[0, 2_000_000],
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
    CslLoanAmtdt1: int = Field(
        default=0,
        title="매도대금담보대출금액 (Sell-proceed collateralized loan)",
        description=(
            "Loan amount collateralized by sell proceeds awaiting settlement. "
            "Currency: KRW."
        ),
        examples=[0, 3_000_000],
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


class CSPAQ22200Response(BaseModel):
    """CSPAQ22200 full API response envelope."""

    header: Optional[CSPAQ22200ResponseHeader] = None
    block1: Optional[CSPAQ22200OutBlock1] = Field(
        default=None,
        title="CSPAQ22200OutBlock1 (Minimal input echo-back)",
        description="Minimal echo-back. Branch number is currently unused upstream.",
    )
    block2: Optional[CSPAQ22200OutBlock2] = Field(
        default=None,
        title="CSPAQ22200OutBlock2 (Asset / credit-collateral snapshot)",
        description=(
            "Account-level asset snapshot with credit-collateral focus: "
            "orderable amounts, deposit ladder, margin, credit-collateral "
            "order amount, credit collateral cash / substitute, credit-set "
            "guarantee, original / sub collateral totals, post-change "
            "collateral ratio, required and shortfall collateral, daily "
            "settlement ladders, sell-proceed collateralized loan."
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
