"""Pydantic models for LS Securities OpenAPI COSAT00311 (Overseas Stock Modify Order — US Markets).

COSAT00311 modifies an existing US-market overseas stock order. The order type
is always '07' (정정주문 / modify). Both the original order number (``OrgOrdNo``)
and the revised quantity / price / price-type are required.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Enum codes (OrdPtnCode, OrdMktCode) are documented verbatim from the
      Korean docstring in the original source.
    - ``OrdprcPtnCode`` in InBlock1 is a plain ``str`` in the source (no enum
      constraint declared); description lists the same codes as COSAT00301 as
      context but uses "not declared in available source" for the enum wording.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_COSAT00311.py``
      (ESPR 1-share modify test) plus safe placeholder values.
      Account number placeholder ``"12345678901"`` is always used — never real accounts.

SAFETY: This is a live order-modification TR. Examples are illustrative only and
must NOT be used as-is to submit real order modifications.
"""

from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAT00311RequestHeader(BlockRequestHeader):
    """COSAT00311 request header. Inherits the standard LS request header schema."""
    pass


class COSAT00311ResponseHeader(BlockResponseHeader):
    """COSAT00311 response header. Inherits the standard LS response header schema."""
    pass


class COSAT00311InBlock1(BaseModel):
    """COSAT00311InBlock1 — input block for a US-market order modification.

    ``OrdPtnCode`` is always '07' (정정주문). ``OrgOrdNo`` identifies the existing
    order to modify. The remaining fields specify the revised order parameters.
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples always use 1.",
        examples=[1],
    )
    OrdPtnCode: Literal["07"] = Field(
        ...,
        title="주문유형코드 (Order type code)",
        description="Order type. Always '07' = modify order (정정주문).",
        examples=["07"],
    )
    OrgOrdNo: int = Field(
        ...,
        title="원주문번호 (Original order number)",
        description="LS-assigned order number of the existing order to be modified.",
        examples=[231, 1234567],
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
        description="Short symbol code (단축종목코드) of the issue being modified (e.g., 'AAPL').",
        examples=["AAPL", "ESPR"],
    )
    OrdQty: int = Field(
        ...,
        title="주문수량 (Order quantity)",
        description="Revised order quantity in shares.",
        examples=[1, 5],
    )
    OvrsOrdPrc: float = Field(
        ...,
        title="해외주문가 (Overseas order price)",
        description=(
            "Revised order price in the instrument's quote currency. Decimal scale not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[180.5, 2.62],
    )
    OrdprcPtnCode: str = Field(
        ...,
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type code. Typical values include '00' = limit (지정가), "
            "'03' = market (시장가). Complete enum mapping not declared in available "
            "source — consume as returned by LS."
        ),
        examples=["00", "03"],
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


class COSAT00311Request(BaseModel):
    """COSAT00311 full request envelope (header + body + setup options)."""

    header: COSAT00311RequestHeader = Field(
        COSAT00311RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAT00311",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[str, COSAT00311InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSAT00311InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=10,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAT00311"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSAT00311OutBlock1(BaseModel):
    """COSAT00311OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1. Additional fields
    ``AcntNo``, ``InptPwd``, and ``RegCommdaCode`` are appended server-side.
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
        description="Echoed order type. Always '07' for modify.",
        examples=["07"],
    )
    OrgOrdNo: int = Field(
        default=0,
        title="원주문번호 (Original order number)",
        description="Echoed original order number that was modified.",
        examples=[0, 231],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Account number associated with the order. Length not declared in available source.",
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
        examples=["AAPL", "ESPR"],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Echoed revised order quantity in shares.",
        examples=[0, 1],
    )
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가 (Overseas order price)",
        description="Echoed revised order price. Decimal scale not declared in available source.",
        examples=[0.0, 180.5],
    )
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드 (Order-price type code)",
        description="Echoed order-price type code. '00' = limit, '03' = market; others may appear.",
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


class COSAT00311OutBlock2(BaseModel):
    """COSAT00311OutBlock2 — order modification acknowledgment block.

    Contains the LS-assigned order number for the modified order and display
    names for the account and issue. Present only on a successful modification.
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
        description="LS-assigned order number for the modification.",
        examples=[0, 1234567],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account name)",
        description="Display name of the account that placed the modification.",
        examples=["홍길동", "Test Account"],
    )
    IsuNm: str = Field(
        default="",
        title="종목명 (Issue name)",
        description="Display name of the modified issue.",
        examples=["APPLE INC", "ESPERION THERAPEUTICS INC"],
    )


class COSAT00311Response(BaseModel):
    """COSAT00311 full response envelope."""

    header: Optional[COSAT00311ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSAT00311OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors InBlock1 inputs plus server-appended fields).",
    )
    block2: Optional[COSAT00311OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block — modification acknowledgment)",
        description="Modification acknowledgment block. Contains LS-assigned order number on success.",
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
