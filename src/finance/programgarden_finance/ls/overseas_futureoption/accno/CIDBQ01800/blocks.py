"""Pydantic models for LS Securities OpenAPI CIDBQ01800 (Overseas Futures Order History).

CIDBQ01800 returns the order history for overseas futures/options, including per-order
detail rows with execution status, pricing, modification/cancellation tracking, and
order classification metadata.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, and complete enum mappings are NOT declared in the
      source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ01800.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01800RequestHeader(BlockRequestHeader):
    """CIDBQ01800 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ01800ResponseHeader(BlockResponseHeader):
    """CIDBQ01800 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ01800InBlock1(BaseModel):
    """CIDBQ01800InBlock1 — input block for overseas futures order history query."""

    RecCnt: int = Field(
        default=1,
        title="Record count (레코드갯수)",
        description="Number of records in this request. LS examples use 1.",
        examples=[1],
    )

    IsuCodeVal: str = Field(
        ...,
        title="Issue code value (종목코드값)",
        description=(
            "Instrument code for the overseas futures/options symbol to query. "
            "From the example script: 'ADM23'. Length not declared in available source."
        ),
        examples=["ADM23", "ESM26", "NQU26"],
    )

    OrdDt: str = Field(
        ...,
        title="Order date (주문일자)",
        description="Query date for orders in YYYYMMDD format. From the example script: '20230609'.",
        examples=["20230609", "20260117"],
    )

    ThdayTpCode: str = Field(
        default="",
        title="Same-day type code (당일구분코드)",
        description=(
            "Same-day classification code. Pass empty string when not filtering by intraday. "
            "Full enum not declared in available source."
        ),
        examples=["", "1"],
    )

    OrdStatCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="Order status code (주문상태코드)",
        description="Order status filter. '0' = all (전체), '1' = executed (체결), '2' = unexecuted (미체결).",
        examples=["0", "1", "2"],
    )

    BnsTpCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction filter. '0' = all (전체), '1' = sell (매도), '2' = buy (매수).",
        examples=["0", "1", "2"],
    )

    QryTpCode: Literal["1", "2"] = Field(
        default="1",
        title="Query type code (조회구분코드)",
        description="Result ordering. '1' = reverse order (역순, newest first), '2' = forward order (정순, oldest first).",
        examples=["1", "2"],
    )

    OrdPtnCode: Literal["00", "01", "02", "03"] = Field(
        default="00",
        title="Order pattern code (주문유형코드)",
        description="Order type filter. '00' = all (전체), '01' = regular (일반), '02' = Average, '03' = Spread.",
        examples=["00", "01", "02", "03"],
    )

    OvrsDrvtFnoTpCode: Literal["A", "F", "O"] = Field(
        default="A",
        title="Overseas derivative futures/options type code (해외파생선물옵션구분코드)",
        description="Product type filter. 'A' = all (전체), 'F' = futures (선물), 'O' = options (옵션).",
        examples=["A", "F", "O"],
    )


class CIDBQ01800Request(BaseModel):
    """CIDBQ01800 full request envelope (header + body + setup options)."""

    header: CIDBQ01800RequestHeader = Field(
        CIDBQ01800RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ01800",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ01800InBlock1"], CIDBQ01800InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ01800InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ01800"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ01800OutBlock1(BaseModel):
    """CIDBQ01800OutBlock1 — input echo block with query summary.

    LS echoes the request inputs back including the resolved account number.
    The actual per-order records are in OutBlock2.
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

    Pwd: str = Field(
        default="",
        title="Account password (비밀번호)",
        description=(
            "Account password as echoed by LS. Treat as sensitive — avoid logging. "
            "Real production responses may mask or omit this value."
        ),
        examples=[""],
    )

    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Echoed instrument code.",
        examples=["ADM23", "ESM26"],
    )

    OrdDt: str = Field(
        default="",
        title="Order date (주문일자)",
        description="Echoed query date in YYYYMMDD format.",
        examples=["20230609", "20260117"],
    )

    ThdayTpCode: str = Field(
        default="",
        title="Same-day type code (당일구분코드)",
        description="Echoed same-day type code.",
        examples=["", "1"],
    )

    OrdStatCode: str = Field(
        default="",
        title="Order status code (주문상태코드)",
        description="Echoed order status filter. '0' = all, '1' = executed, '2' = unexecuted.",
        examples=["0", "1", "2"],
    )

    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Echoed trade direction filter. '0' = all, '1' = sell, '2' = buy.",
        examples=["0", "1", "2"],
    )

    QryTpCode: str = Field(
        default="",
        title="Query type code (조회구분코드)",
        description="Echoed result ordering. '1' = reverse, '2' = forward.",
        examples=["1", "2"],
    )

    OrdPtnCode: str = Field(
        default="",
        title="Order pattern code (주문유형코드)",
        description="Echoed order type filter. '00' = all, '01' = regular, '02' = Average, '03' = Spread.",
        examples=["00", "01", "02", "03"],
    )

    OvrsDrvtFnoTpCode: str = Field(
        default="",
        title="Overseas derivative futures/options type code (해외파생선물옵션구분코드)",
        description="Echoed product type filter. 'A' = all, 'F' = futures, 'O' = options.",
        examples=["A", "F", "O"],
    )


class CIDBQ01800OutBlock2(BaseModel):
    """CIDBQ01800OutBlock2 — per-order detail row (Occurs).

    One record per order (including modify/cancel records). Field length, decimal scale,
    and complete enum mappings are not declared in the source available to this codebase —
    consume as returned by LS.
    """

    OvrsFutsOrdNo: str = Field(
        default="",
        title="Overseas futures order number (해외선물주문번호)",
        description="LS-issued order number for the overseas futures order.",
        examples=["", "1234567"],
    )

    OvrsFutsOrgOrdNo: str = Field(
        default="",
        title="Overseas futures original order number (해외선물원주문번호)",
        description="Original order number for modify/cancel records. Empty for original orders.",
        examples=["", "1234567"],
    )

    FcmOrdNo: str = Field(
        default="",
        title="FCM order number (FCM주문번호)",
        description="FCM-assigned order number. Length not declared in available source.",
        examples=["", "FCM001"],
    )

    IsuCodeVal: str = Field(
        default="",
        title="Issue code value (종목코드값)",
        description="Instrument code for this order.",
        examples=["ADM23", "ESM26"],
    )

    IsuNm: str = Field(
        default="",
        title="Issue name (종목명)",
        description="Display name of the instrument.",
        examples=["E-MINI S&P500", "GOLD FUTURES"],
    )

    AbrdFutsXrcPrc: float = Field(
        default=0.0,
        title="Overseas futures exercise price (해외선물행사가격)",
        description=(
            "Strike / exercise price. 0 for futures contracts. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 5000.0],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description="FCM account number for this order.",
        examples=[""],
    )

    BnsTpCode: str = Field(
        default="",
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )

    BnsTpNm: str = Field(
        default="",
        title="Buy/sell type name (매매구분명)",
        description="Display name of the trade direction.",
        examples=["매도", "매수"],
    )

    FutsOrdStatCode: str = Field(
        default="",
        title="Futures order status code (선물주문상태코드)",
        description=(
            "Order status code. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["", "1", "2"],
    )

    TpCodeNm: str = Field(
        default="",
        title="Type code name (구분코드명)",
        description="Order classification name as returned by LS.",
        examples=["", "신규", "정정", "취소"],
    )

    FutsOrdTpCode: str = Field(
        default="",
        title="Futures order type code (선물주문구분코드)",
        description=(
            "Futures order classification code. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["", "01"],
    )

    TrdTpNm: str = Field(
        default="",
        title="Trade type name (거래구분명)",
        description="Trade processing step name as returned by LS.",
        examples=["", "주문", "접수", "체결"],
    )

    AbrdFutsOrdPtnCode: str = Field(
        default="",
        title="Overseas futures order type code (해외선물주문유형코드)",
        description="Order type code. '1' = market (시장가), '2' = limit (지정가). Other values may exist.",
        examples=["1", "2"],
    )

    OrdPtnNm: str = Field(
        default="",
        title="Order type name (주문유형명)",
        description="Display name of the order type.",
        examples=["시장가", "지정가", "Stop Market", "Stop Limit"],
    )

    OrdPtnTermTpCode: str = Field(
        default="",
        title="Order type term type code (주문유형기간구분코드)",
        description=(
            "Order validity period type code. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "0", "1"],
    )

    CmnCodeNm: str = Field(
        default="",
        title="Common code name (공통코드명)",
        description="Common classification name as returned by LS.",
        examples=["", "일반", "Spread"],
    )

    AppSrtDt: str = Field(
        default="",
        title="Application start date (적용시작일자)",
        description="Application start date in YYYYMMDD format.",
        examples=["", "20260117"],
    )

    AppEndDt: str = Field(
        default="",
        title="Application end date (적용종료일자)",
        description="Application end date in YYYYMMDD format.",
        examples=["", "20260117"],
    )

    OvrsDrvtOrdPrc: float = Field(
        default=0.0,
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Order price for the overseas futures/options. 0 for market orders. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 4500.25, 1900.0],
    )

    OrdQty: int = Field(
        default=0,
        title="Order quantity (주문수량)",
        description="Total order quantity (contracts).",
        examples=[0, 1, 10],
    )

    OvrsDrvtExecIsuCode: str = Field(
        default="",
        title="Overseas derivative executed issue code (해외파생체결종목코드)",
        description="Instrument code at execution. May differ from the order instrument for spread orders.",
        examples=["", "ADM23"],
    )

    ExecIsuNm: str = Field(
        default="",
        title="Executed issue name (체결종목명)",
        description="Display name of the executed instrument.",
        examples=["", "E-MINI S&P500"],
    )

    ExecBnsTpCode: str = Field(
        default="",
        title="Executed buy/sell type code (체결매매구분코드)",
        description="Trade direction at execution. '1' = sell, '2' = buy.",
        examples=["", "1", "2"],
    )

    ExecBnsTpNm: str = Field(
        default="",
        title="Executed buy/sell type name (체결매매구분명)",
        description="Display name of the executed trade direction.",
        examples=["", "매도", "매수"],
    )

    AbrdFutsExecPrc: float = Field(
        default=0.0,
        title="Overseas futures execution price (해외선물체결가격)",
        description=(
            "Execution price. Decimal scale not declared in available source."
        ),
        examples=[0.0, 4502.50, 1905.0],
    )

    ExecQty: int = Field(
        default=0,
        title="Executed quantity (체결수량)",
        description="Quantity that has been executed for this order.",
        examples=[0, 1, 10],
    )

    OrdCndiPrc: float = Field(
        default=0.0,
        title="Order condition price (주문조건가격)",
        description=(
            "Conditional price for stop orders. 0 when not applicable. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 4490.0],
    )

    OvrsDrvtNowPrc: float = Field(
        default=0.0,
        title="Overseas derivative current price (해외파생현재가)",
        description=(
            "Current market price at query time. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 4510.0],
    )

    MdfyQty: int = Field(
        default=0,
        title="Modified quantity (정정수량)",
        description="Quantity that has been modified.",
        examples=[0, 1],
    )

    CancQty: int = Field(
        default=0,
        title="Cancelled quantity (취소수량)",
        description="Quantity that has been cancelled.",
        examples=[0, 1],
    )

    RjtQty: int = Field(
        default=0,
        title="Rejected quantity (거부수량)",
        description="Quantity that has been rejected.",
        examples=[0, 1],
    )

    CnfQty: int = Field(
        default=0,
        title="Confirmed quantity (확인수량)",
        description="Confirmed quantity. Exact semantics not declared in available source.",
        examples=[0, 1],
    )

    UnercQty: int = Field(
        default=0,
        title="Unexecuted quantity (미체결수량)",
        description="Remaining unexecuted quantity for this order.",
        examples=[0, 1, 10],
    )

    CvrgYn: str = Field(
        default="",
        title="Hedge trade flag (반대매매여부)",
        description=(
            "Whether this is a covering (hedge/liquidation) trade. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "Y", "N"],
    )

    RegTmnlNo: str = Field(
        default="",
        title="Registered terminal number (등록단말번호)",
        description="Terminal number used to place the order.",
        examples=["", "001"],
    )

    RegBrnNo: str = Field(
        default="",
        title="Registered branch number (등록지점번호)",
        description="Branch number where the order was registered.",
        examples=["", "001"],
    )

    RegUserId: str = Field(
        default="",
        title="Registered user ID (등록사용자ID)",
        description="User ID that registered the order.",
        examples=["", "user01"],
    )

    OrdDt: str = Field(
        default="",
        title="Order date (주문일자)",
        description="Order placement date in YYYYMMDD format.",
        examples=["20230609", "20260117"],
    )

    OrdTime: str = Field(
        default="",
        title="Order time (주문시각)",
        description="Order placement time. Format and timezone not declared in available source.",
        examples=["", "093015"],
    )

    OvrsOptXrcRsvTpCode: str = Field(
        default="",
        title="Overseas option exercise reservation type code (해외옵션행사예약구분코드)",
        description=(
            "Option exercise reservation type. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "1"],
    )

    OvrsDrvtOptTpCode: str = Field(
        default="",
        title="Overseas derivative option type code (해외파생옵션구분코드)",
        description=(
            "Option type code (call/put etc.). "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "C", "P"],
    )

    SprdBaseIsuYn: str = Field(
        default="",
        title="Spread base issue flag (스프레드기준종목여부)",
        description="Whether this is the base instrument of a spread order.",
        examples=["", "Y", "N"],
    )

    OvrsFutsOrdDt: str = Field(
        default="",
        title="Overseas futures order date (해외선물주문일자)",
        description="Order date specifically as recorded by the overseas futures system in YYYYMMDD format.",
        examples=["", "20230609"],
    )

    OvrsFutsOrdNo2: str = Field(
        default="",
        title="Overseas futures order number 2 (해외선물주문번호2)",
        description="Secondary order number as returned by LS. Exact semantics not declared in available source.",
        examples=["", "1234568"],
    )

    OvrsFutsOrgOrdNo2: str = Field(
        default="",
        title="Overseas futures original order number 2 (해외선물원주문번호2)",
        description="Secondary original order number. Exact semantics not declared in available source.",
        examples=["", "1234567"],
    )

    OvrsDrvtIsuCode2: str = Field(
        default="",
        title="Overseas derivative issue code 2 (해외파생종목코드2)",
        description="Secondary instrument code (e.g., second leg of a spread). Empty when not applicable.",
        examples=["", "ADN23"],
    )


class CIDBQ01800Response(BaseModel):
    """CIDBQ01800 full response envelope."""

    header: Optional[CIDBQ01800ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ01800OutBlock1] = Field(
        None,
        title="First output block — query echo (첫번째 출력 블록)",
        description="Input echo block with resolved account and filter info.",
    )
    block2: List[CIDBQ01800OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-order detail rows (두번째 출력 블록 리스트)",
        description="Per-order detail rows. Ordering follows QryTpCode.",
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
