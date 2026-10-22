"""Pydantic models for LS Securities OpenAPI COSMT00300 (Overseas Stock Margin/Loan Sell-Repayment Order — US Markets).

COSMT00300 places a margin loan sell-repayment order (해외증권 매도상환주문) for
US-listed overseas stocks. The input structure mirrors COSAT00301 but adds
margin/credit fields (``MgntrnCode``, ``LoanDt``, ``LoanDtlClssCode``) and
provides ``AcntNo`` / ``InptPwd`` directly in the InBlock rather than deriving
them server-side.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Enum codes (OrdPtnCode, OrdMktCode, OrdprcPtnCode) documented verbatim
      from the Korean docstring / inline comments in the original source.
    - Fields whose enum / format semantics are not declared in the original
      source use "not declared in available source; consume as returned by LS."
    - No companion example script exists for COSMT00300; ``examples`` use safe
      placeholder values. Account number placeholder ``"12345678901"`` is always
      used — never real accounts.

SAFETY: This is a live order-placement TR. Examples are illustrative only and
must NOT be used as-is to submit real orders.
"""

from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSMT00300RequestHeader(BlockRequestHeader):
    """COSMT00300 request header. Inherits the standard LS request header schema."""
    pass


class COSMT00300ResponseHeader(BlockResponseHeader):
    """COSMT00300 response header. Inherits the standard LS response header schema."""
    pass


class COSMT00300InBlock1(BaseModel):
    """COSMT00300InBlock1 — input block for a US-market margin loan sell-repayment order.

    ``OrdPtnCode`` controls whether this is a sell ('01'), buy ('02'), or cancel
    ('08'). For cancel orders, ``OrgOrdNo`` is required. Unlike COSAT00301, this
    TR accepts ``AcntNo`` and ``InptPwd`` directly in the InBlock, and supports
    margin/credit fields ``MgntrnCode``, ``LoanDt``, and ``LoanDtlClssCode``.
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples always use 1.",
        examples=[1],
    )
    OrdPtnCode: Literal["01", "02", "08"] = Field(
        ...,
        title="주문유형코드 (Order type code)",
        description=(
            "Order type. '01' = sell (매도), '02' = buy (매수), '08' = cancel (취소)."
        ),
        examples=["01", "02", "08"],
    )
    OrgOrdNo: Optional[int] = Field(
        default=None,
        title="원주문번호 (Original order number)",
        description=(
            "Original order number. Required only for cancel orders "
            "(OrdPtnCode='08'). Omit (None) for new buy/sell orders."
        ),
        examples=[None, 1234567],
    )
    AcntNo: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number for the order. Length not declared in available source.",
        examples=["12345678901"],
    )
    InptPwd: str = Field(
        ...,
        title="입력비밀번호 (Input password)",
        description="Account password. Treat as sensitive — avoid logging.",
        examples=[""],
    )
    OrdMktCode: Literal["81", "82"] = Field(
        ...,
        title="주문시장코드 (Order market code)",
        description="Order market. '81' = NYSE (뉴욕), '82' = NASDAQ (나스닥).",
        examples=["82", "81"],
    )
    IsuNo: str = Field(
        ...,
        title="종목번호 (Issue / symbol code)",
        description="Short symbol code (단축종목코드) of the issue to trade (e.g., 'AAPL').",
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
            "declared in available source — consume as returned by LS. "
            "For market orders (OrdprcPtnCode='03') the value is typically 0."
        ),
        examples=[180.5, 0.0],
    )
    OrdprcPtnCode: Literal["00", "03", "M1", "M2", "M3", "M4"] = Field(
        ...,
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type. '00' = limit (지정가), '03' = market (시장가), "
            "'M1' = LOO (Limit-On-Open), 'M2' = LOC (Limit-On-Close), "
            "'M3' = MOO (Market-On-Open), 'M4' = MOC (Market-On-Close)."
        ),
        examples=["00", "03", "M1", "M2", "M3", "M4"],
    )
    BrkTpCode: str = Field(
        "",
        title="중개인구분코드 (Broker type code)",
        description=(
            "Broker classification code. Enum mapping not declared in available source — "
            "consume as returned by LS. Pass empty string for the default broker."
        ),
        examples=["", "01"],
    )
    MgntrnCode: str = Field(
        "",
        title="신용거래코드 (Margin/credit transaction code)",
        description=(
            "Margin or credit transaction code for the sell-repayment. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "000"],
    )
    LoanDt: str = Field(
        "",
        title="대출일자 (Loan date)",
        description="Loan date in YYYYMMDD format. Pass empty string when not applicable.",
        examples=["", "20260101"],
    )


class COSMT00300Request(BaseModel):
    """COSMT00300 full request envelope (header + body + setup options)."""

    header: COSMT00300RequestHeader = Field(
        COSMT00300RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSMT00300",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, COSMT00300InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSMT00300InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSMT00300"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSMT00300OutBlock1(BaseModel):
    """COSMT00300OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1. Additional fields
    ``RegCommdaCode`` and ``LoanDtlClssCode`` are appended server-side.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Echoed record count.",
        examples=[0, 1],
    )
    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드 (Order type code)",
        description="Echoed order type. '01' = sell, '02' = buy, '08' = cancel.",
        examples=["01", "02", "08"],
    )
    OrgOrdNo: Optional[int] = Field(
        default=None,
        title="원주문번호 (Original order number)",
        description="Echoed original order number. None for new orders.",
        examples=[None, 1234567],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Echoed account number. Length not declared in available source.",
        examples=["12345678901"],
    )
    InptPwd: str = Field(
        default="",
        title="입력비밀번호 (Input password)",
        description=(
            "Account password echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )
    OrdMktCode: str = Field(
        default="",
        title="주문시장코드 (Order market code)",
        description="Echoed market code. '81' = NYSE, '82' = NASDAQ.",
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
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드 (Order-price type code)",
        description=(
            "Echoed order-price type. '00' = limit, '03' = market, "
            "'M1' = LOO, 'M2' = LOC, 'M3' = MOO, 'M4' = MOC."
        ),
        examples=["00", "03"],
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
    BrkTpCode: str = Field(
        default="",
        title="중개인구분코드 (Broker type code)",
        description="Echoed broker classification code.",
        examples=["", "01"],
    )
    MgntrnCode: str = Field(
        default="",
        title="신용거래코드 (Margin/credit transaction code)",
        description="Echoed margin/credit transaction code.",
        examples=["", "000"],
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
        description=(
            "Loan detail classification code appended server-side. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "01"],
    )


class COSMT00300OutBlock2(BaseModel):
    """COSMT00300OutBlock2 — order acknowledgment block.

    Contains the LS-assigned order number and display names for the account
    and issue. Present only on a successful order submission.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this acknowledgment block.",
        examples=[0, 1],
    )
    OrdNo: int = Field(
        default=0,
        title="주문번호 (Order number)",
        description="LS-assigned order number for the submitted sell-repayment order.",
        examples=[0, 1234567],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account name)",
        description="Display name of the account that placed the order.",
        examples=["홍길동", "Test Account"],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Issue name)",
        description="Display name of the ordered issue.",
        examples=["APPLE INC", "MICROSOFT CORP"],
    )


class COSMT00300Response(BaseModel):
    """COSMT00300 full response envelope."""

    header: Optional[COSMT00300ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    LoanDtlClssCode: Optional[str] = Field(
        None,
        title="대출상세분류코드 (Loan detail classification code)",
        description=(
            "Loan detail classification code returned at the response envelope level. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=[None, "01"],
    )
    block1: Optional[COSMT00300OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[COSMT00300OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block — order acknowledgment)",
        description="Order acknowledgment block. Contains LS-assigned order number on success.",
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
