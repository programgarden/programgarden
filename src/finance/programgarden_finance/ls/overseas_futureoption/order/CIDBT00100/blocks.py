"""Pydantic models for LS Securities OpenAPI CIDBT00100 (Overseas Futures New Order).

CIDBT00100 submits a NEW (신규) overseas futures order. ``FutsOrdTpCode`` is fixed
at '1' (신규). Both market and limit orders are supported via
``AbrdFutsOrdPtnCode`` ('1' = market, '2' = limit). The response contains an
input-echo block (OutBlock1) and an order acknowledgment block (OutBlock2)
carrying the LS-assigned overseas futures order number.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Enum codes (FutsOrdTpCode, BnsTpCode, AbrdFutsOrdPtnCode) are documented
      verbatim from the Korean source docstring.
    - Decimal scale, currency unit, contract multiplier, and tick-value
      semantics for overseas futures are NOT declared in the source available
      to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS" or "not declared in available source".
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBT00100.py``
      (ADZ25 1-lot test) plus safe placeholder values. Account number
      placeholder "12345678901" is always used — never real accounts.

SAFETY: This is a live order-submission TR. Examples are illustrative only and
must NOT be used as-is to submit real orders.
"""

from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBT00100RequestHeader(BlockRequestHeader):
    """CIDBT00100 request header. Inherits the standard LS request header schema."""
    pass


class CIDBT00100ResponseHeader(BlockResponseHeader):
    """CIDBT00100 response header. Inherits the standard LS response header schema."""
    pass


class CIDBT00100InBlock1(BaseModel):
    """CIDBT00100InBlock1 — input block for an overseas futures new order.

    ``FutsOrdTpCode`` is always '1' (신규). For market orders set
    ``AbrdFutsOrdPtnCode`` to '1' and pass ``OvrsDrvtOrdPrc=0``; for limit
    orders set '2' and supply the limit price.
    """

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records sent in this request. LS examples always use 1.",
        examples=[1],
    )
    OrdDt: str = Field(
        ...,
        title="Order date (주문일자)",
        description="Order date in YYYYMMDD format. Example script uses today's date via strftime.",
        examples=["20260507", "20260601"],
    )
    IsuCodeVal: str = Field(
        ...,
        title="Issue code value (종목코드값)",
        description=(
            "LS instrument code for the overseas futures contract being ordered. "
            "Example script uses 'ADZ25'. Length not declared in available source."
        ),
        examples=["ADZ25", "ESM26", "NQU26"],
    )
    FutsOrdTpCode: Literal["1"] = Field(
        ...,
        title="Futures order type code (선물주문구분코드)",
        description="Futures order type. Always '1' = new order (신규) for CIDBT00100.",
        examples=["1"],
    )
    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )
    AbrdFutsOrdPtnCode: Literal["1", "2"] = Field(
        ...,
        title="Overseas futures order pattern code (해외선물주문유형코드)",
        description=(
            "Order pattern. '1' = market order (시장가), '2' = limit order (지정가). "
            "When '1', set OvrsDrvtOrdPrc to 0."
        ),
        examples=["1", "2"],
    )
    CrcyCode: str = Field(
        "",
        title="Currency code (통화코드)",
        description=(
            "Currency code for the order. Empty string is accepted by LS — "
            "use empty unless required by a specific instrument. Enum mapping not "
            "declared in available source — consume as returned by LS."
        ),
        examples=["", "USD"],
    )
    OvrsDrvtOrdPrc: float = Field(
        ...,
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Limit order price in the instrument's quote currency. Pass 0 when "
            "AbrdFutsOrdPtnCode is '1' (market). Decimal scale not declared in "
            "available source — consume as returned by LS."
        ),
        examples=[0.64935, 0.0, 4500.25],
    )
    CndiOrdPrc: float = Field(
        ...,
        title="Conditional order price (조건주문가격)",
        description=(
            "Condition / trigger price. Example script uses 0. Decimal scale and "
            "trigger semantics not declared in available source — consume as "
            "returned by LS."
        ),
        examples=[0, 0.0],
    )
    OrdQty: int = Field(
        ...,
        title="Order quantity (주문수량)",
        description="Order quantity in contracts. Example script uses 1.",
        examples=[1, 5],
    )
    PrdtCode: str = Field(
        "000000",
        title="Product code (상품코드)",
        description=(
            "Product code. Defaults to '000000'; LS source also notes SPACE is "
            "accepted. Code values not declared in available source — consume "
            "as returned by LS."
        ),
        examples=["000000", " "],
    )
    DueYymm: str = Field(
        "000000",
        title="Due year/month (만기년월)",
        description=(
            "Contract expiry year/month. Defaults to '000000'. Format hinted as "
            "YYMM in the source docstring; full length / zero-pad rules not "
            "declared in available source — consume as returned by LS."
        ),
        examples=["000000", "2512"],
    )
    ExchCode: str = Field(
        "",
        title="Exchange code (거래소코드)",
        description=(
            "Exchange code. Empty string is accepted by LS. Enum mapping not "
            "declared in available source — consume as returned by LS."
        ),
        examples=["", "CME"],
    )


class CIDBT00100Request(BaseModel):
    """CIDBT00100 full request envelope (header + body + setup options)."""

    header: CIDBT00100RequestHeader = Field(
        CIDBT00100RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBT00100",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, CIDBT00100InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBT00100InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=5,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBT00100"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBT00100OutBlock1(BaseModel):
    """CIDBT00100OutBlock1 — input echo block for the new order request.

    LS echoes the InBlock1 inputs back in OutBlock1. Additional server-side
    fields ``BrnCode``, ``AcntNo``, and ``Pwd`` identify the originating
    branch / account.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Echoed record count.",
        examples=[0, 1],
    )
    OrdDt: str = Field(
        default="",
        title="Order date (주문일자)",
        description="Echoed order date in YYYYMMDD format.",
        examples=["", "20260507"],
    )
    BrnCode: str = Field(
        default="",
        title="Branch code (지점코드)",
        description="Branch code associated with the account. Length not declared in available source.",
        examples=["", "001"],
    )
    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number that placed the order. Length not declared in available source.",
        examples=["", "12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="Password (비밀번호)",
        description=(
            "Account password echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )
    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Echoed instrument code for the ordered overseas futures contract.",
        examples=["", "ADZ25", "ESM26"],
    )
    FutsOrdTpCode: str = Field(
        default="",
        title="Futures order type code (선물주문구분코드)",
        description="Echoed futures order type. '1' = new order (신규) for CIDBT00100.",
        examples=["", "1"],
    )
    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Echoed trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["", "1", "2"],
    )
    AbrdFutsOrdPtnCode: str = Field(
        default="",
        title="Overseas futures order pattern code (해외선물주문유형코드)",
        description="Echoed order pattern. '1' = market (시장가), '2' = limit (지정가).",
        examples=["", "1", "2"],
    )
    CrcyCode: str = Field(
        default="",
        title="Currency code (통화코드)",
        description="Echoed currency code. Enum mapping not declared in available source.",
        examples=["", "USD"],
    )
    OvrsDrvtOrdPrc: float = Field(
        default=0.0,
        title="Overseas derivative order price (해외파생주문가격)",
        description="Echoed limit order price. Decimal scale not declared in available source.",
        examples=[0.0, 0.64935],
    )
    CndiOrdPrc: float = Field(
        default=0.0,
        title="Conditional order price (조건주문가격)",
        description="Echoed condition price. Decimal scale not declared in available source.",
        examples=[0.0],
    )
    OrdQty: int = Field(
        default=0,
        title="Order quantity (주문수량)",
        description="Echoed order quantity in contracts.",
        examples=[0, 1],
    )
    PrdtCode: str = Field(
        default="",
        title="Product code (상품코드)",
        description="Echoed product code. Code values not declared in available source.",
        examples=["", "000000"],
    )
    DueYymm: str = Field(
        default="",
        title="Due year/month (만기년월)",
        description="Echoed contract expiry year/month. Format not declared in available source.",
        examples=["", "000000", "2512"],
    )
    ExchCode: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description="Echoed exchange code. Enum mapping not declared in available source.",
        examples=["", "CME"],
    )


class CIDBT00100OutBlock2(BaseModel):
    """CIDBT00100OutBlock2 — order acknowledgment block.

    Carries the LS-assigned overseas futures order number assigned to the
    submitted order. Present only on a successful order submission.
    """

    RecCnt: int = Field(
        default=0,
        title="Record count (레코드갯수)",
        description="Record count for this acknowledgment block.",
        examples=[0, 1],
    )
    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number that placed the order.",
        examples=["", "12345678901"],
    )
    OvrsFutsOrdNo: str = Field(
        default="",
        title="Overseas futures order number (해외선물주문번호)",
        description=(
            "LS-assigned overseas futures order number for the new order. "
            "Use this value for subsequent modify (CIDBT00900) or cancel "
            "(CIDBT01000) requests via OvrsFutsOrgOrdNo."
        ),
        examples=["", "2250", "2278"],
    )


class CIDBT00100Response(BaseModel):
    """CIDBT00100 full response envelope."""

    header: Optional[CIDBT00100ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBT00100OutBlock1] = Field(
        None,
        title="First output block — input echo (첫번째 출력 블록 — 입력 에코)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[CIDBT00100OutBlock2] = Field(
        None,
        title="Second output block — order acknowledgment (두번째 출력 블록 — 주문 응답)",
        description="Order acknowledgment block. Contains the LS-assigned overseas futures order number on success.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP status code (HTTP 상태 코드)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="LS response code (응답 코드)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="LS response message (응답 메시지)",
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
