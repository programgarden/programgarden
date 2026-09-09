"""LS Securities OpenAPI CIDBQ03000 overseas futures deposit/balance models.

The response describes account deposit/balance state for ``TrdDt`` and may
contain individual currency rows and an aggregate target such as ``TOT(USD)``.

Metadata sources:
    - The LS request/response table supplied by the user on 2026-09-09 defines
      field labels, string lengths, numeric lengths/scales and account types.
      These describe the wire format; the model adds no new validation limits.
    - The supplied response example contains ``TOT(USD)`` and ``rsp_cd="00136"``.
    - The repository example uses a blank ``TrdDt``. The supplied table does not
      define that convention or the available historical query period.
    - Date-specific responses do not establish intraday reset boundaries or
      arithmetic relationships between the P&L and commission fields.

Keep the returned currency target and snapshot fields separate. Do not treat
snapshot components as independent additions to reported equity without a
confirmed accounting identity. The labels/example do not establish a formula
between liquidation P&L, final settlement P&L, valuation P&L and commission.
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
            "String length 1 in the supplied request table."
        ),
        examples=["1", "2"],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description=(
            "Trading date, string length 8, YYYYMMDD. "
            "The repository example passes an empty string; the supplied table does not define this convention."
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
        description="Echoed record count. Numeric length 5 in the supplied response table.",
        examples=[0, 1],
    )

    AcntTpCode: str = Field(
        default="",
        title="Account type code (계좌구분코드)",
        description="Echoed account type, string length 1. '1' = consignment, '2' = brokerage.",
        examples=["1", "2"],
    )

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for the query, string length 20.",
        examples=["12345678901"],
    )

    AcntPwd: str = Field(
        default="",
        title="Account password (계좌비밀번호)",
        description=(
            "Account password as echoed by LS, string length 8. Treat as sensitive; avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description="Echoed trading date, string length 8, YYYYMMDD.",
        examples=["", "20260117"],
    )


class CIDBQ03000OutBlock2(BaseModel):
    """CIDBQ03000OutBlock2 — per-currency deposit/balance detail row (Occurs).

    The supplied example returns a list containing a ``TOT(USD)`` aggregate row.
    Keep aggregate and individual currency rows separate; summing them can double
    count the same balance. Numeric lengths/scales describe the wire format,
    not conversion rates, arithmetic identities or accumulation/reset periods.
    """

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for this record, string length 20.",
        examples=["12345678901"],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description="Trading date for this balance record, string length 8, YYYYMMDD.",
        examples=["20260117", ""],
    )

    CrcyObjCode: str = Field(
        default="",
        title="Currency target code (통화대상코드)",
        description=(
            "Currency target code, string length 12. The supplied example uses the "
            "aggregate target 'TOT(USD)'. Preserve the target as returned; the "
            "table does not give a complete enum or conversion rule."
        ),
        examples=["TOT(USD)", "USD", "HKD"],
    )

    OvrsFutsDps: float = Field(
        default=0.0,
        title="Overseas futures deposit (해외선물예수금)",
        description=(
            "Deposit balance for overseas futures. "
            "LS numeric length/scale 23.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[10000.0, 0.0],
    )

    CustmMnyioAmt: float = Field(
        default=0.0,
        title="Customer deposit/withdrawal amount (고객입출금금액)",
        description=(
            "Net customer deposit/withdrawal amount. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[5000.0, -2000.0, 0.0],
    )

    AbrdFutsLqdtPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures liquidation P&L amount (해외선물청산손익금액)",
        description=(
            "Realized P&L from liquidated overseas futures positions. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    AbrdFutsCmsnAmt: float = Field(
        default=0.0,
        title="Overseas futures commission amount (해외선물수수료금액)",
        description=(
            "Total commission for overseas futures. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[50.0, 0.0],
    )

    PrexchDps: float = Field(
        default=0.0,
        title="Pre-exchange deposit (가환전예수금)",
        description=(
            "LS-reported deposit amount (가환전예수금). "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[0.0, 8000.0],
    )

    EvalAssetAmt: float = Field(
        default=0.0,
        title="Evaluated asset amount (평가자산금액)",
        description=(
            "Total evaluated asset amount including open positions. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[10000.0, 0.0],
    )

    AbrdFutsCsgnMgn: float = Field(
        default=0.0,
        title="Overseas futures consignment margin amount (해외선물위탁증거금액)",
        description=(
            "Required margin for overseas futures consignment positions. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[5000.0, 0.0],
    )

    AbrdFutsAddMgn: float = Field(
        default=0.0,
        title="Overseas futures additional margin amount (해외선물추가증거금액)",
        description=(
            "Additional margin required (variation/call margin). "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[0.0, 1000.0],
    )

    AbrdFutsWthdwAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures withdrawable amount (해외선물인출가능금액)",
        description=(
            "Amount that can be withdrawn from the overseas futures account. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[3000.0, 0.0],
    )

    AbrdFutsOrdAbleAmt: float = Field(
        default=0.0,
        title="Overseas futures orderable amount (해외선물주문가능금액)",
        description=(
            "Available funds for placing new overseas futures orders. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[5000.0, 0.0],
    )

    AbrdFutsEvalPnlAmt: float = Field(
        default=0.0,
        title="Overseas futures unrealized P&L amount (해외선물평가손익금액)",
        description=(
            "Unrealized (mark-to-market) P&L for overseas futures positions. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    LastSettPnlAmt: float = Field(
        default=0.0,
        title="Final settlement P&L amount (최종결제손익금액)",
        description=(
            "Final settlement P&L amount as reported by LS. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[500.0, -200.0, 0.0],
    )

    OvrsOptSettAmt: float = Field(
        default=0.0,
        title="Overseas option settlement amount (해외옵션결제금액)",
        description=(
            "Settlement amount for overseas options. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
        ),
        examples=[0.0, 250.0],
    )

    OvrsOptBalEvalAmt: float = Field(
        default=0.0,
        title="Overseas option balance evaluation amount (해외옵션잔고평가금액)",
        description=(
            "Evaluated balance amount for overseas option positions. "
            "LS numeric length/scale 19.2 (two decimal places). Currency target: CrcyObjCode."
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
        description="Deposit/balance rows, including aggregate currency targets when returned.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답코드)",
        description="LS response code, preserved verbatim. The supplied completed-query example uses '00136'.",
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
