"""Pydantic models for LS Securities OpenAPI CIDEQ00800 (Overseas Futures Daily Open Position Balance).

CIDEQ00800 returns the open (outstanding) position balance for overseas futures/options
on a specified trading date, including position details, P&L, and monetary evaluations.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, currency unit, and complete enum mappings are NOT declared
      in the source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - PnL fields (AbrdFutsEvalPnlAmt, FcurrEvalPnlAmt) include positive, negative, and zero
      examples as required by plan policy.
    - No example script is available for this TR. All examples are illustrative safe placeholders
      consistent with the field semantics described in the LS Korean source comments.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDEQ00800RequestHeader(BlockRequestHeader):
    """CIDEQ00800 request header. Inherits the standard LS request header schema."""
    pass


class CIDEQ00800ResponseHeader(BlockResponseHeader):
    """CIDEQ00800 response header. Inherits the standard LS response header schema."""
    pass


class CIDEQ00800InBlock1(BaseModel):
    """CIDEQ00800InBlock1 — input block for overseas futures daily open position balance query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS source comment uses 1.",
        examples=[1],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description=(
            "Trading date in YYYYMMDD format for the position balance query. "
            "Pass empty string for the current trading date. "
            "Length not declared in available source."
        ),
        examples=["", "20260117", "20260101"],
    )


class CIDEQ00800Request(BaseModel):
    """CIDEQ00800 full request envelope (header + body + setup options)."""

    header: CIDEQ00800RequestHeader = Field(
        CIDEQ00800RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDEQ00800",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDEQ00800InBlock1"], CIDEQ00800InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDEQ00800InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDEQ00800"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDEQ00800OutBlock1(BaseModel):
    """CIDEQ00800OutBlock1 — input echo block with account identity.

    LS echoes the request inputs plus the resolved account number and password.
    The per-position detail rows are in OutBlock2.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Echoed record count from the request.",
        examples=[0, 1],
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


class CIDEQ00800OutBlock2(BaseModel):
    """CIDEQ00800OutBlock2 — per-position daily open balance detail row (Occurs).

    One record per open position for the queried trading date. Currency unit,
    decimal scale, and multiplier are not declared in the source available to
    this codebase — consume values as returned by LS.
    """

    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number for this position record. Length not declared in available source.",
        examples=["12345678901"],
    )

    TrdDt: str = Field(
        default="",
        title="Trading date (거래일자)",
        description="Trading date for this position record in YYYYMMDD format.",
        examples=["20260117", "20260101"],
    )

    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Instrument code for this open position.",
        examples=["ESM26", "NQU26", "CLN26"],
    )

    BnsTpNm: str = Field(
        default="",
        title="Buy/sell type name (매매구분명)",
        description="Display name of the position direction (long / short).",
        examples=["매수", "매도"],
    )

    BalQty: float = Field(
        default=0.0,
        title="Balance quantity (잔고수량)",
        description=(
            "Open position quantity (contracts). "
            "Decimal scale not declared in available source."
        ),
        examples=[1.0, 5.0, 0.0],
    )

    LqdtAbleQty: float = Field(
        default=0.0,
        title="Liquidatable quantity (청산가능수량)",
        description=(
            "Quantity that can be liquidated. "
            "Decimal scale not declared in available source."
        ),
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
            "Unrealized (mark-to-market) P&L for this open position. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )

    CustmBalAmt: float = Field(
        default=0.0,
        title="Customer balance amount (고객잔고금액)",
        description=(
            "Customer balance amount for this position. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
    )

    FcurrEvalAmt: float = Field(
        default=0.0,
        title="Foreign currency evaluation amount (외화평가금액)",
        description=(
            "Foreign currency evaluated amount for this position. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[10000.0, 0.0],
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
        description="Currency code for this position.",
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

    DueDt: str = Field(
        default="",
        title="Expiry date (만기일자)",
        description="Instrument expiry date in YYYYMMDD format.",
        examples=["20260321", "20260620", ""],
    )

    PrcntrAmt: float = Field(
        default=0.0,
        title="Per-contract amount (계약당금액)",
        description=(
            "Amount per contract. "
            "Currency, decimal scale, and multiplier not declared in available source — "
            "consume as returned by LS."
        ),
        examples=[0.0, 50.0, 500.0],
    )

    FcurrEvalPnlAmt: float = Field(
        default=0.0,
        title="Foreign currency evaluation P&L amount (외화평가손익금액)",
        description=(
            "Unrealized P&L in foreign currency for this position. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1234.56, -789.01, 0.0],
    )


class CIDEQ00800Response(BaseModel):
    """CIDEQ00800 full response envelope."""

    header: Optional[CIDEQ00800ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDEQ00800OutBlock1] = Field(
        None,
        title="First output block — account identity echo (첫 번째 출력 블록)",
        description="Input echo block with resolved account number.",
    )
    block2: List[CIDEQ00800OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-position open balance rows (두 번째 출력 블록 리스트)",
        description="Per-position daily open balance detail rows.",
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
