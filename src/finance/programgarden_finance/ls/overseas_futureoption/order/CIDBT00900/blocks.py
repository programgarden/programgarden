"""Pydantic models for LS Securities OpenAPI CIDBT00900 (Overseas Futures Modify Order).

CIDBT00900 modifies (정정) an existing overseas futures order. ``FutsOrdTpCode``
is fixed at '2' (정정). The original LS-assigned order number must be supplied
via ``OvrsFutsOrgOrdNo``. ``FutsOrdPtnCode`` is fixed at '2' (지정가) — modify
operations require a limit price.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Enum codes (FutsOrdTpCode, BnsTpCode, FutsOrdPtnCode) are documented
      verbatim from the Korean source docstring.
    - Decimal scale, currency unit, contract multiplier, and tick-value
      semantics for overseas futures are NOT declared in the source available
      to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS" or "not declared in available source".
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBT00900.py``
      (ADZ25 modify of order '2250') plus safe placeholder values. Account
      number placeholder "12345678901" is always used — never real accounts.

SAFETY: This is a live order-modification TR. Examples are illustrative only
and must NOT be used as-is to submit real order modifications.
"""

from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBT00900RequestHeader(BlockRequestHeader):
    """CIDBT00900 request header. Inherits the standard LS request header schema."""
    pass


class CIDBT00900ResponseHeader(BlockResponseHeader):
    """CIDBT00900 response header. Inherits the standard LS response header schema."""
    pass


class CIDBT00900InBlock1(BaseModel):
    """CIDBT00900InBlock1 — input block for an overseas futures modify order.

    ``FutsOrdTpCode`` is always '2' (정정) and ``FutsOrdPtnCode`` is always '2'
    (지정가). ``OvrsFutsOrgOrdNo`` identifies the existing order to modify;
    the remaining fields specify the revised order parameters.
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
    OvrsFutsOrgOrdNo: str = Field(
        ...,
        title="Overseas futures original order number (해외선물원주문번호)",
        description=(
            "LS-assigned order number of the existing order to be modified. "
            "Obtained from a prior CIDBT00100 OutBlock2.OvrsFutsOrdNo response."
        ),
        examples=["2250", "2278"],
    )
    IsuCodeVal: str = Field(
        ...,
        title="Issue code value (종목코드값)",
        description=(
            "LS instrument code for the overseas futures contract being modified. "
            "Must match the original order's instrument."
        ),
        examples=["ADZ25", "ESM26", "NQU26"],
    )
    FutsOrdTpCode: Literal["2"] = Field(
        ...,
        title="Futures order type code (선물주문구분코드)",
        description="Futures order type. Always '2' = modify order (정정) for CIDBT00900.",
        examples=["2"],
    )
    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )
    FutsOrdPtnCode: Literal["2"] = Field(
        ...,
        title="Futures order pattern code (선물주문유형코드)",
        description="Order pattern. Always '2' = limit order (지정가) for modify operations.",
        examples=["2"],
    )
    CrcyCodeVal: str = Field(
        "",
        title="Currency code value (통화코드값)",
        description=(
            "Currency code value for the order. Empty / blank string is accepted "
            "by LS. Enum mapping not declared in available source — consume as "
            "returned by LS."
        ),
        examples=["", "USD"],
    )
    OvrsDrvtOrdPrc: float = Field(
        ...,
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Revised limit order price in the instrument's quote currency. "
            "Decimal scale not declared in available source — consume as "
            "returned by LS."
        ),
        examples=[0.64935, 4500.25],
    )
    CndiOrdPrc: float = Field(
        ...,
        title="Conditional order price (조건주문가격)",
        description=(
            "Condition / trigger price. Example script uses 0. Decimal scale "
            "and trigger semantics not declared in available source — consume "
            "as returned by LS."
        ),
        examples=[0, 0.0],
    )
    OrdQty: int = Field(
        ...,
        title="Order quantity (주문수량)",
        description="Revised order quantity in contracts. Example script uses 1.",
        examples=[1, 5],
    )
    OvrsDrvtPrdtCode: str = Field(
        "",
        title="Overseas derivative product code (해외파생상품코드)",
        description=(
            "Overseas derivative product code. Empty / blank string is accepted "
            "by LS. Code values not declared in available source — consume as "
            "returned by LS."
        ),
        examples=["", " "],
    )
    DueYymm: str = Field(
        "",
        title="Due year/month (만기년월)",
        description=(
            "Contract expiry year/month. Format hinted as YYMM in the source "
            "docstring; full length / zero-pad rules not declared in available "
            "source — consume as returned by LS."
        ),
        examples=["", "2512"],
    )
    ExchCode: str = Field(
        "",
        title="Exchange code (거래소코드)",
        description=(
            "Exchange code. Empty / blank string is accepted by LS. Enum "
            "mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "CME"],
    )


class CIDBT00900Request(BaseModel):
    """CIDBT00900 full request envelope (header + body + setup options)."""

    header: CIDBT00900RequestHeader = Field(
        CIDBT00900RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBT00900",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, CIDBT00900InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBT00900InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=5,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBT00900"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBT00900OutBlock1(BaseModel):
    """CIDBT00900OutBlock1 — input echo block for the modify order request.

    LS echoes the InBlock1 inputs back in OutBlock1. Additional server-side
    fields ``RegBrnNo``, ``AcntNo``, and ``Pwd`` identify the originating
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
    RegBrnNo: str = Field(
        default="",
        title="Registered branch number (등록지점번호)",
        description="Branch number registered to the account. Length not declared in available source.",
        examples=["", "001"],
    )
    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number that placed the modification. Length not declared in available source.",
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
    OvrsFutsOrgOrdNo: str = Field(
        default="",
        title="Overseas futures original order number (해외선물원주문번호)",
        description="Echoed original order number that was modified.",
        examples=["", "2250"],
    )
    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Echoed instrument code for the modified overseas futures contract.",
        examples=["", "ADZ25"],
    )
    FutsOrdTpCode: str = Field(
        default="",
        title="Futures order type code (선물주문구분코드)",
        description="Echoed futures order type. '2' = modify order (정정) for CIDBT00900.",
        examples=["", "2"],
    )
    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Echoed trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["", "1", "2"],
    )
    FutsOrdPtnCode: str = Field(
        default="",
        title="Futures order pattern code (선물주문유형코드)",
        description="Echoed order pattern. '2' = limit (지정가) for modify operations.",
        examples=["", "2"],
    )
    CrcyCodeVal: str = Field(
        default="",
        title="Currency code value (통화코드값)",
        description="Echoed currency code value. Enum mapping not declared in available source.",
        examples=["", "USD"],
    )
    OvrsDrvtOrdPrc: float = Field(
        default=0.0,
        title="Overseas derivative order price (해외파생주문가격)",
        description="Echoed revised limit order price. Decimal scale not declared in available source.",
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
        description="Echoed revised order quantity in contracts.",
        examples=[0, 1],
    )
    OvrsDrvtPrdtCode: str = Field(
        default="",
        title="Overseas derivative product code (해외파생상품코드)",
        description="Echoed overseas derivative product code. Code values not declared in available source.",
        examples=["", " "],
    )
    DueYymm: str = Field(
        default="",
        title="Due year/month (만기년월)",
        description="Echoed contract expiry year/month. Format not declared in available source.",
        examples=["", "2512"],
    )
    ExchCode: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description="Echoed exchange code. Enum mapping not declared in available source.",
        examples=["", "CME"],
    )


class CIDBT00900OutBlock2(BaseModel):
    """CIDBT00900OutBlock2 — modification acknowledgment block.

    Carries the LS-assigned overseas futures order number for the modified
    order plus an inner message string. Present only on a successful
    modification.
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
        description="Account number that placed the modification.",
        examples=["", "12345678901"],
    )
    OvrsFutsOrdNo: str = Field(
        default="",
        title="Overseas futures order number (해외선물주문번호)",
        description=(
            "LS-assigned overseas futures order number for the modification. "
            "Use this value for any subsequent modify or cancel against the "
            "newly-modified order."
        ),
        examples=["", "2250", "2278"],
    )
    InnerMsgCnts: str = Field(
        default="",
        title="Inner message contents (내부메시지내용)",
        description=(
            "Server-side inner message text accompanying the modification "
            "acknowledgment. Content semantics not declared in available "
            "source — consume as returned by LS."
        ),
        examples=["", "정상 처리"],
    )


class CIDBT00900Response(BaseModel):
    """CIDBT00900 full response envelope."""

    header: Optional[CIDBT00900ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBT00900OutBlock1] = Field(
        None,
        title="First output block — input echo (첫번째 출력 블록 — 입력 에코)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[CIDBT00900OutBlock2] = Field(
        None,
        title="Second output block — modification acknowledgment (두번째 출력 블록 — 정정 응답)",
        description="Modification acknowledgment block. Contains LS-assigned order number on success.",
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
