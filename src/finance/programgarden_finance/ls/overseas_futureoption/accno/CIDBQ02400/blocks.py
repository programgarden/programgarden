"""Pydantic models for LS Securities OpenAPI CIDBQ02400 (Overseas Futures Order Execution Detail).

CIDBQ02400 returns detailed order and execution records for overseas futures/options over
a date range, including execution breakdown, commission components, and order classification.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into English.
      Korean source label is appended in parentheses for AI chatbot Korean↔English mapping.
    - Field length, decimal scale, currency unit, and complete enum mappings are NOT declared
      in the source available to this codebase. Where ambiguous, descriptions state
      "consume as returned by LS."
    - Commission fields (CsgnCmsn, FcmCmsn, ThcoCmsn, etc.) include positive and zero examples.
    - ``examples`` come from ``src/finance/example/overseas_futureoption/run_CIDBQ02400.py``
      where present, plus safe placeholder values ("12345678901" for account numbers).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ02400RequestHeader(BlockRequestHeader):
    """CIDBQ02400 request header. Inherits the standard LS request header schema."""
    pass


class CIDBQ02400ResponseHeader(BlockResponseHeader):
    """CIDBQ02400 response header. Inherits the standard LS response header schema."""
    pass


class CIDBQ02400InBlock1(BaseModel):
    """CIDBQ02400InBlock1 — input block for overseas futures order execution detail query."""

    IsuCodeVal: str = Field(
        ...,
        title="Issue code value (종목코드값)",
        description=(
            "Instrument code for the overseas futures/options symbol to query. "
            "From the example script: 'ADM23'. Length not declared in available source."
        ),
        examples=["ADM23", "ESM26", "NQU26"],
    )

    QrySrtDt: str = Field(
        ...,
        title="Query start date (조회시작일자)",
        description=(
            "Query start date in YYYYMMDD format. Used for historical queries. "
            "From the example script: '20230516'."
        ),
        examples=["20230516", "20260101"],
    )

    QryEndDt: str = Field(
        ...,
        title="Query end date (조회종료일자)",
        description=(
            "Query end date in YYYYMMDD format. Used for historical queries. "
            "From the example script: '20230609'."
        ),
        examples=["20230609", "20260131"],
    )

    ThdayTpCode: Literal["0", "1"] = Field(
        ...,
        title="Same-day type code (당일구분코드)",
        description="'0' = historical query (과거조회), '1' = same-day query (당일조회).",
        examples=["0", "1"],
    )

    OrdStatCode: Literal["0", "1", "2"] = Field(
        ...,
        title="Order status code (주문상태코드)",
        description="Order status filter. '0' = all (전체), '1' = executed (체결), '2' = unexecuted (미체결).",
        examples=["0", "1", "2"],
    )

    BnsTpCode: Literal["0", "1", "2"] = Field(
        ...,
        title="Buy/sell type code (매매구분코드)",
        description="Trade direction filter. '0' = all (전체), '1' = sell (매도), '2' = buy (매수).",
        examples=["0", "1", "2"],
    )

    QryTpCode: Literal["1", "2"] = Field(
        ...,
        title="Query type code (조회구분코드)",
        description="Result ordering. '1' = reverse order (역순, newest first), '2' = forward order (정순, oldest first).",
        examples=["1", "2"],
    )

    OrdPtnCode: Literal["00", "01", "02", "03"] = Field(
        ...,
        title="Order pattern code (주문유형코드)",
        description="Order type filter. '00' = all (전체), '01' = regular (일반), '02' = Average, '03' = Spread.",
        examples=["00", "01", "02", "03"],
    )

    OvrsDrvtFnoTpCode: Literal["A", "F", "O"] = Field(
        ...,
        title="Overseas derivative futures/options type code (해외파생선물옵션구분코드)",
        description="Product type filter. 'A' = all (전체), 'F' = futures (선물), 'O' = options (옵션).",
        examples=["A", "F", "O"],
    )


class CIDBQ02400Request(BaseModel):
    """CIDBQ02400 full request envelope (header + body + setup options)."""

    header: CIDBQ02400RequestHeader = Field(
        CIDBQ02400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ02400",
            tr_cont="N",
            tr_cont_key="",
            mac_address="",
        ),
        title="Request header (요청 헤더 데이터 블록)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["CIDBQ02400InBlock1"], CIDBQ02400InBlock1] = Field(
        ...,
        title="Input body (입력 데이터 블록)",
        description="Wrapped input block keyed by 'CIDBQ02400InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ02400"
        ),
        title="Setup options (설정 옵션)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class CIDBQ02400OutBlock1(BaseModel):
    """CIDBQ02400OutBlock1 — input echo block with query summary.

    LS echoes the request inputs back including the resolved account number.
    The actual per-order/execution records are in OutBlock2.
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

    QrySrtDt: str = Field(
        default="",
        title="Query start date (조회시작일자)",
        description="Echoed query start date in YYYYMMDD format.",
        examples=["20230516", "20260101"],
    )

    QryEndDt: str = Field(
        default="",
        title="Query end date (조회종료일자)",
        description="Echoed query end date in YYYYMMDD format.",
        examples=["20230609", "20260131"],
    )

    ThdayTpCode: str = Field(
        default="",
        title="Same-day type code (당일구분코드)",
        description="Echoed same-day flag. '0' = historical, '1' = same-day.",
        examples=["0", "1"],
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


class CIDBQ02400OutBlock2(BaseModel):
    """CIDBQ02400OutBlock2 — per-order/execution detail row (Occurs).

    One record per order or execution event. Field length, decimal scale, currency unit,
    and complete enum mappings are not declared in the source available to this codebase —
    consume as returned by LS.
    """

    OrdDt: str = Field(
        default="",
        title="Order date (주문일자)",
        description="Order placement date in YYYYMMDD format.",
        examples=["20230609", "20260117"],
    )

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
        description="FCM-assigned order number.",
        examples=["", "FCM001"],
    )

    ExecDt: str = Field(
        default="",
        title="Execution date (체결일자)",
        description="Execution date in YYYYMMDD format. Empty when the order has not executed.",
        examples=["", "20230609"],
    )

    OvrsFutsExecNo: str = Field(
        default="",
        title="Overseas futures execution number (해외선물체결번호)",
        description="LS-issued execution number. Empty for non-executed records.",
        examples=["", "7654321"],
    )

    FcmAcntNo: str = Field(
        default="",
        title="FCM account number (FCM계좌번호)",
        description="FCM account number for this order.",
        examples=[""],
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
        description="Order classification name as returned by LS (e.g., 신규, 정정, 취소).",
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
        examples=["", "주문", "접수", "확인", "체결", "소멸", "거부"],
    )

    AbrdFutsOrdPtnCode: str = Field(
        default="",
        title="Overseas futures order type code (해외선물주문유형코드)",
        description="Order type. '1' = market, '2' = limit. Other values may exist.",
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

    OrdQty: int = Field(
        default=0,
        title="Order quantity (주문수량)",
        description="Total order quantity (contracts).",
        examples=[0, 1, 10],
    )

    OvrsDrvtOrdPrc: float = Field(
        default=0.0,
        title="Overseas derivative order price (해외파생주문가격)",
        description=(
            "Order price. 0 for market orders. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 4500.25, 1900.0],
    )

    OvrsDrvtExecIsuCode: str = Field(
        default="",
        title="Overseas derivative executed issue code (해외파생체결종목코드)",
        description="Instrument code at execution. May differ for spread orders.",
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

    ExecQty: int = Field(
        default=0,
        title="Executed quantity (체결수량)",
        description="Executed quantity (contracts).",
        examples=[0, 1, 10],
    )

    AbrdFutsExecPrc: float = Field(
        default=0.0,
        title="Overseas futures execution price (해외선물체결가격)",
        description=(
            "Execution price. Decimal scale not declared in available source."
        ),
        examples=[0.0, 4502.50],
    )

    OrdCndiPrc: float = Field(
        default=0.0,
        title="Order condition price (주문조건가격)",
        description=(
            "Stop trigger price. 0 when not applicable. "
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

    UnercQty: int = Field(
        default=0,
        title="Unexecuted quantity (미체결수량)",
        description="Remaining unexecuted quantity.",
        examples=[0, 1, 10],
    )

    TrxStatCode: str = Field(
        default="",
        title="Processing status code (처리상태코드)",
        description=(
            "Transaction processing status code. "
            "Enum mapping not declared in available source — consume as returned by LS."
        ),
        examples=["", "0", "1"],
    )

    TrxStatCodeNm: str = Field(
        default="",
        title="Processing status code name (처리상태코드명)",
        description="Display name of the processing status.",
        examples=["", "처리완료"],
    )

    CsgnCmsn: float = Field(
        default=0.0,
        title="Consignment commission (위탁수수료)",
        description=(
            "Commission charged by LS for the consignment. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[5.0, 0.0],
    )

    FcmCmsn: float = Field(
        default=0.0,
        title="FCM commission (FCM수수료)",
        description=(
            "Commission charged by the FCM. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[2.0, 0.0],
    )

    ThcoCmsn: float = Field(
        default=0.0,
        title="Company commission (당사수수료)",
        description=(
            "Internal company commission. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[1.0, 0.0],
    )

    MdaCode: str = Field(
        default="",
        title="Media code (매체코드)",
        description="Channel/media code used to place the order.",
        examples=["", "00", "10"],
    )

    MdaCodeNm: str = Field(
        default="",
        title="Media code name (매체코드명)",
        description="Display name of the media/channel.",
        examples=["", "창구", "HTS"],
    )

    RegTmnlNo: str = Field(
        default="",
        title="Registered terminal number (등록단말번호)",
        description="Terminal number used to place the order.",
        examples=["", "001"],
    )

    RegUserId: str = Field(
        default="",
        title="Registered user ID (등록사용자ID)",
        description="User ID that registered the order.",
        examples=["", "user01"],
    )

    OrdSndDttm: str = Field(
        default="",
        title="Order send datetime (주문발송일시)",
        description="Order send datetime in YYYYMMDDHHMMSSsss format.",
        examples=["", "20230609093015000"],
    )

    ExecDttm: str = Field(
        default="",
        title="Execution datetime (체결일시)",
        description="Execution datetime in YYYYMMDDHHMMSSsss format. Empty for unexecuted orders.",
        examples=["", "20230609093016500"],
    )

    EufOneCmsnAmt: float = Field(
        default=0.0,
        title="Exchange fee 1 commission amount (거래소비용1수수료금액)",
        description=(
            "Exchange cost 1 fee. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 1.25],
    )

    EufTwoCmsnAmt: float = Field(
        default=0.0,
        title="Exchange fee 2 commission amount (거래소비용2수수료금액)",
        description=(
            "Exchange cost 2 fee. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.75],
    )

    LchOneCmsnAmt: float = Field(
        default=0.0,
        title="London clearing house 1 commission amount (런던청산소1수수료금액)",
        description=(
            "London clearing house cost 1. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.50],
    )

    LchTwoCmsnAmt: float = Field(
        default=0.0,
        title="London clearing house 2 commission amount (런던청산소2수수료금액)",
        description=(
            "London clearing house cost 2. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.25],
    )

    TrdOneCmsnAmt: float = Field(
        default=0.0,
        title="Trade 1 commission amount (거래1수수료금액)",
        description=(
            "Trade fee component 1. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.10],
    )

    TrdTwoCmsnAmt: float = Field(
        default=0.0,
        title="Trade 2 commission amount (거래2수수료금액)",
        description=(
            "Trade fee component 2. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.10],
    )

    TrdThreeCmsnAmt: float = Field(
        default=0.0,
        title="Trade 3 commission amount (거래3수수료금액)",
        description=(
            "Trade fee component 3. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.05],
    )

    StrmOneCmsnAmt: float = Field(
        default=0.0,
        title="Short-term 1 commission amount (단기1수수료금액)",
        description=(
            "Short-term fee component 1. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.05],
    )

    StrmTwoCmsnAmt: float = Field(
        default=0.0,
        title="Short-term 2 commission amount (단기2수수료금액)",
        description=(
            "Short-term fee component 2. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.05],
    )

    StrmThreeCmsnAmt: float = Field(
        default=0.0,
        title="Short-term 3 commission amount (단기3수수료금액)",
        description=(
            "Short-term fee component 3. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.05],
    )

    TransOneCmsnAmt: float = Field(
        default=0.0,
        title="Transfer 1 commission amount (전달1수수료금액)",
        description=(
            "Transfer fee component 1. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.02],
    )

    TransTwoCmsnAmt: float = Field(
        default=0.0,
        title="Transfer 2 commission amount (전달2수수료금액)",
        description=(
            "Transfer fee component 2. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.02],
    )

    TransThreeCmsnAmt: float = Field(
        default=0.0,
        title="Transfer 3 commission amount (전달3수수료금액)",
        description=(
            "Transfer fee component 3. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.02],
    )

    TransFourCmsnAmt: float = Field(
        default=0.0,
        title="Transfer 4 commission amount (전달4수수료금액)",
        description=(
            "Transfer fee component 4. "
            "Currency and decimal scale not declared in available source."
        ),
        examples=[0.0, 0.01],
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

    OvrsDrvtIsuCode2: str = Field(
        default="",
        title="Overseas derivative issue code 2 (해외파생종목코드2)",
        description="Secondary instrument code (e.g., second leg of a spread). Empty when not applicable.",
        examples=["", "ADN23"],
    )


class CIDBQ02400Response(BaseModel):
    """CIDBQ02400 full response envelope."""

    header: Optional[CIDBQ02400ResponseHeader] = Field(
        None,
        title="Response header (요청 헤더 데이터 블록)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[CIDBQ02400OutBlock1] = Field(
        None,
        title="First output block — query echo (첫번째 출력 블록)",
        description="Input echo block with resolved account and filter info.",
    )
    block2: List[CIDBQ02400OutBlock2] = Field(
        default_factory=list,
        title="Second output block — per-order/execution detail rows (두번째 출력 블록 리스트)",
        description="Per-order/execution detail rows. Ordering follows QryTpCode.",
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
