"""Pydantic models for LS Securities OpenAPI CIDBT01000 (Overseas Futures Cancel Order).

CIDBT01000 cancels (취소) an existing overseas futures order. ``FutsOrdTpCode``
is fixed at '3' (취소). The original LS-assigned order number must be supplied
via ``OvrsFutsOrgOrdNo``.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Enum codes (FutsOrdTpCode) are documented verbatim from the Korean
      source docstring.
    - ``PrdtTpCode`` and ``ExchCode`` accept a single SPACE as default per
      source. Code values are not declared in available source — descriptions
      state "consume as returned by LS".
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBT01000.py``
      (cancel of order '2278' for ADZ25) plus safe placeholder values. Account
      number placeholder "12345678901" is always used — never real accounts.

SAFETY: This is a live order-cancellation TR. Examples are illustrative only
and must NOT be used as-is to cancel real orders.
"""

from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBT01000RequestHeader(BlockRequestHeader):
    """CIDBT01000 request header. Inherits the standard LS request header schema."""
    pass


class CIDBT01000ResponseHeader(BlockResponseHeader):
    """CIDBT01000 response header. Inherits the standard LS response header schema."""
    pass


class CIDBT01000InBlock1(BaseModel):
    """CIDBT01000InBlock1 — input block for an overseas futures cancel order.

    ``FutsOrdTpCode`` is always '3' (취소). ``OvrsFutsOrgOrdNo`` identifies the
    existing order to cancel. Quantity / price are not required (the original
    order's values are cancelled in full).
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
            "LS instrument code for the overseas futures contract being cancelled. "
            "Must match the original order's instrument."
        ),
        examples=["ADZ25", "ESM26", "NQU26"],
    )
    OvrsFutsOrgOrdNo: str = Field(
        ...,
        title="Overseas futures original order number (해외선물원주문번호)",
        description=(
            "LS-assigned order number of the existing order to be cancelled. "
            "Obtained from a prior CIDBT00100 OutBlock2.OvrsFutsOrdNo response."
        ),
        examples=["2278", "2250"],
    )
    FutsOrdTpCode: Literal["3"] = Field(
        ...,
        title="Futures order type code (선물주문구분코드)",
        description="Futures order type. Always '3' = cancel order (취소) for CIDBT01000.",
        examples=["3"],
    )
    PrdtTpCode: str = Field(
        " ",
        title="Product type code (상품구분코드)",
        description=(
            "Product type code. Defaults to single SPACE — LS source notes "
            "SPACE is accepted. Code values not declared in available source — "
            "consume as returned by LS."
        ),
        examples=[" "],
    )
    ExchCode: str = Field(
        " ",
        title="Exchange code (거래소코드)",
        description=(
            "Exchange code. Defaults to single SPACE — LS source notes SPACE "
            "is accepted. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=[" ", "CME"],
    )


class CIDBT01000Request(BaseModel):
    """CIDBT01000 full request envelope (header + body + setup options)."""

    header: CIDBT01000RequestHeader = Field(
        CIDBT01000RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBT01000",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, CIDBT01000InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBT01000InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=5,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBT01000"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBT01000OutBlock1(BaseModel):
    """CIDBT01000OutBlock1 — input echo block for the cancel order request.

    LS echoes the InBlock1 inputs back in OutBlock1. Additional server-side
    fields ``BrnNo``, ``AcntNo``, and ``Pwd`` identify the originating
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
    BrnNo: str = Field(
        default="",
        title="Branch number (지점번호)",
        description="Branch number associated with the account. Length not declared in available source.",
        examples=["", "001"],
    )
    AcntNo: str = Field(
        default="",
        title="Account number (계좌번호)",
        description="Account number that placed the cancellation. Length not declared in available source.",
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
        description="Echoed instrument code for the cancelled overseas futures contract.",
        examples=["", "ADZ25"],
    )
    OvrsFutsOrgOrdNo: str = Field(
        default="",
        title="Overseas futures original order number (해외선물원주문번호)",
        description="Echoed original order number that was cancelled.",
        examples=["", "2278"],
    )
    FutsOrdTpCode: str = Field(
        default="",
        title="Futures order type code (선물주문구분코드)",
        description="Echoed futures order type. '3' = cancel order (취소) for CIDBT01000.",
        examples=["", "3"],
    )
    PrdtTpCode: str = Field(
        default="",
        title="Product type code (상품구분코드)",
        description="Echoed product type code. Code values not declared in available source.",
        examples=["", " "],
    )
    ExchCode: str = Field(
        default="",
        title="Exchange code (거래소코드)",
        description="Echoed exchange code. Enum mapping not declared in available source.",
        examples=["", "CME"],
    )


class CIDBT01000OutBlock2(BaseModel):
    """CIDBT01000OutBlock2 — cancellation acknowledgment block.

    Carries the LS-assigned overseas futures order number for the cancellation
    plus an inner message string. Present only on a successful cancellation.
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
        description="Account number that placed the cancellation.",
        examples=["", "12345678901"],
    )
    OvrsFutsOrdNo: str = Field(
        default="",
        title="Overseas futures order number (해외선물주문번호)",
        description="LS-assigned overseas futures order number for the cancellation acknowledgment.",
        examples=["", "2278"],
    )
    InnerMsgCnts: str = Field(
        default="",
        title="Inner message contents (내부메시지내용)",
        description=(
            "Server-side inner message text accompanying the cancellation "
            "acknowledgment. Content semantics not declared in available "
            "source — consume as returned by LS."
        ),
        examples=["", "정상 처리"],
    )


class CIDBT01000Response(BaseModel):
    """CIDBT01000 full response envelope."""

    header: Optional[CIDBT01000ResponseHeader] = Field(
        None,
        title="Response header (응답 헤더)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBT01000OutBlock1] = Field(
        None,
        title="First output block — input echo (첫번째 출력 블록 — 입력 에코)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[CIDBT01000OutBlock2] = Field(
        None,
        title="Second output block — cancellation acknowledgment (두번째 출력 블록 — 취소 응답)",
        description="Cancellation acknowledgment block. Contains LS-assigned order number on success.",
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
