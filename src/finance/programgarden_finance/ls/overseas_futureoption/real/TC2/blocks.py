"""Pydantic models for LS Securities OpenAPI TC2 (Overseas Futures Order Response — confirm / reject).

TC2 is a Real-time WebSocket TR that pushes the exchange-side response
to overseas-futures order requests (confirmation or rejection that
follows the LS-side ACK pushed via TC1). The ``TC2RealRequestBody``
carries the WebSocket subscription envelope (``tr_cd`` + optional
``tr_key``); the ``TC2RealResponseBody`` carries the per-event push
payload (order metadata, prices, quantity, and rejection reason fields
for HO03 events).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Code classifiers documented in the in-source Korean comments
      (``s_b_ccd``, ``ordr_ccd``, ``ordr_typ_cd``, ``svc_id``) are listed
      verbatim. The ``ordr_typ_cd`` ``Literal["1", "2", "3", "4"]``
      annotation is preserved verbatim from source.
    - Unlike TC1 (where ``ordr_prc`` / ``cndt_ordr_prc`` are float and
      ``ordr_q`` is int), TC2 declares all of them as ``str`` in source —
      preserved verbatim. Stringified-numeric scale not declared.
    - Rejection-reason code mapping (``rfsl_cd`` / ``text``) is not
      enumerated in the available source — described as "consume as
      returned by LS".
    - Account number placeholders use ``"12345678901"`` per safety policy.
    - ``examples`` for ``tr_key`` reflect the example script which omits
      it; response examples mirror typical LS WS payload shapes.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class TC2RealRequestHeader(BlockRealRequestHeader):
    """TC2 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class TC2RealResponseHeader(BlockRealResponseHeader):
    """TC2 real-time response header. Adds the response-side ``tr_cd`` echo."""
    tr_cd: str = Field(
        ...,
        title="거래 CD (TR code)",
        description="LS-side TR code echoed in the response header. Always 'TC2' for this stream.",
        examples=["TC2"],
    )


class TC2RealRequestBody(BaseModel):
    """TC2RealRequestBody — WebSocket subscription envelope for order-response push.

    TC2 is typically subscribed account-wide; ``tr_key`` is optional.
    """

    tr_cd: str = Field(
        default="TC2",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'TC2'.",
        examples=["TC2"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short futures symbol, optional)",
        description=(
            "Optional short overseas-futures contract symbol. May be left "
            "empty for account-wide subscription. Max 8 characters."
        ),
        examples=["", "ESZ25   "],
    )


class TC2RealRequest(BaseModel):
    """
    해외선물 주문응답 실시간 요청 (Overseas Futures Order Response — request envelope).
    """
    header: TC2RealRequestHeader = Field(
        TC2RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="TC2 WebSocket subscription header block (token + tr_type)."
    )
    body: TC2RealRequestBody = Field(
        ...,
        title="입력 데이터 블록 (Input body block)",
        description=(
            "해외선물 주문응답 input body — TR code and optional symbol key "
            "(account-wide subscription if omitted)."
        ),
    )


class TC2RealResponseBody(BaseModel):
    """TC2RealResponseBody — order-response push payload (confirm / reject).

    Carries WS line metadata, service-ID classifier (HO02 = confirm,
    HO03 = reject), order identifiers, account / symbol, side / new-modify-
    cancel classifier, order-type enum, prices (string), quantity (string),
    order time, exchange-side confirmation quantity, and rejection-reason
    fields populated for HO03 events.
    """

    lineseq: str = Field(
        ...,
        title="라인일련번호 (Line sequence number)",
        description="Line-level sequence number assigned by LS for the push frame.",
        examples=["1", "0001"],
    )
    key: str = Field(
        ...,
        title="KEY (LS-side push key)",
        description="LS-side push key associated with this event; consume as returned by LS.",
        examples=["12345678901"],
    )
    user: str = Field(
        ...,
        title="조작자ID (Operator ID)",
        description="Operator (user) ID that originated the order action.",
        examples=["USER01"],
    )
    svc_id: str = Field(
        ...,
        title="서비스ID (Service ID)",
        description=(
            "Service-ID classifier. 'HO02' = confirm (확인), 'HO03' = "
            "reject (거부)."
        ),
        examples=["HO02", "HO03"],
    )
    ordr_dt: str = Field(
        ...,
        title="주문일자 (Order date)",
        description="Order date in YYYYMMDD format.",
        examples=["20260506"],
    )
    brn_cd: str = Field(
        ...,
        title="지점번호 (Branch number)",
        description="LS branch number; consume as returned by LS.",
        examples=["001"],
    )
    ordr_no: str = Field(
        ...,
        title="주문번호 (Order number)",
        description="Assigned order number for this event, as a string.",
        examples=["100001"],
    )
    orgn_ordr_no: str = Field(
        ...,
        title="원주문번호 (Original order number)",
        description="Original order number this event references (0 / blank when not applicable).",
        examples=["0", "100001"],
    )
    mthr_ordr_no: str = Field(
        ...,
        title="모주문번호 (Parent order number)",
        description="Parent order number for grouped orders; consume as returned by LS.",
        examples=["0"],
    )
    ac_no: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number the event belongs to. Placeholder used in examples — never real.",
        examples=["12345678901"],
    )
    is_cd: str = Field(
        ...,
        title="종목코드 (Symbol / contract code)",
        description="Overseas-futures contract code for the order (root + expiry).",
        examples=["ESZ25", "NQU26"],
    )
    s_b_ccd: str = Field(
        ...,
        title="매도매수유형 (Sell/buy classifier)",
        description="Sell/buy classifier. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )
    ordr_ccd: str = Field(
        ...,
        title="정정취소유형 (New/modify/cancel classifier)",
        description="Order-action classifier. '1' = new (신규), '2' = modify (정정), '3' = cancel (취소).",
        examples=["1", "2", "3"],
    )
    ordr_typ_cd: Literal["1", "2", "3", "4"] = Field(
        ...,
        title="주문유형코드 (Order-type code)",
        description=(
            "Order-type code. '1' = market (시장가), '2' = limit (지정가), "
            "'3' = Stop Market, '4' = Stop Limit."
        ),
        examples=["1", "2", "3", "4"],
    )
    ordr_typ_prd_ccd: str = Field(
        ...,
        title="주문기간코드 (Order time-in-force / period code)",
        description=(
            "Order time-in-force / period code. Complete enum mapping not "
            "declared in available source; consume as returned by LS."
        ),
        examples=["0"],
    )
    ordr_aplc_strt_dt: str = Field(
        ...,
        title="주문적용시작일자 (Order effective start date)",
        description="Order effective start date in YYYYMMDD format.",
        examples=["20260506"],
    )
    ordr_aplc_end_dt: str = Field(
        ...,
        title="주문적용종료일자 (Order effective end date)",
        description="Order effective end date in YYYYMMDD format.",
        examples=["20260506"],
    )
    ordr_prc: str = Field(
        ...,
        title="주문가격 (Order price)",
        description=(
            "Order price in the contract's quote currency. Returned as a "
            "string — decimal scale and tick semantics not declared in "
            "available source."
        ),
        examples=["5025.25", "0"],
    )
    cndt_ordr_prc: str = Field(
        ...,
        title="주문조건가격 (Conditional / stop trigger price)",
        description=(
            "Conditional (stop) trigger price for Stop Market / Stop Limit "
            "orders, as a string; '0' for market / limit. Scale not declared."
        ),
        examples=["0", "5020.00"],
    )
    ordr_q: str = Field(
        ...,
        title="주문수량 (Order quantity)",
        description="Order quantity in contracts, as a string.",
        examples=["1", "5"],
    )
    ordr_tm: str = Field(
        ...,
        title="주문시간 (Order time)",
        description=(
            "Order time stamp. Format / time zone not declared in available "
            "source."
        ),
        examples=["093015"],
    )
    cnfr_q: str = Field(
        ...,
        title="호가확인수량 (Exchange confirmation quantity)",
        description=(
            "Quantity confirmed by the exchange for this order, as a string. "
            "Typically equals ``ordr_q`` on HO02 (confirm); meaning on HO03 "
            "(reject) consume as returned by LS."
        ),
        examples=["1", "0"],
    )
    rfsl_cd: str = Field(
        ...,
        title="호가거부사유코드 (Order reject reason code)",
        description=(
            "Exchange-side reject-reason code populated for HO03 events; "
            "blank otherwise. Code mapping not declared in available source; "
            "consume as returned by LS."
        ),
        examples=["", "0001"],
    )
    text: str = Field(
        ...,
        title="호가거부사유코드명 (Order reject reason text)",
        description=(
            "Human-readable reject-reason text matching ``rfsl_cd`` for "
            "HO03 events; blank for HO02. Text taxonomy not declared."
        ),
        examples=["", "INVALID PRICE"],
    )
    userid: str = Field(
        ...,
        title="사용자ID (User ID)",
        description="LS user ID associated with the order.",
        examples=["USER01"],
    )


class TC2RealResponse(BaseModel):
    header: Optional[TC2RealResponseHeader]
    body: Optional[TC2RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
