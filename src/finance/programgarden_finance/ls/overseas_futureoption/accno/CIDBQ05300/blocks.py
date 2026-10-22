"""Pydantic models for LS Securities OpenAPI CIDBQ05300 (Overseas Futures Deposited Assets).

CIDBQ05300 returns per-currency deposited asset snapshots for overseas futures accounts,
including margin, P&L, and option value breakdown, plus a cross-currency aggregate summary.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, currency unit, and complete enum mappings are NOT declared
      in the source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - PnL fields (CustmLpnlAmt, AbrdFutsEvalPnlAmt, AbrdFutsLqdtPnlAmt, FutsDueNarrvLqdtPnlAmt)
      include positive, negative, and zero examples as required by plan policy.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ05300.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ05300RequestHeader(BlockRequestHeader):
    """CIDBQ05300 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ05300ResponseHeader(BlockResponseHeader):
    """CIDBQ05300 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ05300InBlock1(BaseModel):
    """CIDBQ05300InBlock1 — input block for overseas futures deposited assets query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS examples use 1.",
        examples=[1],
    )

    OvrsAcntTpCode: Literal["1"] = Field(
        default="1",
        title="Overseas account type code (해외계좌구분코드)",
        description="Overseas account type. '1' = consignment (위탁). Only '1' is documented.",
        examples=["1"],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description=(
            "FCM (Futures Commission Merchant) account number. "
            "Pass empty string when not applicable."
        ),
        examples=[""],
    )

    CrcyCode: Literal["ALL", "CAD", "CHF", "EUR", "GBP", "HKD", "JPY", "SGD", "USD"] = Field(
        default="",
        title="Currency code (통화코드)",
        description=(
            "Currency filter. 'ALL' = all currencies (전체). "
            "Other values: 'CAD' = Canadian dollar, 'CHF' = Swiss franc, 'EUR' = Euro, "
            "'GBP' = British pound, 'HKD' = Hong Kong dollar, 'JPY' = Japanese yen, "
            "'SGD' = Singapore dollar, 'USD' = U.S. dollar. "
            "From the example script: 'ALL'."
        ),
        examples=["ALL", "USD", "HKD", "JPY"],
    )


class CIDBQ05300Request(BaseModel):
    """CIDBQ05300 full request envelope (header + body + setup options)."""

    header: CIDBQ05300RequestHeader = Field(
        CIDBQ05300RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ05300",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ05300InBlock1"], CIDBQ05300InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ05300InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ05300"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ05300OutBlock1(BaseModel):
    """CIDBQ05300OutBlock1 — input echo block with account identity.

    LS echoes the request inputs plus the resolved account number and password.
    Per-currency details are in OutBlock2; the cross-currency aggregate is in OutBlock3.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )

    OvrsAcntTpCode: str = Field(
        default="",
        title="Overseas account type code (해외계좌구분코드)",
        description="Echoed overseas account type. '1' = consignment.",
        examples=["1"],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description="Echoed FCM account number. Empty when not applicable.",
        examples=[""],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number resolved from the session. Length not declared in available source.",
        examples=["12345678901"],
    )

    AcntPwd: str = Field(
        default="",
        title="Account password (계좌비밀번호)",
        description=(
            "Account password as echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )

    CrcyCode: str = Field(
        default="",
        title="Currency code (통화코드)",
        description="Echoed currency filter. 'ALL' = all currencies, or a specific currency code.",
        examples=["ALL", "USD"],
    )


class CIDBQ05300OutBlock2(BaseModel):
    """CIDBQ05300OutBlock2 — per-currency asset detail row (Occurs).

    One record per currency. Currency unit, decimal scale, and multiplier are not
    declared in the source available to this codebase — consume values as returned by LS.
    """

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for this record. Length not declared in available source.",
        examples=["12345678901"],
    )

    CrcyCode: str = Field(
        default="",
        title="Currency code (통화코드)",
        description="Currency code for this record.",
        examples=["USD", "HKD", "JPY"],
    )

    OvrsFutsDps: float = Field(
        default=0.0,
        title="Overseas futures deposit (해외선물예수금)",
        description=(
            "Deposit balance for overseas futures in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    AbrdFutsCsgnMgn: float = Field(
        default=0.0,
        title="Overseas futures consignment margin amount (해외선물위탁증거금액)",
        description=(
            "Required margin for consignment positions in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    OvrsFutsSplmMgn: float = Field(
        default=0.0,
        title="Overseas futures supplemental margin (해외선물추가증거금)",
        description=(
            "Supplemental (additional call) margin in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 1000.0],
    )

    CustmLpnlAmt: float = Field(
        default=0.0,
        title="Customer liquidation P&L amount (고객청산손익금액)",
        description=(
            "Realized P&L for the customer from liquidated positions in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures unrealized P&L amount (해외선물평가손익금액)",
        description=(
            "Unrealized (mark-to-market) P&L for overseas futures in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    AbrdFutsCmsnAmt: float = Field(
        default=0.0,
        title="Overseas futures commission amount (해외선물수수료금액)",
        description=(
            "Total commission for overseas futures in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[50.0, 0.0],
    )

    AbrdFutsEvalDpstgTotAmt: float = Field(
        default=0.0,
        title="Overseas futures evaluated total deposit amount (해외선물평가예탁총금액)",
        description=(
            "Total evaluated deposit amount including open position P&L in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    Xchrat: float = Field(
        default=0.0,
        title="Exchange rate (환율)",
        description=(
            "Exchange rate for this currency to the base currency. "
            "Scale not declared in available source — consume as returned by LS."
        ),
        examples=[1320.5, 1.0, 0.0],
    )

    FcurrRealMxchgAmt: float = Field(
        default=0.0,
        title="Foreign currency actual exchange amount (외화실환전금액)",
        description=(
            "Actual foreign currency amount after exchange conversion. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 5000.0],
    )

    AbrdFutsWthdwAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures withdrawable amount (해외선물인출가능금액)",
        description=(
            "Amount that can be withdrawn from the overseas futures account in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[3000.0, 0.0],
    )

    AbrdFutsOrdAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures orderable amount (해외선물주문가능금액)",
        description=(
            "Available funds for placing new overseas futures orders in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    FutsDueNarrvLqdtPnlAmt: float = Field(
        default=0.0,
        title="Futures pre-expiry liquidation P&L amount (선물만기미도래청산손익금액)",
        description=(
            "Realized P&L from positions liquidated before futures expiry in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[500.0, -200.0, 0.0],
    )

    FutsDueNarrvCmsn: float = Field(
        default=0.0,
        title="Futures pre-expiry commission (선물만기미도래수수료)",
        description=(
            "Commission for positions settled before futures expiry in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[10.0, 0.0],
    )

    AbrdFutsLqdtPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures liquidation P&L amount (해외선물청산손익금액)",
        description=(
            "Total realized P&L from liquidated overseas futures positions in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    OvrsFutsDueCmsn: float = Field(
        default=0.0,
        title="Overseas futures expiry commission (해외선물만기수수료)",
        description=(
            "Commission incurred at futures expiry in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 5.0],
    )

    OvrsFutsOptBuyAmt: float = Field(
        default=0.0,
        title="Overseas futures option buy amount (해외선물옵션매수금액)",
        description=(
            "Amount paid for buying overseas options in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 500.0],
    )

    OvrsFutsOptSellAmt: float = Field(
        default=0.0,
        title="Overseas futures option sell amount (해외선물옵션매도금액)",
        description=(
            "Amount received from selling overseas options in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 400.0],
    )

    OptBuyMktWrthAmt: float = Field(
        default=0.0,
        title="Option buy market value amount (옵션매수시장가치금액)",
        description=(
            "Market value of long option positions in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 600.0],
    )

    OptSellMktWrthAmt: float = Field(
        default=0.0,
        title="Option sell market value amount (옵션매도시장가치금액)",
        description=(
            "Market value of short option positions in this currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 380.0],
    )


class CIDBQ05300OutBlock3(BaseModel):
    """CIDBQ05300OutBlock3 — cross-currency aggregate summary block.

    A single record summarising totals across all queried currencies.
    Currency unit and decimal scale are not declared in available source —
    consume as returned by LS.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Record count for this aggregate block.",
        examples=[0, 1],
    )

    OvrsFutsDps: float = Field(
        default=0.0,
        title="Overseas futures deposit total (해외선물예수금)",
        description=(
            "Total deposit balance for overseas futures across all currencies. "
            "Decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    AbrdFutsLqdtPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures liquidation P&L amount total (해외선물청산손익금액)",
        description=(
            "Total realized P&L from liquidated overseas futures positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    FutsDueNarrvLqdtPnlAmt: float = Field(
        default=0.0,
        title="Futures pre-expiry liquidation P&L amount total (선물만기미도래청산손익금액)",
        description=(
            "Total realized P&L from positions liquidated before expiry. "
            "Decimal scale not declared in available source."
        ),
        examples=[500.0, -200.0, 0.0],
    )

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures unrealized P&L amount total (해외선물평가손익금액)",
        description=(
            "Total unrealized (mark-to-market) P&L for overseas futures. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    AbrdFutsEvalDpstgTotAmt: float = Field(
        default=0.0,
        title="Overseas futures evaluated total deposit amount (해외선물평가예탁총금액)",
        description=(
            "Total evaluated deposit amount across all currencies. "
            "Decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    CustmLpnlAmt: float = Field(
        default=0.0,
        title="Customer liquidation P&L amount total (고객청산손익금액)",
        description=(
            "Total realized P&L for the customer from liquidated positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    OvrsFutsDueCmsn: float = Field(
        default=0.0,
        title="Overseas futures expiry commission total (해외선물만기수수료)",
        description=(
            "Total commission incurred at futures expiry. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 5.0],
    )

    FcurrRealMxchgAmt: float = Field(
        default=0.0,
        title="Foreign currency actual exchange amount total (외화실환전금액)",
        description=(
            "Total actual foreign currency amount after exchange conversion. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 5000.0],
    )

    AbrdFutsCmsnAmt: float = Field(
        default=0.0,
        title="Overseas futures commission amount total (해외선물수수료금액)",
        description=(
            "Total commission for overseas futures across all currencies. "
            "Decimal scale not declared in available source."
        ),
        examples=[50.0, 0.0],
    )

    FutsDueNarrvCmsn: float = Field(
        default=0.0,
        title="Futures pre-expiry commission total (선물만기미도래수수료)",
        description=(
            "Total commission for positions settled before expiry. "
            "Decimal scale not declared in available source."
        ),
        examples=[10.0, 0.0],
    )

    AbrdFutsCsgnMgn: float = Field(
        default=0.0,
        title="Overseas futures consignment margin amount total (해외선물위탁증거금액)",
        description=(
            "Total required margin for consignment positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    OvrsFutsMaintMgn: float = Field(
        default=0.0,
        title="Overseas futures maintenance margin total (해외선물유지증거금)",
        description=(
            "Total maintenance margin level. "
            "Decimal scale not declared in available source."
        ),
        examples=[4000.0, 0.0],
    )

    OvrsFutsOptBuyAmt: float = Field(
        default=0.0,
        title="Overseas futures option buy amount total (해외선물옵션매수금액)",
        description=(
            "Total amount paid for buying overseas options. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 500.0],
    )

    OvrsFutsOptSellAmt: float = Field(
        default=0.0,
        title="Overseas futures option sell amount total (해외선물옵션매도금액)",
        description=(
            "Total amount received from selling overseas options. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 400.0],
    )

    CtlmtAmt: float = Field(
        default=0.0,
        title="Credit limit amount (신용한도금액)",
        description=(
            "Credit limit amount. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 100000.0],
    )

    OvrsFutsSplmMgn: float = Field(
        default=0.0,
        title="Overseas futures supplemental margin total (해외선물추가증거금)",
        description=(
            "Total supplemental (additional call) margin. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 1000.0],
    )

    MgnclRat: float = Field(
        default=0.0,
        title="Margin call rate (마진콜율)",
        description=(
            "Margin call ratio. Scale not declared in available source — "
            "consume as returned by LS."
        ),
        examples=[0.0, 75.5, 110.0],
    )

    AbrdFutsOrdAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures orderable amount total (해외선물주문가능금액)",
        description=(
            "Total available funds for placing new overseas futures orders. "
            "Decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    AbrdFutsWthdwAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures withdrawable amount total (해외선물인출가능금액)",
        description=(
            "Total amount that can be withdrawn from the overseas futures account. "
            "Decimal scale not declared in available source."
        ),
        examples=[3000.0, 0.0],
    )

    OptBuyMktWrthAmt: float = Field(
        default=0.0,
        title="Option buy market value amount total (옵션매수시장가치금액)",
        description=(
            "Total market value of long option positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 600.0],
    )

    OptSellMktWrthAmt: float = Field(
        default=0.0,
        title="Option sell market value amount total (옵션매도시장가치금액)",
        description=(
            "Total market value of short option positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 380.0],
    )

    OvrsOptSettAmt: float = Field(
        default=0.0,
        title="Overseas option settlement amount total (해외옵션결제금액)",
        description=(
            "Total settlement amount for overseas options. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 250.0],
    )

    OvrsOptBalEvalAmt: float = Field(
        default=0.0,
        title="Overseas option balance evaluation amount total (해외옵션잔고평가금액)",
        description=(
            "Total evaluated balance amount for overseas option positions. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 750.0],
    )


class CIDBQ05300Response(BaseModel):
    """CIDBQ05300 full response envelope."""

    header: Optional[CIDBQ05300ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ05300OutBlock1] = Field(
        None,
        title="First output block — account identity echo (첫 번째 출력 블록)",
        description="Input echo block with resolved account number.",
    )
    block2: List[CIDBQ05300OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-currency asset detail rows (두 번째 출력 블록 리스트)",
        description="Per-currency deposited asset detail rows.",
    )
    block3: Optional[CIDBQ05300OutBlock3] = Field(
        None,
        title="Third output block — cross-currency aggregate (세 번째 출력 블록)",
        description="Cross-currency aggregate summary block.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답메시지)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="Error message (오류 메시지)",
        description="Error message when an exception or HTTP error occurred. None on success.",
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        """Raw underlying response object (for debugging)."""
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
