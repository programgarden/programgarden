"""Pydantic models for LS Securities OpenAPI CSPAT00701 (Korea Stock Spot Modify Order).

CSPAT00701 modifies the price / quantity / order-price type of an existing Korean
spot equity order. ``OrgOrdNo`` is the original order number returned by
CSPAT00601 in OutBlock2.OrdNo. InBlock1 carries the modify parameters; OutBlock1
echoes them back; OutBlock2 returns the new LS-assigned order number plus the
parent order number (``PrntOrdNo``) for chained-modify lineage.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      The Korean source label is appended in parentheses inside ``title`` for
      AI chatbot Korean<->English mapping.
    - Enum codes (OrdprcPtnCode, OrdCndiTpCode) are documented verbatim from
      the Korean docstring in the original source. Note: '12' (midpoint) is
      not in the modify-supported set per source -- preserved verbatim.
    - OutBlock fields whose enum mapping is not declared in available source
      use "consume as returned by LS."
    - ``examples`` come from ``src/finance/example/korea_stock/run_CSPAT00701.py``
      (modify against an intentionally non-existent OrgOrdNo for safe testing)
      plus safe placeholder values. Account number placeholder ``"12345678901"``
      is always used -- never real accounts.

SAFETY: This is a live order-modify TR. Examples are illustrative only and
must NOT be used as-is to modify real orders.
"""

from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAT00701RequestHeader(BlockRequestHeader):
    """CSPAT00701 request header. Inherits the standard LS request header schema."""
    pass


class CSPAT00701ResponseHeader(BlockResponseHeader):
    """CSPAT00701 response header. Inherits the standard LS response header schema."""
    pass


class CSPAT00701InBlock1(BaseModel):
    """CSPAT00701InBlock1 -- input block for a Korean spot modify order.

    Modifies the price / quantity / order-price type of an existing order
    identified by ``OrgOrdNo`` (the OrdNo returned by CSPAT00601). Only fields
    eligible for modification are accepted -- LS rejects modifying instruments,
    accounts, or buy/sell direction.
    """

    OrgOrdNo: int = Field(
        ...,
        title="원주문번호 (Original order number)",
        description=(
            "Order number to modify. Use the ``OrdNo`` returned by CSPAT00601 "
            "OutBlock2 for the original order."
        ),
        examples=[1234567, 999999],
    )
    IsuNo: str = Field(
        ...,
        title="종목번호 (Issue / symbol code)",
        description=(
            "Issue code of the original order. Stock / ETF: 6-digit code or "
            "'A' + 6-digit code (simulation accounts always use 'A' + code). "
            "ELW: 'J' + 6-digit code. ETN: 'Q' + 6-digit code."
        ),
        examples=["005930", "A005930"],
    )
    OrdQty: int = Field(
        ...,
        title="주문수량 (Order quantity)",
        description="New order quantity in shares.",
        examples=[1, 10],
    )
    OrdprcPtnCode: Literal["00", "03", "05", "06", "07", "61", "81", "82"] = Field(
        default="00",
        title="호가유형코드 (Order-price type code)",
        description=(
            "New order-price type. '00' = limit (지정가), '03' = market (시장가), "
            "'05' = conditional limit (조건부지정가), '06' = best limit (최유리지정가), "
            "'07' = top limit (최우선지정가), "
            "'61' = pre-open after-hours close (장개시전시간외종가), "
            "'81' = after-hours close (시간외종가), "
            "'82' = after-hours single-price (시간외단일가). "
            "Note: '12' (midpoint) is not in the modify-supported set per source."
        ),
        examples=["00", "03"],
    )
    OrdCndiTpCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="주문조건구분 (Order condition type code)",
        description="Order condition. '0' = none, '1' = IOC, '2' = FOK.",
        examples=["0", "1", "2"],
    )
    OrdPrc: float = Field(
        default=0,
        title="주문가 (Order price)",
        description=(
            "New order price in KRW. Use 0 for market orders ('03') and other "
            "non-limit price types. Decimal scale not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=[0, 100, 70000],
    )


class CSPAT00701Request(BaseModel):
    """CSPAT00701 full request envelope (header + body + setup options)."""

    header: CSPAT00701RequestHeader = Field(
        CSPAT00701RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CSPAT00701",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CSPAT00701InBlock1"], CSPAT00701InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'CSPAT00701InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CSPAT00701"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CSPAT00701OutBlock1(BaseModel):
    """CSPAT00701OutBlock1 -- input echo block.

    LS echoes the InBlock1 inputs back along with server-appended fields
    (account number, password, communication medium, basket / strategy fields).
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Echoed record count.",
        examples=[0, 1],
    )
    OrgOrdNo: int = Field(
        default=0,
        title="원주문번호 (Original order number)",
        description="Echoed original order number.",
        examples=[0, 1234567],
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
            "Account password echoed by LS. Treat as sensitive -- avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue / symbol code)",
        description="Echoed issue code.",
        examples=["005930", "A005930"],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Echoed new order quantity.",
        examples=[0, 1],
    )
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드 (Order-price type code)",
        description=(
            "Echoed order-price type. '00' = limit, '03' = market, '05' = conditional limit, "
            "'06' = best limit, '07' = top limit, '61' = pre-open after-hours close, "
            "'81' = after-hours close, '82' = after-hours single-price."
        ),
        examples=["00", "03"],
    )
    OrdCndiTpCode: str = Field(
        default="",
        title="주문조건구분 (Order condition type code)",
        description="Echoed order condition flag. '0' = none, '1' = IOC, '2' = FOK.",
        examples=["0"],
    )
    OrdPrc: float = Field(
        default=0,
        title="주문가 (Order price)",
        description="Echoed new order price.",
        examples=[0, 100],
    )
    CommdaCode: str = Field(
        default="",
        title="통신매체코드 (Communication medium code)",
        description=(
            "Communication channel code recorded by LS for this modify request. "
            "Enum mapping not declared in available source -- consume as returned by LS."
        ),
        examples=[""],
    )
    StrtgCode: str = Field(
        default="",
        title="전략코드 (Strategy code)",
        description=(
            "Strategy code for institutional / basket orders. Enum mapping not "
            "declared in available source -- consume as returned by LS."
        ),
        examples=[""],
    )
    GrpId: str = Field(
        default="",
        title="그룹ID (Group ID)",
        description="Order group identifier for institutional / basket orders.",
        examples=[""],
    )
    OrdSeqNo: int = Field(
        default=0,
        title="주문회차 (Order sequence number)",
        description="Order sequence number for batched / multi-step orders.",
        examples=[0],
    )
    PtflNo: int = Field(
        default=0,
        title="포트폴리오번호 (Portfolio number)",
        description="Portfolio identifier for institutional orders.",
        examples=[0],
    )
    BskNo: int = Field(
        default=0,
        title="바스켓번호 (Basket number)",
        description="Basket identifier for institutional / basket orders.",
        examples=[0],
    )
    TrchNo: int = Field(
        default=0,
        title="트렌치번호 (Tranche number)",
        description="Tranche identifier for institutional / basket orders.",
        examples=[0],
    )
    ItemNo: int = Field(
        default=0,
        title="아이템번호 (Item number)",
        description="Item index within the order basket / tranche.",
        examples=[0],
    )


class CSPAT00701OutBlock2(BaseModel):
    """CSPAT00701OutBlock2 -- modify acknowledgment block.

    Returned on a successful modify submission. ``OrdNo`` is the new LS-assigned
    order number for the modified order; ``PrntOrdNo`` is the parent order
    number used for chained-modify lineage.
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
        description="LS-assigned new order number for the modified order.",
        examples=[0, 1234568],
    )
    PrntOrdNo: int = Field(
        default=0,
        title="모주문번호 (Parent order number)",
        description="Parent order number in the modify chain (links back to the prior order).",
        examples=[0, 1234567],
    )
    OrdTime: str = Field(
        default="",
        title="주문시각 (Order time)",
        description=(
            "Time the modify order was accepted. Format not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=["", "090015123"],
    )
    OrdMktCode: str = Field(
        default="",
        title="주문시장코드 (Order market code)",
        description=(
            "Market the order was routed to. Enum mapping not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=[""],
    )
    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드 (Order pattern code)",
        description=(
            "Order-pattern classification. Enum mapping not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=[""],
    )
    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호 (Short issue code)",
        description="Short issue code (6-digit) for the modified instrument.",
        examples=["005930"],
    )
    PrgmOrdprcPtnCode: str = Field(
        default="",
        title="프로그램호가유형코드 (Program order-price type code)",
        description=(
            "Program-trade order-price type. Enum mapping not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=[""],
    )
    StslOrdprcTpCode: str = Field(
        default="",
        title="공매도호가구분 (Short-sale order-price type code)",
        description=(
            "Short-sale order-price classification. Enum mapping not declared in "
            "available source -- consume as returned by LS."
        ),
        examples=[""],
    )
    StslAbleYn: str = Field(
        default="",
        title="공매도가능여부 (Short-sale eligibility flag)",
        description=(
            "Whether the order is eligible to be treated as a short sale. Enum mapping "
            "not declared in available source -- consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    MgntrnCode: str = Field(
        default="",
        title="신용거래코드 (Credit-trade code)",
        description=(
            "Credit-trade flag inherited from the original order. See CSPAT00601 "
            "InBlock1 for the enum mapping."
        ),
        examples=["000"],
    )
    LoanDt: str = Field(
        default="",
        title="대출일 (Loan date)",
        description="Loan origination date inherited from the original order.",
        examples=[""],
    )
    CvrgOrdTp: str = Field(
        default="",
        title="반대매매주문구분 (Forced-liquidation order type)",
        description=(
            "Forced-liquidation classification. Enum mapping not declared in "
            "available source -- consume as returned by LS."
        ),
        examples=[""],
    )
    LpYn: str = Field(
        default="",
        title="유동성공급자여부 (Liquidity-provider flag)",
        description=(
            "Whether the order originates from a registered liquidity provider. "
            "Enum mapping not declared in available source -- consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )
    MgempNo: str = Field(
        default="",
        title="관리사원번호 (Managing-staff number)",
        description="Internal staff/manager identifier recorded by LS.",
        examples=[""],
    )
    OrdAmt: int = Field(
        default=0,
        title="주문금액 (Order amount)",
        description=(
            "Modified order amount in KRW. Decimal scale not declared in available "
            "source -- consume as returned by LS."
        ),
        examples=[0, 100],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분 (Buy/sell type code)",
        description="Buy/sell flag inherited from the original order. '1' = sell, '2' = buy.",
        examples=["1", "2"],
    )
    SpareOrdNo: int = Field(
        default=0,
        title="예비주문번호 (Reserve order number)",
        description="Spare order number for internal LS bookkeeping.",
        examples=[0],
    )
    CvrgSeqno: int = Field(
        default=0,
        title="반대매매일련번호 (Forced-liquidation sequence number)",
        description="Sequence number for forced-liquidation chains; 0 for ordinary orders.",
        examples=[0],
    )
    RsvOrdNo: int = Field(
        default=0,
        title="예약주문번호 (Reserved order number)",
        description="Reserved-order identifier; 0 when not a reserved order.",
        examples=[0],
    )
    MnyOrdAmt: int = Field(
        default=0,
        title="현금주문금액 (Cash order amount)",
        description="Cash component of the order amount.",
        examples=[0],
    )
    SubstOrdAmt: int = Field(
        default=0,
        title="대용주문금액 (Substitute order amount)",
        description="Substitute-securities component of the order amount.",
        examples=[0],
    )
    RuseOrdAmt: int = Field(
        default=0,
        title="재사용주문금액 (Reused order amount)",
        description="Reused-settlement-position component of the order amount.",
        examples=[0],
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
        description="Display name of the modified issue.",
        examples=["삼성전자", "Samsung Electronics"],
    )


class CSPAT00701Response(BaseModel):
    """CSPAT00701 full response envelope.

    ``rsp_cd`` codes are not declared in available source -- inspect ``rsp_msg``
    for accept / reject reasons. A modify against a non-existent ``OrgOrdNo``
    typically returns a non-success ``rsp_cd`` with descriptive ``rsp_msg``.
    """

    header: Optional[CSPAT00701ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CSPAT00701OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block -- input echo)",
        description="Input echo block (mirrors InBlock1 plus server-appended fields).",
    )
    block2: Optional[CSPAT00701OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block -- modify acknowledgment)",
        description=(
            "Modify acknowledgment block. Contains the new LS-assigned order "
            "number plus parent order number on success."
        ),
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드 (HTTP status code)",
        description="HTTP status code from the request. None when no response was received.",
    )
    rsp_cd: str = Field(
        ...,
        title="응답 코드 (LS response code)",
        description="LS response code. Specific success / failure codes not declared in available source.",
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
