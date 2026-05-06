"""Pydantic models for LS Securities OpenAPI COSAQ01400 (Overseas Stock Reservation-Order History).

COSAQ01400 returns the processing-result history for reservation
(예약주문) orders placed against an overseas stock account, including
each reservation's order date, reserved order number, instrument,
quantity, price-type, status, and any error details (OutBlock2).

Use ``SrtDt`` / ``EndDt`` (YYYYMMDD) to bound the query window. Filter
by ``BnsTpCode`` (buy/sell), ``RsvOrdCndiCode`` (reservation condition),
and ``RsvOrdStatCode`` (reservation status) as required.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated
      into English. Korean source label is appended in parentheses for
      AI chatbot Korean↔English mapping.
    - Field length, currency unit, decimal scale, and complete enum
      mappings are NOT declared in the source available to this codebase.
      Where the Korean spec is silent the description states "consume
      as returned by LS" and does not invent additional values.
    - ``examples`` come from
      ``src/finance/example/overseas_stock/run_cosoq01400.py`` where
      present, plus safe placeholder values
      (``"12345678901"`` for account numbers — never real accounts).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAQ01400RequestHeader(BlockRequestHeader):
    """COSAQ01400 request header. Inherits the standard LS request header schema."""
    pass


class COSAQ01400ResponseHeader(BlockResponseHeader):
    """COSAQ01400 response header. Inherits the standard LS response header schema."""
    pass


class COSAQ01400InBlock1(BaseModel):
    """COSAQ01400InBlock1 — input block for overseas stock reservation-order history."""

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples typically use 1.",
        examples=[1],
    )
    QryTpCode: str = Field(
        default="1",
        title="조회구분코드 (Query type code)",
        description=(
            "Query type. '1' = by account (계좌별). The LS spec documents only "
            "'1' for this TR; consume any other value as returned."
        ),
        examples=["1"],
    )
    CntryCode: str = Field(
        ...,
        title="국가코드 (Country code)",
        description=(
            "Country code (LS-internal numeric string). The LS spec for this TR "
            "does not publish a complete enum mapping in the source available to "
            "this codebase — pass the value documented for your target market "
            "(example uses '001') and consume the response code as returned by LS."
        ),
        examples=["001"],
    )
    SrtDt: str = Field(
        ...,
        title="시작일자 (Start date)",
        description="Query window start date in YYYYMMDD format. Required.",
        examples=["20251201", "20260101"],
    )
    EndDt: str = Field(
        ...,
        title="종료일자 (End date)",
        description="Query window end date in YYYYMMDD format. Required.",
        examples=["20260123", "20260131"],
    )
    BnsTpCode: str = Field(
        ...,
        title="매매구분코드 (Buy/sell type code)",
        description=(
            "Buy/sell filter. '0' = all (전체), '1' = sell (매도), '2' = buy (매수)."
        ),
        examples=["0", "1", "2"],
    )
    RsvOrdCndiCode: str = Field(
        ...,
        title="예약주문조건코드 (Reservation order condition code)",
        description=(
            "Reservation condition code (LS-internal). The example uses '00'. "
            "Complete enum mapping not declared in available source — consume as "
            "returned by LS."
        ),
        examples=["00"],
    )
    RsvOrdStatCode: str = Field(
        ...,
        title="예약주문상태코드 (Reservation order status code)",
        description=(
            "Reservation status code (LS-internal). The example uses '1'. "
            "Complete enum mapping not declared in available source — consume as "
            "returned by LS."
        ),
        examples=["1"],
    )


class COSAQ01400Request(BaseModel):
    """COSAQ01400 full request envelope (header + body + setup options)."""
    header: COSAQ01400RequestHeader = Field(
        COSAQ01400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAQ01400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["COSAQ01400InBlock1"], COSAQ01400InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSAQ01400InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAQ01400"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSAQ01400OutBlock1(BaseModel):
    """COSAQ01400OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1. Use this only for
    verification — the actual reservation rows live in OutBlock2.
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )
    QryTpCode: str = Field(
        default="1",
        title="조회구분코드 (Query type code)",
        description="Echoed query type. '1' = by account.",
        examples=["1"],
    )
    CntryCode: str = Field(
        default="",
        title="국가코드 (Country code)",
        description="Echoed country code from the request.",
        examples=["001"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Account number associated with the query. Length not declared in available source.",
        examples=["12345678901"],
    )
    Pwd: str = Field(
        default="",
        title="비밀번호 (Account password)",
        description=(
            "Account password as echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )
    SrtDt: str = Field(
        default="",
        title="시작일자 (Start date)",
        description="Echoed query start date in YYYYMMDD format.",
        examples=["20251201"],
    )
    EndDt: str = Field(
        default="",
        title="종료일자 (End date)",
        description="Echoed query end date in YYYYMMDD format.",
        examples=["20260123"],
    )
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드 (Buy/sell type code)",
        description="Echoed buy/sell filter. '0' = all, '1' = sell, '2' = buy.",
        examples=["0", "1", "2"],
    )
    RsvOrdCndiCode: str = Field(
        default="",
        title="예약주문조건코드 (Reservation order condition code)",
        description="Echoed reservation condition code.",
        examples=["00"],
    )
    RsvOrdStatCode: str = Field(
        default="",
        title="예약주문상태코드 (Reservation order status code)",
        description="Echoed reservation status code.",
        examples=["1"],
    )


class COSAQ01400OutBlock2(BaseModel):
    """COSAQ01400OutBlock2 — per-reservation detail row.

    One record per reservation order matching the query window and
    filters. Field length, decimal scale, and currency unit are not
    declared in the source available to this codebase — consume as
    returned by LS.
    """
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Account number for the reservation order.",
        examples=["12345678901"],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account name)",
        description="Display name of the account.",
        examples=["홍길동"],
    )
    OrdDt: str = Field(
        default="",
        title="주문일자 (Order date)",
        description="Order date in YYYYMMDD format.",
        examples=["20260120"],
    )
    OrdNo: int = Field(
        default=0,
        title="주문번호 (Order number)",
        description="Order number (LS-issued numeric identifier) for the executed order, if any.",
        examples=[0, 1234567],
    )
    RsvOrdInptDt: str = Field(
        default="",
        title="예약주문입력일자 (Reservation order input date)",
        description="Reservation input date in YYYYMMDD format.",
        examples=["20260119"],
    )
    RsvOrdNo: int = Field(
        default=0,
        title="예약주문번호 (Reservation order number)",
        description="Reservation order number (LS-issued numeric identifier).",
        examples=[0, 9001],
    )
    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호 (Short issue code)",
        description="Short symbol code for the issue (e.g., 'AAPL', 'MSFT').",
        examples=["AAPL", "MSFT"],
    )
    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명 (Japan market Korean issue name)",
        description="Korean display name of the issue when applicable to Japan market.",
        examples=["", "도요타자동차"],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Reservation order quantity (shares).",
        examples=[0, 100],
    )
    OrdprcPtnNm: str = Field(
        default="",
        title="호가유형명 (Order-price type name)",
        description="Display name of the order-price type (e.g., limit / market).",
        examples=["지정가", "시장가"],
    )
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가 (Overseas order price)",
        description=(
            "Reserved order price in the instrument's quote currency. Decimal "
            "scale not declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 150.25],
    )
    BnsTpNm: str = Field(
        default="",
        title="매매구분명 (Buy/sell type name)",
        description="Display name of the buy/sell side (e.g., '매도', '매수').",
        examples=["매도", "매수"],
    )
    ExecQty: int = Field(
        default=0,
        title="체결수량 (Executed quantity)",
        description="Quantity that has been executed for this reservation.",
        examples=[0, 100],
    )
    UnercQty: int = Field(
        default=0,
        title="미체결수량 (Unexecuted quantity)",
        description="Remaining unexecuted quantity for this reservation.",
        examples=[0, 100],
    )
    TotExecQty: int = Field(
        default=0,
        title="총체결수량 (Total executed quantity)",
        description="Total executed quantity across this reservation's lifecycle.",
        examples=[0, 100],
    )
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Order currency. 'USD' = U.S. dollar; other ISO-4217-style codes may appear.",
        examples=["USD", "JPY"],
    )
    RsvOrdStatCode: str = Field(
        default="",
        title="예약주문상태코드 (Reservation order status code)",
        description=(
            "Reservation status code as recorded for this row. Complete enum "
            "mapping not declared in available source — consume as returned by LS."
        ),
        examples=["1", "2"],
    )
    MktTpNm: str = Field(
        default="",
        title="시장구분명 (Market type name)",
        description="Display name of the market (e.g., '뉴욕', '나스닥').",
        examples=["뉴욕", "나스닥"],
    )
    ErrCnts: str = Field(
        default="",
        title="오류내용 (Error content)",
        description="Error description text when the reservation processing failed; empty otherwise.",
        examples=[""],
    )
    LoanDt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description="Loan date in YYYYMMDD format. Empty when not applicable.",
        examples=["", "20260101"],
    )
    MgntrnCode: str = Field(
        default="",
        title="신용거래코드 (Credit transaction code)",
        description=(
            "Credit (margin) transaction code. Enum mapping not declared in "
            "available source — consume as returned by LS."
        ),
        examples=["", "01"],
    )


class COSAQ01400Response(BaseModel):
    """COSAQ01400 full response envelope."""
    header: Optional[COSAQ01400ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSAQ01400OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors the InBlock1 inputs).",
    )
    block2: List[COSAQ01400OutBlock2] = Field(
        default_factory=list,
        title="두번째 출력 블록 리스트 (Second output block — per-reservation detail rows)",
        description="Per-reservation detail rows.",
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
