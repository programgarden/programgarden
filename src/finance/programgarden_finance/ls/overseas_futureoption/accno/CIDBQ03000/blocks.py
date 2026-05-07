"""Pydantic models for LS Securities OpenAPI CIDBQ03000 (Overseas Futures Deposit/Balance Status).

CIDBQ03000 returns a per-currency snapshot of the overseas futures account's deposit,
margin, P&L, and orderable/withdrawable amounts for a given trading date.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, currency unit, and complete enum mappings are NOT declared
      in the source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - PnL fields (AbrdFutsLqdtPnlAmt, AbrdFutsEvalPnlAmt, LastSettPnlAmt) include positive,
      negative, and zero examples as required by plan policy.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ03000.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ03000RequestHeader(BlockRequestHeader):
    """CIDBQ03000 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ03000ResponseHeader(BlockResponseHeader):
    """CIDBQ03000 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ03000InBlock1(BaseModel):
    """CIDBQ03000InBlock1 — input block for overseas futures deposit/balance status query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS examples use 1.",
        examples=[1],
    )

    AcntTpCode: str = Field(
        default="",
        title="Account type code (계좌구분코드)",
        description=(
            "'1' = consignment account (위탁계좌), '2' = brokerage account (중개계좌). "
            "From the example script: '1'."
        ),
        examples=["1", "2"],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description=(
            "Trading date in YYYYMMDD format. Pass empty string for the current trading date. "
            "From the example script: empty string."
        ),
        examples=["", "20260117"],
    )


class CIDBQ03000Request(BaseModel):
    """CIDBQ03000 full request envelope (header + body + setup options)."""

    header: CIDBQ03000RequestHeader = Field(
        CIDBQ03000RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ03000",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ03000InBlock1"], CIDBQ03000InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ03000InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ03000"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ03000OutBlock1(BaseModel):
    """CIDBQ03000OutBlock1 — input echo block with account identity.

    LS echoes the request inputs plus resolved account number and password.
    The per-currency balance details are in OutBlock2.
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
        description="Echoed account type. '1' = consignment, '2' = brokerage.",
        examples=["1", "2"],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for the query. Length not declared in available source.",
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

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description="Echoed trading date in YYYYMMDD format.",
        examples=["", "20260117"],
    )


class CIDBQ03000OutBlock2(BaseModel):
    """CIDBQ03000OutBlock2 — per-currency deposit/balance detail row (Occurs).

    One record per currency. Currency unit, decimal scale, and multiplier are not
    declared in the source available to this codebase — consume values as returned by LS.
    """

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for this record. Length not declared in available source.",
        examples=["12345678901"],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description="Trading date for this balance record in YYYYMMDD format.",
        examples=["20260117", ""],
    )

    CrcyObjCode: str = Field(
        default="",
        title="Currency target code (통화대상코드)",
        description=(
            "Currency code for this record. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["USD", "HKD"],
    )

    OvrsFutsDps: float = Field(
        default=0.0,
        title="Overseas futures deposit (해외선물예수금)",
        description=(
            "Deposit balance for overseas futures. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    CustmMnyioAmt: float = Field(
        default=0.0,
        title="Customer deposit/withdrawal amount (고객입출금금액)",
        description=(
            "Net customer deposit/withdrawal amount. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5000.0, -2000.0, 0.0],
    )

    AbrdFutsLqdtPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures liquidation P&L amount (해외선물청산손익금액)",
        description=(
            "Realized P&L from liquidated overseas futures positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    AbrdFutsCmsnAmt: float = Field(
        default=0.0,
        title="Overseas futures commission amount (해외선물수수료금액)",
        description=(
            "Total commission for overseas futures. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[50.0, 0.0],
    )

    PrexchDps: float = Field(
        default=0.0,
        title="Pre-exchange deposit (가환전예수금)",
        description=(
            "Pre-exchange (before FX conversion) deposit amount. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 8000.0],
    )

    EvalAssetAmt: float = Field(
        default=0.0,
        title="Evaluated asset amount (평가자산금액)",
        description=(
            "Total evaluated asset amount including open positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    AbrdFutsCsgnMgn: float = Field(
        default=0.0,
        title="Overseas futures consignment margin amount (해외선물위탁증거금액)",
        description=(
            "Required margin for overseas futures consignment positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    AbrdFutsAddMgn: float = Field(
        default=0.0,
        title="Overseas futures additional margin amount (해외선물추가증거금액)",
        description=(
            "Additional margin required (variation/call margin). "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 1000.0],
    )

    AbrdFutsWthdwAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures withdrawable amount (해외선물인출가능금액)",
        description=(
            "Amount that can be withdrawn from the overseas futures account. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[3000.0, 0.0],
    )

    AbrdFutsOrdAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures orderable amount (해외선물주문가능금액)",
        description=(
            "Available funds for placing new overseas futures orders. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5000.0, 0.0],
    )

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures unrealized P&L amount (해외선물평가손익금액)",
        description=(
            "Unrealized (mark-to-market) P&L for overseas futures positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    LastSettPnlAmt: float = Field(
        default=0.0,
        title="Last settlement P&L amount (최종결제손익금액)",
        description=(
            "P&L from the last daily settlement. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[500.0, -200.0, 0.0],
    )

    OvrsOptSettAmt: float = Field(
        default=0.0,
        title="Overseas option settlement amount (해외옵션결제금액)",
        description=(
            "Settlement amount for overseas options. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 250.0],
    )

    OvrsOptBalEvalAmt: float = Field(
        default=0.0,
        title="Overseas option balance evaluation amount (해외옵션잔고평가금액)",
        description=(
            "Evaluated balance amount for overseas option positions. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 750.0],
    )


class CIDBQ03000Response(BaseModel):
    """CIDBQ03000 full response envelope."""

    header: Optional[CIDBQ03000ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ03000OutBlock1] = Field(
        None,
        title="First output block — account identity echo (첫 번째 출력 블록)",
        description="Input echo block with resolved account number.",
    )
    block2: List[CIDBQ03000OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-currency balance rows (두 번째 출력 블록 리스트)",
        description="Per-currency deposit/balance detail rows.",
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
