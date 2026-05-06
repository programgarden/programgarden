"""Pydantic models for LS Securities OpenAPI COSAQ00102 (Overseas Stock Account Order History).

COSAQ00102 returns the order history for an overseas stock account, including:

    - Per-account aggregated buy / sell execution amount and quantity (OutBlock2).
    - Per-order detail rows: order/execution time, price, quantity, instrument
      info, communication channel, currency, broker info, and loan flags
      (OutBlock3).

The TR supports server-side pagination via ``SrtOrdNo`` (start order number).
Use ``999999999`` to walk back from the most recent order (역순 / reverse) and
``0`` to walk forward from the earliest (정순 / forward).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses for AI chatbot
      Korean↔English mapping.
    - Field length, currency unit, decimal scale, and complete enum mappings
      are NOT declared in the source available to this codebase. Where the
      Korean spec uses "등" (etc.), the description states "consume as
      returned by LS" and does not invent additional enum values.
    - ``examples`` come from ``src/finance/example/overseas_stock/run_cosaq00102.py``
      where present, plus safe placeholder values (``"12345678901"`` for
      account numbers — never real accounts).
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAQ00102RequestHeader(BlockRequestHeader):
    """COSAQ00102 request header. Inherits the standard LS request header schema."""
    pass


class COSAQ00102ResponseHeader(BlockResponseHeader):
    """COSAQ00102 response header. Inherits the standard LS response header schema."""
    pass


class COSAQ00102InBlock1(BaseModel):
    """COSAQ00102InBlock1 — input block for overseas stock account order history.

    Use ``SrtOrdNo=999999999`` for the most recent orders (reverse order) and
    ``SrtOrdNo=0`` to start from the earliest (forward order). To paginate,
    take the smallest ``OrdNo`` returned in OutBlock3 and pass it back as
    ``SrtOrdNo`` on the next call (reverse mode).
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수 (Record count)",
        description="Number of records sent in this request. LS examples typically use 1.",
        examples=[1],
    )
    QryTpCode: Literal["1"] = Field(
        default="1",
        title="조회구분코드 (Query type code)",
        description="Query type. '1' = by account (계좌별). Only '1' is documented.",
        examples=["1"],
    )
    BkseqTpCode: str = Field(
        default="1",
        title="역순구분코드 (Reverse-order type code)",
        description=(
            "Result iteration direction. '1' = reverse order / 역순 (newest first), "
            "'2' = forward order / 정순 (oldest first)."
        ),
        examples=["1", "2"],
    )
    OrdMktCode: str = Field(
        default="81",
        title="주문시장코드 (Order market code)",
        description=(
            "Order market identifier. '81' = NYSE (뉴욕), '82' = NASDAQ (나스닥). "
            "The LS spec wording for this TR ends with '등' (etc.); additional "
            "exchange codes may exist server-side. Pass the value documented for "
            "your target market and consume the response code as returned by LS."
        ),
        examples=["81", "82"],
    )
    BnsTpCode: str = Field(
        default="0",
        title="매매구분코드 (Buy/sell type code)",
        description=(
            "Buy/sell filter. '0' = all (전체), '1' = sell (매도), '2' = buy (매수)."
        ),
        examples=["0", "1", "2"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue / symbol code)",
        description=(
            "Stock symbol code. Pass an empty string ('') to query across all "
            "symbols. Length not declared in available source."
        ),
        examples=["", "AAPL", "MSFT"],
    )
    SrtOrdNo: int = Field(
        default=999999999,
        title="시작주문번호 (Start order number)",
        description=(
            "Pagination cursor. Use 999999999 with ``BkseqTpCode='1'`` (reverse) "
            "to start from the most recent order; use 0 with ``BkseqTpCode='2'`` "
            "(forward) to start from the earliest. To paginate further, feed back "
            "an ``OrdNo`` returned in OutBlock3."
        ),
        examples=[0, 999999999],
    )
    OrdDt: str = Field(
        ...,
        title="주문일자 (Order date)",
        description=(
            "Query start date in YYYYMMDD format. Required. The TR returns "
            "orders placed on or related to this date (refer to LS spec for "
            "exact range semantics)."
        ),
        examples=["20260122", "20260201"],
    )
    ExecYn: str = Field(
        default="0",
        title="체결여부 (Execution status)",
        description=(
            "Execution filter. '0' = all (전체), '1' = executed (체결), "
            "'2' = unexecuted (미체결)."
        ),
        examples=["0", "1", "2"],
    )
    CrcyCode: str = Field(
        default="000",
        title="통화코드 (Currency code)",
        description=(
            "Currency filter. '000' = all (전체), 'USD' = U.S. dollar (미국). "
            "The LS spec wording ends with '등' (etc.); additional ISO-4217 "
            "currency codes may be accepted server-side."
        ),
        examples=["000", "USD"],
    )
    ThdayBnsAppYn: str = Field(
        default="0",
        title="당일매매적용여부 (Apply same-day trades flag)",
        description=(
            "Whether to include same-day (intraday) trades. '0' = exclude / "
            "미적용, '1' = include / 적용."
        ),
        examples=["0", "1"],
    )
    LoanBalHldYn: str = Field(
        default="0",
        title="대출잔고보유여부 (Loan balance hold filter)",
        description=(
            "Whether to restrict results to loan-balance positions. '0' = all "
            "(전체), '1' = loan-balance only (대출잔고만)."
        ),
        examples=["0", "1"],
    )


class COSAQ00102Request(BaseModel):
    """COSAQ00102 full request envelope (header + body + setup options)."""
    header: COSAQ00102RequestHeader = Field(
        COSAQ00102RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAQ00102",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 (Request header)",
        description="Request header block carrying tr_cd, authorization, and continuation flags.",
    )
    body: dict[Literal["COSAQ00102InBlock1"], COSAQ00102InBlock1] = Field(
        ...,
        title="입력 데이터 블록 (Input body)",
        description="Wrapped input block keyed by 'COSAQ00102InBlock1'.",
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=2,
            on_rate_limit="wait",
            rate_limit_key="COSAQ00102"
        ),
        title="설정 옵션 (Setup options)",
        description="Pre-execution setup options (rate limit, retry behavior).",
    )


class COSAQ00102OutBlock1(BaseModel):
    """COSAQ00102OutBlock1 — input echo block.

    LS echoes the InBlock1 inputs back in OutBlock1. Use this only for
    verification / continuation handling — the actual data rows live in
    OutBlock3 (per-order detail) and the aggregate summary in OutBlock2.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Echoed record count from the request.",
        examples=[0, 1],
    )
    QryTpCode: str = Field(
        default="",
        title="조회구분코드 (Query type code)",
        description="Echoed query type. '1' = by account.",
        examples=["1"],
    )
    BkseqTpCode: str = Field(
        default="",
        title="역순구분코드 (Reverse-order type code)",
        description="Echoed iteration direction. '1' = reverse, '2' = forward.",
        examples=["1", "2"],
    )
    OrdMktCode: str = Field(
        default="81",
        title="주문시장코드 (Order market code)",
        description="Echoed market code. '81' = NYSE, '82' = NASDAQ. Other LS-defined codes may appear.",
        examples=["81", "82"],
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
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드 (Buy/sell type code)",
        description="Echoed buy/sell filter. '0' = all, '1' = sell, '2' = buy.",
        examples=["0", "1", "2"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue / symbol code)",
        description="Echoed symbol code. Empty string means the request was unfiltered by symbol.",
        examples=["", "AAPL"],
    )
    SrtOrdNo: int = Field(
        default=0,
        title="시작주문번호 (Start order number)",
        description="Echoed pagination cursor.",
        examples=[0, 999999999],
    )
    OrdDt: str = Field(
        default="",
        title="주문일자 (Order date)",
        description="Echoed query date in YYYYMMDD format.",
        examples=["20260122"],
    )
    ExecYn: str = Field(
        default="",
        title="체결여부 (Execution status filter)",
        description="Echoed execution filter. '0' = all, '1' = executed, '2' = unexecuted.",
        examples=["0", "1", "2"],
    )
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Echoed currency filter. '000' = all, 'USD' = U.S. dollar, other LS-defined codes may appear.",
        examples=["000", "USD"],
    )
    ThdayBnsAppYn: str = Field(
        default="",
        title="당일매매적용여부 (Apply same-day trades flag)",
        description="Echoed same-day-trade flag. '0' = exclude, '1' = include.",
        examples=["0", "1"],
    )
    LoanBalHldYn: str = Field(
        default="",
        title="대출잔고보유여부 (Loan balance hold filter)",
        description="Echoed loan-balance filter. '0' = all, '1' = loan-balance only.",
        examples=["0", "1"],
    )


class COSAQ00102OutBlock2(BaseModel):
    """COSAQ00102OutBlock2 — account-level execution aggregate.

    Returns one record per account (request scope) summarising aggregated
    buy and sell executed amounts and quantities for the queried period.
    Currency unit and decimal scale are not declared in the source available
    to this codebase — consume the values as returned by LS.
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수 (Record count)",
        description="Record count for this aggregate block.",
        examples=[0, 1],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account name)",
        description="Display name of the account.",
        examples=["홍길동", "Test Account"],
    )
    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명 (Japan market Korean issue name)",
        description=(
            "Korean display name of the issue when the account holds a Japan-market "
            "instrument. Empty when not applicable."
        ),
        examples=["", "도요타자동차"],
    )
    MgmtBrnNm: str = Field(
        default="",
        title="관리지점명 (Managing branch name)",
        description="Display name of the managing branch for the account.",
        examples=["본점", "Test Branch"],
    )
    SellExecFcurrAmt: str = Field(
        default="",
        title="매도체결외화금액 (Sell-executed foreign-currency amount)",
        description=(
            "Aggregated sell-executed amount in foreign currency. LS returns this "
            "as a string. Currency depends on the request's ``CrcyCode`` and the "
            "instrument; decimal scale is not declared in available source."
        ),
        examples=["0", "1234.56"],
    )
    SellExecQty: int = Field(
        default=0,
        title="매도체결수량 (Sell-executed quantity)",
        description="Aggregated sell-executed share quantity.",
        examples=[0, 100],
    )
    BuyExecFcurrAmt: str = Field(
        default="",
        title="매수체결외화금액 (Buy-executed foreign-currency amount)",
        description=(
            "Aggregated buy-executed amount in foreign currency. LS returns this "
            "as a string. Currency depends on the request's ``CrcyCode`` and the "
            "instrument; decimal scale is not declared in available source."
        ),
        examples=["0", "1234.56"],
    )
    BuyExecQty: int = Field(
        default=0,
        title="매수체결수량 (Buy-executed quantity)",
        description="Aggregated buy-executed share quantity.",
        examples=[0, 100],
    )


class COSAQ00102OutBlock3(BaseModel):
    """COSAQ00102OutBlock3 — per-order detail row.

    One record per order (or order-modification / cancellation) within the
    requested window. Field length, decimal scale, and currency unit are not
    declared in the source available to this codebase — consume as returned
    by LS.
    """
    MgmtBrnNo: str = Field(
        default="",
        title="관리지점번호 (Managing branch number)",
        description="Branch identifier for the account.",
        examples=["001", "100"],
    )
    AcntNo: str = Field(
        default="",
        title="계좌번호 (Account number)",
        description="Account number for the order. Length not declared in available source.",
        examples=["12345678901"],
    )
    AcntNm: str = Field(
        default="",
        title="계좌명 (Account name)",
        description="Display name of the account.",
        examples=["홍길동"],
    )
    ExecTime: str = Field(
        default="",
        title="체결시각 (Execution time)",
        description=(
            "Execution time in HHMMSSmmm (hour-minute-second-millisecond). "
            "Empty when the order has not yet executed."
        ),
        examples=["", "093015123"],
    )
    OrdTime: str = Field(
        default="",
        title="주문시각 (Order time)",
        description="Order placement time in HHMMSSmmm format.",
        examples=["093001000"],
    )
    OrdNo: int = Field(
        default=0,
        title="주문번호 (Order number)",
        description="Order number (LS-issued numeric identifier).",
        examples=[0, 1234567],
    )
    OrgOrdNo: int = Field(
        default=0,
        title="원주문번호 (Original order number)",
        description=(
            "Original order number for modify/cancel records. 0 when this row "
            "represents the original order itself."
        ),
        examples=[0, 1234567],
    )
    ShtnIsuNo: str = Field(
        default="",
        title="단축종목번호 (Short issue code)",
        description="Short symbol code for the issue (e.g., 'AAPL', 'MSFT').",
        examples=["AAPL", "MSFT"],
    )
    OrdTrxPtnNm: str = Field(
        default="",
        title="주문처리유형명 (Order processing type name)",
        description="Display name of the order processing type as classified by LS.",
        examples=["접수", "체결"],
    )
    OrdTrxPtnCode: int = Field(
        default=0,
        title="주문처리유형코드 (Order processing type code)",
        description=(
            "Numeric code for the order processing type. Enum mapping not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[0, 1, 2],
    )
    MrcAbleQty: int = Field(
        default=0,
        title="정정취소가능수량 (Modify/cancel-able quantity)",
        description="Remaining quantity that can still be modified or cancelled.",
        examples=[0, 100],
    )
    OrdQty: int = Field(
        default=0,
        title="주문수량 (Order quantity)",
        description="Total order quantity (shares).",
        examples=[0, 100],
    )
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가 (Overseas order price)",
        description=(
            "Order price in the instrument's quote currency. Decimal scale not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 150.25],
    )
    ExecQty: int = Field(
        default=0,
        title="체결수량 (Executed quantity)",
        description="Quantity that has been executed so far for this order.",
        examples=[0, 100],
    )
    OvrsExecPrc: float = Field(
        default=0.0,
        title="해외체결가 (Overseas execution price)",
        description=(
            "Average execution price in the instrument's quote currency. "
            "Decimal scale not declared in available source."
        ),
        examples=[0.0, 150.25],
    )
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type / 호가유형 code. Enum mapping not declared in "
            "available source — consume as returned by LS."
        ),
        examples=["00", "03"],
    )
    OrdprcPtnNm: str = Field(
        default="",
        title="호가유형명 (Order-price type name)",
        description="Display name of the order-price type (e.g., limit / market).",
        examples=["지정가", "시장가"],
    )
    OrdPtnNm: str = Field(
        default="",
        title="주문유형명 (Order type name)",
        description="Display name of the order type as classified by LS.",
        examples=["신규매수", "신규매도"],
    )
    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드 (Order type code)",
        description=(
            "Order type code. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["00", "01"],
    )
    MrcTpCode: str = Field(
        default="",
        title="정정취소구분코드 (Modify/cancel type code)",
        description=(
            "Modify/cancel classification code. Enum mapping not declared in "
            "available source — consume as returned by LS."
        ),
        examples=["0", "1", "2"],
    )
    MrcTpNm: str = Field(
        default="",
        title="정정취소구분명 (Modify/cancel type name)",
        description="Display name of the modify/cancel classification.",
        examples=["", "정정", "취소"],
    )
    AllExecQty: int = Field(
        default=0,
        title="전체체결수량 (Total executed quantity)",
        description="Total executed quantity across this order's lifecycle.",
        examples=[0, 100],
    )
    CommdaCode: str = Field(
        default="",
        title="통신매체코드 (Communication medium code)",
        description=(
            "Code for the communication channel used to place the order. "
            "Enum mapping not declared in available source."
        ),
        examples=["00", "10"],
    )
    OrdMktCode: str = Field(
        default="",
        title="주문시장코드 (Order market code)",
        description="Order market code. '81' = NYSE, '82' = NASDAQ; other LS-defined codes may appear.",
        examples=["81", "82"],
    )
    MktNm: str = Field(
        default="",
        title="시장명 (Market name)",
        description="Display name of the order market.",
        examples=["뉴욕", "나스닥"],
    )
    CommdaNm: str = Field(
        default="",
        title="통신매체명 (Communication medium name)",
        description="Display name of the communication channel.",
        examples=["HTS", "API"],
    )
    JpnMktHanglIsuNm: str = Field(
        default="",
        title="일본시장한글종목명 (Japan market Korean issue name)",
        description="Korean display name of the issue when applicable to Japan market.",
        examples=["", "도요타자동차"],
    )
    UnercQty: int = Field(
        default=0,
        title="미체결수량 (Unexecuted quantity)",
        description="Remaining unexecuted quantity for this order.",
        examples=[0, 100],
    )
    CnfQty: int = Field(
        default=0,
        title="확인수량 (Confirmed quantity)",
        description="Confirmed quantity. Exact semantics not declared in available source.",
        examples=[0, 100],
    )
    CrcyCode: str = Field(
        default="",
        title="통화코드 (Currency code)",
        description="Order currency. 'USD' = U.S. dollar; other ISO-4217-style codes may appear.",
        examples=["USD", "JPY"],
    )
    RegMktCode: str = Field(
        default="",
        title="등록시장코드 (Listed market code)",
        description=(
            "Listed market code. Enum mapping not declared in available source — "
            "consume as returned by LS."
        ),
        examples=["81", "82"],
    )
    IsuNo: str = Field(
        default="",
        title="종목번호 (Issue / symbol code)",
        description="Symbol code for the order's issue.",
        examples=["AAPL", "MSFT"],
    )
    BrkTpCode: str = Field(
        default="",
        title="중개인구분코드 (Broker type code)",
        description=(
            "Broker classification code. Enum mapping not declared in "
            "available source."
        ),
        examples=["", "01"],
    )
    OppBrkNm: str = Field(
        default="",
        title="상대중개인명 (Counterparty broker name)",
        description="Display name of the counterparty broker (when reported).",
        examples=[""],
    )
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드 (Buy/sell type code)",
        description="Buy/sell side. '0' = all (filter only), '1' = sell, '2' = buy.",
        examples=["0", "1", "2"],
    )
    LoanDt: str = Field(
        default="",
        title="대출일자 (Loan date)",
        description="Loan date in YYYYMMDD format. Empty when not applicable.",
        examples=["", "20260101"],
    )
    LoanAmt: float = Field(
        default=0.0,
        title="대출금액 (Loan amount)",
        description=(
            "Loan amount in the order's currency. Decimal scale not declared in "
            "available source."
        ),
        examples=[0.0, 1000.0],
    )


class COSAQ00102Response(BaseModel):
    """COSAQ00102 full response envelope."""
    header: Optional[COSAQ00102ResponseHeader] = Field(
        None,
        title="응답 헤더 (Response header)",
        description="Response header block. None on transport / HTTP errors.",
    )
    block1: Optional[COSAQ00102OutBlock1] = Field(
        None,
        title="첫번째 출력 블록 (First output block — input echo)",
        description="Input echo block (mirrors the InBlock1 inputs).",
    )
    block2: Optional[COSAQ00102OutBlock2] = Field(
        None,
        title="두번째 출력 블록 (Second output block — account aggregate)",
        description="Account-level execution aggregate.",
    )
    block3: List[COSAQ00102OutBlock3] = Field(
        default_factory=list,
        title="세번째 출력 블록 리스트 (Third output block — per-order detail rows)",
        description="Per-order detail rows. Order ordering follows ``BkseqTpCode``.",
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
