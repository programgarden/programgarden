"""Pydantic models for LS Securities OpenAPI CIDBQ01500 (Overseas Futures Open Position Balance).

CIDBQ01500 returns the outstanding (open) position balance for overseas futures/options,
including per-position details (symbol, side, quantity, P&L, margin) across currencies.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, currency unit, and complete enum mappings are NOT declared
      in the source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - PnL fields (LpnlAmt, FutsDueBfLpnlAmt, AbrdFutsEvalPnlAmt) include positive,
      negative, and zero examples as required by plan policy.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ01500.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01500RequestHeader(BlockRequestHeader):
    """CIDBQ01500 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ01500ResponseHeader(BlockResponseHeader):
    """CIDBQ01500 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ01500InBlock1(BaseModel):
    """CIDBQ01500InBlock1 — input block for overseas futures open position balance query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS examples use 1.",
        examples=[1],
    )

    AcntTpCode: str = Field(
        default="1",
        title="Account type code (계좌구분코드)",
        description="Account type. '1' = consignment (위탁). Enum mapping not fully declared in available source.",
        examples=["1"],
    )

    QryDt: str = Field(
        default="",
        title="Query date (조회일자)",
        description=(
            "Query date in YYYYMMDD format. From the example script: '20260117'. "
            "Pass empty string for the current trading date."
        ),
        examples=["20260117", "20260101", ""],
    )

    BalTpCode: str = Field(
        default="1",
        title="Balance type code (잔고구분코드)",
        description="Balance aggregation type. '1' = aggregated (합산), '2' = per-entry (건별).",
        examples=["1", "2"],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description=(
            "FCM (Futures Commission Merchant) account number. "
            "Pass empty string when not applicable. Length not declared in available source."
        ),
        examples=[""],
    )


class CIDBQ01500Request(BaseModel):
    """CIDBQ01500 full request envelope (header + body + setup options)."""

    header: CIDBQ01500RequestHeader = Field(
        CIDBQ01500RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ01500",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ01500InBlock1"], CIDBQ01500InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ01500InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ01500"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ01500OutBlock1(BaseModel):
    """CIDBQ01500OutBlock1 — input echo block with account identity.

    LS echoes the request inputs plus the resolved account number and password.
    The actual position detail rows are in OutBlock2.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )

    AcntTpCode: str = Field(
        default="",
        title="Account type code (계좌구분코드)",
        description="Echoed account type. '1' = consignment (위탁).",
        examples=["1"],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for the query. Length not declared in available source.",
        examples=["12345678901"],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description="Echoed FCM account number. Empty when not applicable.",
        examples=[""],
    )

    Pwd: str = Field(
        default="",
        title="Account password (비밀번호)",
        description=(
            "Account password as echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )

    QryDt: str = Field(
        default="",
        title="Query date (조회일자)",
        description="Echoed query date in YYYYMMDD format.",
        examples=["20260117", ""],
    )

    BalTpCode: str = Field(
        default="",
        title="Balance type code (잔고구분코드)",
        description="Echoed balance type. '1' = aggregated, '2' = per-entry.",
        examples=["1", "2"],
    )


class CIDBQ01500OutBlock2(BaseModel):
    """CIDBQ01500OutBlock2 — per-position open balance detail row (Occurs).

    One record per open position (or per aggregated position when BalTpCode='1').
    Currency unit, decimal scale, and multiplier are not declared in the source
    available to this codebase — consume values as returned by LS.
    """

    BaseDt: str = Field(
        default="",
        title="Base date (기준일자)",
        description="Base date for the position record in YYYYMMDD format.",
        examples=["20260117", "20260101"],
    )

    Dps: float = Field(
        default=0.0,
        title="Deposit (예수금)",
        description=(
            "Deposit / cash balance. Currency and decimal scale not declared in available source. "
            "Consume as returned by LS."
        ),
        examples=[10000.0, 0.0],
    )

    LpnlAmt: float = Field(
        default=0.0,
        title="Liquidation P&L amount (청산손익금액)",
        description=(
            "Realized P&L from liquidated positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    FutsDueBfLpnlAmt: float = Field(
        default=0.0,
        title="Pre-expiry liquidation P&L amount (선물만기전청산손익금액)",
        description=(
            "Realized P&L from positions liquidated before futures expiry. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[500.0, -200.0, 0.0],
    )

    FutsDueBfCmsn: float = Field(
        default=0.0,
        title="Pre-expiry commission (선물만기전수수료)",
        description=(
            "Commission incurred for positions settled before futures expiry. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[10.0, 0.0],
    )

    CsgnMgn: float = Field(
        default=0.0,
        title="Consignment margin amount (위탁증거금액)",
        description=(
            "Required margin for consignment positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    MaintMgn: float = Field(
        default=0.0,
        title="Maintenance margin (유지증거금)",
        description=(
            "Maintenance margin level. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[4000.0, 0.0],
    )

    CtlmtAmt: float = Field(
        default=0.0,
        title="Credit limit amount (신용한도금액)",
        description=(
            "Credit limit amount. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 100000.0],
    )

    AddMgn: float = Field(
        default=0.0,
        title="Additional margin amount (추가증거금액)",
        description=(
            "Additional (variation/call) margin required. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 1000.0],
    )

    MgnclRat: float = Field(
        default=0.0,
        title="Margin call rate (마진콜율)",
        description=(
            "Margin call ratio. Scale and unit not declared in available source — "
            "consume as returned by LS."
        ),
        examples=[0.0, 75.5, 110.0],
    )

    OrdAbleAmt: float = Field(
        default=0.0,
        title="Orderable amount (주문가능금액)",
        description=(
            "Available funds for placing new orders. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    WthdwAbleAmt: float = Field(
        default=0.0,
        title="Withdrawable amount (인출가능금액)",
        description=(
            "Amount that can be withdrawn from the account. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[3000.0, 0.0],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for this position record. Length not declared in available source.",
        examples=["12345678901"],
    )

    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Instrument code for this open position.",
        examples=["ADM23", "ESM26", "NQU26"],
    )

    IsuNm: str = Field(
        default="",
        title="Issue name (종목명)",
        description="Display name of the instrument.",
        examples=["E-MINI S&P500", "GOLD FUTURES"],
    )

    CrcyCodeVal: str = Field(
        default="",
        title="Currency code value (통화코드값)",
        description="Currency code for this position. Enum not fully declared in available source.",
        examples=["USD", "HKD"],
    )

    OvrsDrvtPrdtCode: str = Field(
        default="",
        title="Overseas derivative product code (해외파생상품코드)",
        description=(
            "Product type code for the overseas derivative. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "F", "O"],
    )

    OvrsDrvtOptTpCode: str = Field(
        default="",
        title="Overseas derivative option type code (해외파생옵션구분코드)",
        description=(
            "Option type classification. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "C", "P"],
    )

    DueDt: str = Field(
        default="",
        title="Expiry date (만기일자)",
        description="Instrument expiry date in YYYYMMDD format.",
        examples=["20260321", "20260620", ""],
    )

    OvrsDrvtXrcPrc: float = Field(
        default=0.0,
        title="Overseas derivative exercise price (해외파생행사가격)",
        description=(
            "Strike / exercise price for option instruments. "
            "0 for futures. Decimal scale not declared in available source."
        ),
        examples=[0.0, 5000.0, 4800.0],
    )

    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Position direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )

    CmnCodeNm: str = Field(
        default="",
        title="Common code name (공통코드명)",
        description="Common classification name as returned by LS.",
        examples=["", "선물"],
    )

    TpCodeNm: str = Field(
        default="",
        title="Type code name (구분코드명)",
        description="Type classification name as returned by LS.",
        examples=["", "신규"],
    )

    BalQty: float = Field(
        default=0.0,
        title="Balance quantity (잔고수량)",
        description="Open position quantity (contracts). Scale not declared in available source.",
        examples=[1.0, 5.0, 0.0],
    )

    PchsPrc: float = Field(
        default=0.0,
        title="Purchase price (매입가격)",
        description=(
            "Average purchase (entry) price for the open position. "
            "Decimal scale not declared in available source."
        ),
        examples=[4500.25, 1900.0, 0.0],
    )

    OvrsDrvtNowPrc: float = Field(
        default=0.0,
        title="Overseas derivative current price (해외파생현재가)",
        description=(
            "Current market price of the instrument. "
            "Decimal scale not declared in available source."
        ),
        examples=[4550.0, 1920.5, 0.0],
    )

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures unrealized P&L amount (해외선물평가손익금액)",
        description=(
            "Unrealized (mark-to-market) P&L for the open position. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    CsgnCmsn: float = Field(
        default=0.0,
        title="Consignment commission (위탁수수료)",
        description=(
            "Commission charged for the consignment. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5.0, 0.0],
    )

    PosNo: str = Field(
        default="",
        title="Position number (포지션번호)",
        description="LS-assigned position identifier. Length not declared in available source.",
        examples=["", "1", "00001"],
    )

    EufOneCmsnAmt: float = Field(
        default=0.0,
        title="Exchange fee 1 commission amount (거래소비용1수수료금액)",
        description=(
            "Exchange cost 1 fee amount. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 1.25],
    )

    EufTwoCmsnAmt: float = Field(
        default=0.0,
        title="Exchange fee 2 commission amount (거래소비용2수수료금액)",
        description=(
            "Exchange cost 2 fee amount. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.75],
    )


class CIDBQ01500Response(BaseModel):
    """CIDBQ01500 full response envelope."""

    header: Optional[CIDBQ01500ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ01500OutBlock1] = Field(
        None,
        title="First output block — input echo (첫 번째 출력 블록)",
        description="Input echo block with resolved account number.",
    )
    block2: List[CIDBQ01500OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-position detail rows (두 번째 출력 블록 리스트)",
        description="Per-position open balance detail rows. Ordering follows BalTpCode setting.",
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
