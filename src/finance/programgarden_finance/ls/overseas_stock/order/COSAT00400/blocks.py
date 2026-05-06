"""Pydantic models for LS Securities OpenAPI COSAT00400 (Overseas Stock Reserved Order — Register / Cancel).

COSAT00400 registers or cancels a reserved (예약주문) overseas stock order. A reserved
order is scheduled to execute on a future date range (``RsvOrdSrtDt`` to ``RsvOrdEndDt``).
``TrxTpCode`` controls whether this call registers a new reserved order or cancels an
existing one. On success, OutBlock2 returns the assigned reserved order number.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Fields whose enum / format semantics are not declared in the original
      source use "not declared in available source; consume as returned by LS."
    - No companion example script exists for COSAT00400; ``examples`` use safe
      placeholder values. Account number placeholder ``"12345678901"`` is always
      used — never real accounts.

SAFETY: This is a live reserved-order TR. Examples are illustrative only and
must NOT be used as-is to submit real orders.
"""

from typing import Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAT00400RequestHeader(BlockRequestHeader):
    """COSAT00400 request header. Inherits the standard LS request header schema."""
    pass


class COSAT00400ResponseHeader(BlockResponseHeader):
    """COSAT00400 response header. Inherits the standard LS response header schema."""
    pass


class COSAT00400InBlock1(BaseModel):
    """COSAT00400InBlock1 — input block for reserved order registration or cancellation.

    Pass ``TrxTpCode`` to indicate whether this is a registration or cancellation.
    For cancellations, ``RsvOrdNo`` identifies the existing reserved order.
    ``RsvOrdSrtDt`` and ``RsvOrdEndDt`` define the execution window.
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples always use 1.",
        examples=[1],
    )
    TrxTpCode: str = Field(
        ...,
        title="처리구분코드 (Transaction type code)",
        description=(
            "Transaction type controlling whether this registers or cancels a reserved order. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["1", "2"],
    )
    CntryCode: str = Field(
        ...,
        title="국가코드 (Country code)",
        description=(
            "Country code identifying the market country. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["US", "JP"],
    )
    RsvOrdInptDt: str = Field(
        ...,
        title="예약주문입력일자 (Reserved order input date)",
        description="Date the reserved order is being entered, in YYYYMMDD format.",
        examples=["20260506", "20260601"],
    )
    RsvOrdNo: Optional[int] = Field(
        default=None,
        title="예약주문번호 (Reserved order number)",
        description=(
            "Reserved order number. Required for cancellation. "
            "Omit (None) when registering a new reserved order."
        ),
        examples=[None, 123456],
    )
    BnsTpCode: str = Field(
        ...,
        title="매매구분코드 (Buy/sell type code)",
        description=(
            "Buy/sell side of the reserved order. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["1", "2"],
    )
    AcntNo: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number for the reserved order. Length not declared in available source.",
        examples=["12345678901"],
    )
    Pwd: str = Field(
        ...,
        title="비밀번호 (Account password)",
        description="Account password. Treat as sensitive — avoid logging.",
        examples=[""],
    )
    FcurrMktCode: str = Field(
        ...,
        title="외화시장코드 (Foreign currency market code)",
        description=(
            "Foreign currency market code identifying the target exchange. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["82", "81"],
    )
    IsuNo: str = Field(
        ...,
        title="종목번호 (Issue / symbol code)",
        description="Short symbol code (단축종목코드) of the issue to trade.",
        examples=["AAPL", "MSFT"],
    )
    OrdQty: int = Field(
        ...,
        title="주문수량 (Order quantity)",
        description="Order quantity in shares.",
        examples=[1, 5],
    )
    OvrsOrdPrc: float = Field(
        ...,
        title="해외주문가 (Overseas order price)",
        description=(
            "Order price in the instrument's quote currency. Decimal scale not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[180.5, 0.0],
    )
    OrdprcPtnCode: str = Field(
        ...,
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type code. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["00", "03"],
    )
    RsvOrdSrtDt: str = Field(
        ...,
        title="예약주문시작일자 (Reserved order start date)",
        description="Start date of the reserved order execution window, in YYYYMMDD format.",
        examples=["20260510", "20260601"],
    )
    RsvOrdEndDt: str = Field(
        ...,
        title="예약주문종료일자 (Reserved order end date)",
        description="End date of the reserved order execution window, in YYYYMMDD format.",
        examples=["20260520", "20260630"],
    )
    RsvOrdCndiCode: str = Field(
        ...,
        title="예약주문조건코드 (Reserved order condition code)",
        description=(
            "Condition code for the reserved order execution. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["0", "1"],
    )
    MgntrnCode: str = Field(
        ...,
        title="신용거래코드 (Margin/credit transaction code)",
        description=(
            "Margin or credit transaction code. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["000", ""],
    )
    LoanDt: str = Field(
        ...,
        title="대출일자 (Loan date)",
        description="Loan date in YYYYMMDD format. Pass empty string when not applicable.",
        examples=["", "20260101"],
    )
    LoanDtlClssCode: str = Field(
        ...,
        title="대출상세분류코드 (Loan detail classification code)",
        description=(
            "Loan detail classification code. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "01"],
    )


class COSAT00400Request(BaseModel):
    """COSAT00400 full request envelope (header + body + setup options)."""

    header: COSAT00400RequestHeader = Field(
        COSAT00400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAT00400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, COSAT00400InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSAT00400InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=10,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAT00400"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSAT00400OutBlock1(BaseModel):
    """COSAT00400OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1, appending
    ``RegCommdaCode`` server-side.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Echoed record count.",
        examples=[0, 1],
    )
    TrxTpCode: str = Field(
        default="",
        title="처리구분코드 (Transaction type code)",
        description="Echoed transaction type code.",
        examples=["1", "2"],
    )
    CntryCode: str = Field(
        default="",
        title="국가코드 (Country code)",
        description="Echoed country code.",
        examples=["US", "JP"],
    )
    RsvOrdInptDt: str = Field(
        default="",
        title="예약주문입력일자 (Reserved order input date)",
        description="Echoed reserved order input date in YYYYMMDD format.",
        examples=["20260506"],
    )
    RsvOrdNo: Optional[int] = Field(
        default=None,
        title="예약주문번호 (Reserved order number)",
        description="Echoed reserved order number. None for new registration.",
        examples=[None, 123456],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드 (Buy/sell type code)",
        description="Echoed buy/sell side code.",
        examples=["1", "2"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Echoed account number. Length not declared in available source.",
        examples=["12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password)",
        description="Echoed account password. Treat as sensitive — avoid logging.",
        examples=[""],
    )
    FcurrMktCode: str = Field(
        default="",
        title="외화시장코드 (Foreign currency market code)",
        description="Echoed foreign currency market code.",
        examples=["82", "81"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue / symbol code)",
        description="Echoed short symbol code.",
        examples=["AAPL", "MSFT"],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Echoed order quantity in shares.",
        examples=[0, 1],
    )
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가 (Overseas order price)",
        description="Echoed order price. Decimal scale not declared in available source.",
        examples=[0.0, 180.5],
    )
    RegCommdaCode: str = Field(
        default="",
        title="등록통신매체코드 (Registered communication medium code)",
        description=(
            "Communication channel code registered for the order. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "00"],
    )
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드 (Order-price type code)",
        description="Echoed order-price type code.",
        examples=["00", "03"],
    )
    RsvOrdSrtDt: str = Field(
        default="",
        title="예약주문시작일자 (Reserved order start date)",
        description="Echoed start date of the execution window in YYYYMMDD format.",
        examples=["20260510"],
    )
    RsvOrdEndDt: str = Field(
        default="",
        title="예약주문종료일자 (Reserved order end date)",
        description="Echoed end date of the execution window in YYYYMMDD format.",
        examples=["20260520"],
    )
    RsvOrdCndiCode: str = Field(
        default="",
        title="예약주문조건코드 (Reserved order condition code)",
        description="Echoed reserved order condition code.",
        examples=["0", "1"],
    )
    MgntrnCode: str = Field(
        default="",
        title="신용거래코드 (Margin/credit transaction code)",
        description="Echoed margin/credit transaction code.",
        examples=["000", ""],
    )
    LoanDt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description="Echoed loan date in YYYYMMDD format. Empty when not applicable.",
        examples=["", "20260101"],
    )
    LoanDtlClssCode: str = Field(
        default="",
        title="대출상세분류코드 (Loan detail classification code)",
        description="Echoed loan detail classification code.",
        examples=["", "01"],
    )


class COSAT00400OutBlock2(BaseModel):
    """COSAT00400OutBlock2 — reserved order acknowledgment block.

    Contains the LS-assigned reserved order number on successful registration.
    Present only when the request succeeds.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this acknowledgment block.",
        examples=[0, 1],
    )
    RsvOrdNo: Optional[int] = Field(
        default=None,
        title="예약주문번호 (Reserved order number)",
        description="LS-assigned reserved order number. Present on successful registration.",
        examples=[None, 123456],
    )


class COSAT00400Response(BaseModel):
    """COSAT00400 full response envelope."""

    header: Optional[COSAT00400ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSAT00400OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[COSAT00400OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block — reserved order acknowledgment)",
        description="Reserved order acknowledgment block. Contains LS-assigned reserved order number on success.",
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. '00000' indicates success.",
    )
    rsp_msg: str = Field(
        ...,
        title="응답 메시지 (LS response message)",
        description="LS response message text.",
    )
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지 (Error message)",
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
