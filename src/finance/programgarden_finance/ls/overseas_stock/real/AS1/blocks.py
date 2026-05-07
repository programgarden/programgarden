"""Pydantic models for LS Securities OpenAPI AS1 (Overseas Stock Order Execution — US Markets).

AS1 is a Real-time WebSocket TR that pushes execution (fill) events for US-listed
overseas stocks. The ``AS1RealRequestBody`` carries only the WebSocket
subscription envelope (``tr_cd`` + ``tr_key``); the ``AS1RealResponseBody``
carries the per-fill push payload — a system / WS frame header followed by
execution-specific fields (``sExecQty`` / ``sExecPrc`` / running balances).

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and the
2026-05-06 finance TR field metadata plan):
    - Description text mirrors the LS Korean source labels translated into
      English. Korean source label is appended in parentheses.
    - Enum codes documented verbatim in the Korean source (``sOrdxctPtnCode``,
      ``sOrdPtnCode``, ``sBnsTp``) are listed exhaustively. Code classifiers
      without a declared enum mapping are described as "consume as returned
      by LS." rather than inferred.
    - Decimal scale / currency / time-zone are NOT declared in available
      source — examples are illustrative shapes (LS WS sample payload style).
    - Account number placeholders use ``"12345678901"`` — never real accounts.
    - ``examples`` mirror typical LS WS execution-push payload shapes.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class AS1RealRequestHeader(BlockRealRequestHeader):
    """AS1 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class AS1RealResponseHeader(BlockRealResponseHeader):
    """AS1 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class AS1RealRequestBody(BaseModel):
    """AS1RealRequestBody — WebSocket subscription envelope for execution push."""

    tr_cd: str = Field(
        default="AS1",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'AS1'.",
        examples=["AS1"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short symbol code)",
        description=(
            "Short symbol code (단축종목코드) used as the WS subscription key "
            "for the issue whose fill events are pushed. Up to 8 characters."
        ),
        examples=["AAPL", "TSLA"],
    )


class AS1RealRequest(BaseModel):
    """
    해외주식주문체결(미국) 실시간 요청 (Overseas Stock Order Execution — US, real-time request envelope).
    """
    header: AS1RealRequestHeader = Field(
        AS1RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록 (Request header block)",
        description="AS1 WebSocket subscription header block (token + tr_type)."
    )
    body: AS1RealRequestBody = Field(
        AS1RealRequestBody(
            tr_cd="AS1",
            tr_key=""
        ),
        title="입력 데이터 블록 (Input body block)",
        description="AS1 (overseas-stock order execution, US) input body — TR code and short symbol key.",
    )


class AS1RealResponseBody(BaseModel):
    """AS1RealResponseBody — execution push payload for a US overseas-stock symbol.

    Combines a system / WS frame header block (``lineseq`` … ``filler1``) with
    execution-specific fields (``sOrdxctPtnCode`` … ``sMgntrnCode``).
    """

    # ------------------------------------------------------------------
    # System / WS frame header fields (shared across AS0~AS4 push payloads)
    # ------------------------------------------------------------------
    lineseq: str = Field(
        ...,
        title="라인일련번호 (Line sequence number)",
        description="Line-level sequence number assigned by LS for the push frame.",
        examples=["1", "0001"],
    )
    accno: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number the event belongs to. Treat as PII; placeholder used in examples.",
        examples=["12345678901"],
    )
    user: str = Field(
        ...,
        title="조작자ID (Operator ID)",
        description="Operator (user) ID that originated the order action.",
        examples=["USER01"],
    )
    len: str = Field(
        ...,
        title="헤더길이 (Header length)",
        description="WS frame header length, as a fixed-width string.",
        examples=["0512"],
    )
    gubun: str = Field(
        ...,
        title="헤더구분 (Header classifier)",
        description="WS frame header classifier code; consume as returned by LS.",
        examples=["B"],
    )
    compress: str = Field(
        ...,
        title="압축구분 (Compression flag)",
        description="Compression flag for the WS frame; consume as returned by LS.",
        examples=["0"],
    )
    encrypt: str = Field(
        ...,
        title="암호구분 (Encryption flag)",
        description="Encryption flag for the WS frame; consume as returned by LS.",
        examples=["0"],
    )
    offset: str = Field(
        ...,
        title="공통시작지점 (Common start offset)",
        description="Common start offset within the WS frame; consume as returned by LS.",
        examples=["0000"],
    )
    trcode: str = Field(
        ...,
        title="TRCODE (TR code echo)",
        description="Echoed TR code identifying this push payload.",
        examples=["AS1"],
    )
    comid: str = Field(
        ...,
        title="이용사번호 (User-company number)",
        description="LS-assigned user-company / member-company number; consume as returned by LS.",
        examples=["001"],
    )
    userid: str = Field(
        ...,
        title="사용자ID (User ID)",
        description="LS user ID echoed in the push frame.",
        examples=["USER01"],
    )
    media: str = Field(
        ...,
        title="접속매체 (Connection medium)",
        description="Connection medium classifier (e.g., HTS / API); consume as returned by LS.",
        examples=["I"],
    )
    ifid: str = Field(
        ...,
        title="I/F일련번호 (I/F sequence number)",
        description="Interface-level sequence number for the push frame.",
        examples=["0001"],
    )
    seq: str = Field(
        ...,
        title="전문일련번호 (Telegram sequence number)",
        description="Per-telegram sequence number assigned by LS.",
        examples=["00000001"],
    )
    trid: str = Field(
        ...,
        title="TR추적ID (TR trace ID)",
        description="TR-level trace ID assigned by LS for diagnostic correlation.",
        examples=["0000001"],
    )
    pubip: str = Field(
        ...,
        title="공인IP (Public IP)",
        description="Public IP address LS assigns to the session.",
        examples=["203.0.113.1"],
    )
    prvip: str = Field(
        ...,
        title="사설IP (Private IP)",
        description="Private IP address recorded by LS.",
        examples=["10.0.0.1"],
    )
    pcbpno: str = Field(
        ...,
        title="처리지점번호 (Processing branch number)",
        description="LS processing branch number; consume as returned by LS.",
        examples=["001"],
    )
    bpno: str = Field(
        ...,
        title="지점번호 (Branch number)",
        description="LS branch number; consume as returned by LS.",
        examples=["001"],
    )
    termno: str = Field(
        ...,
        title="단말번호 (Terminal number)",
        description="LS terminal number; consume as returned by LS.",
        examples=["0001"],
    )
    lang: str = Field(
        ...,
        title="언어구분 (Language classifier)",
        description="Language classifier flag; consume as returned by LS.",
        examples=["K"],
    )
    proctm: str = Field(
        ...,
        title="AP처리시간 (AP processing time)",
        description="LS AP-side processing time stamp; format / scale not declared in available source.",
        examples=["120000"],
    )
    msgcode: str = Field(
        ...,
        title="메세지코드 (Message code)",
        description="Message / status code returned by LS for this frame.",
        examples=["00000"],
    )
    outgu: str = Field(
        ...,
        title="메세지출력구분 (Message output classifier)",
        description="Message output classifier; consume as returned by LS.",
        examples=["0"],
    )
    compreq: str = Field(
        ...,
        title="압축요청구분 (Compression request flag)",
        description="Compression request flag; consume as returned by LS.",
        examples=["0"],
    )
    funckey: str = Field(
        ...,
        title="기능키 (Function key)",
        description="Function-key field used by LS internally; consume as returned by LS.",
        examples=[" "],
    )
    reqcnt: str = Field(
        ...,
        title="요청레코드개수 (Request record count)",
        description="Number of request records associated with this frame.",
        examples=["0001"],
    )
    filler: str = Field(
        ...,
        title="예비영역 (Reserved area)",
        description="Reserved area; consume as returned by LS.",
        examples=[" "],
    )
    cont: str = Field(
        ...,
        title="연속구분 (Continuation flag)",
        description="Continuation flag; consume as returned by LS.",
        examples=["N"],
    )
    contkey: str = Field(
        ...,
        title="연속키값 (Continuation key value)",
        description="Continuation key value; consume as returned by LS.",
        examples=[""],
    )
    varlen: str = Field(
        ...,
        title="가변시스템길이 (Variable system length)",
        description="Variable-portion system length; consume as returned by LS.",
        examples=["0512"],
    )
    varhdlen: str = Field(
        ...,
        title="가변해더길이 (Variable header length)",
        description="Variable-portion header length; consume as returned by LS.",
        examples=["0064"],
    )
    varmsglen: str = Field(
        ...,
        title="가변메시지길이 (Variable message length)",
        description="Variable-portion message length; consume as returned by LS.",
        examples=["0512"],
    )
    trsrc: str = Field(
        ...,
        title="조회발원지 (Query origin)",
        description="Query-origin classifier; consume as returned by LS.",
        examples=["0"],
    )
    eventid: str = Field(
        ...,
        title="I/F이벤트ID (I/F event ID)",
        description="Interface event ID; consume as returned by LS.",
        examples=["0000"],
    )
    ifinfo: str = Field(
        ...,
        title="I/F정보 (I/F info)",
        description="Interface info field; consume as returned by LS.",
        examples=[""],
    )
    filler1: str = Field(
        ...,
        title="예비영역 (Reserved area)",
        description="Reserved area; consume as returned by LS.",
        examples=[""],
    )

    # ------------------------------------------------------------------
    # Execution-specific fields (AS1)
    # ------------------------------------------------------------------
    sOrdxctPtnCode: str = Field(
        ...,
        title="주문체결유형코드 (Order-execution-pattern code)",
        description=(
            "Order-event lifecycle code. '01' = new order accepted (신규매매접수), "
            "'03' = cancel order accepted (취소주문접수), '12' = modify completed (정정완료), "
            "'13' = cancel completed (취소완료), '14' = reject completed (거부완료)."
        ),
        examples=["01", "03", "12", "13", "14"],
    )
    sOrdMktCode: str = Field(
        ...,
        title="주문시장코드 (Order market code)",
        description=(
            "Order market code. Complete enum mapping not declared in available "
            "source; consume as returned by LS."
        ),
        examples=["81", "82"],
    )
    sOrdPtnCode: str = Field(
        ...,
        title="주문유형코드 (Order type code)",
        description="Order side. '01' = sell (매도), '02' = buy (매수).",
        examples=["01", "02"],
    )
    sMgmtBrnNo: str = Field(
        ...,
        title="관리지점번호 (Management branch number)",
        description="Management branch number; consume as returned by LS.",
        examples=["001"],
    )
    sAcntNo: str = Field(
        ...,
        title="계좌번호 (Account number)",
        description="Account number the fill belongs to. Placeholder used in examples — never real.",
        examples=["12345678901"],
    )
    sAcntNm: str = Field(
        ...,
        title="계좌명 (Account name)",
        description="Account holder name as recorded by LS.",
        examples=["홍길동"],
    )
    sIsuNo: str = Field(
        ...,
        title="종목번호 (Issue / symbol code)",
        description="LS-internal full issue code (typically exchange + ticker).",
        examples=["82AAPL"],
    )
    sIsuNm: str = Field(
        ...,
        title="종목명 (Issue name)",
        description="Issue name as recorded by LS.",
        examples=["애플"],
    )
    sOrdNo: int = Field(
        ...,
        title="주문번호 (Order number)",
        description="Order number this fill applies to.",
        examples=[231, 100001],
    )
    sOrgOrdNo: int = Field(
        ...,
        title="원주문번호 (Original order number)",
        description="Original order number when this fill amends a prior order (0 otherwise).",
        examples=[0, 231],
    )
    sExecNO: str = Field(
        ...,
        title="체결번호 (Execution number)",
        description="LS-assigned execution / fill number.",
        examples=["E0000001"],
    )
    sAbrdExecId: str = Field(
        ...,
        title="해외체결ID (Overseas execution ID)",
        description="Overseas-side execution identifier.",
        examples=[""],
    )
    sOrdQty: int = Field(
        ...,
        title="주문수량 (Order quantity)",
        description="Order quantity in shares.",
        examples=[1, 10],
    )
    sOrdPrc: float = Field(
        ...,
        title="주문가 (Order price)",
        description=(
            "Order price in the instrument's quote currency. Decimal scale not "
            "declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 180.5],
    )
    sExecQty: int = Field(
        ...,
        title="체결수량 (Execution quantity)",
        description="Quantity filled in this execution event.",
        examples=[0, 1],
    )
    sExecPrc: float = Field(
        ...,
        title="체결가 (Execution price)",
        description=(
            "Execution / fill price in the instrument's quote currency. Decimal "
            "scale not declared in available source — consume as returned by LS."
        ),
        examples=[0.0, 180.55],
    )
    sMdfyCnfQty: int = Field(
        ...,
        title="정정확인수량 (Modify-confirm quantity)",
        description="Quantity confirmed for a modify event.",
        examples=[0, 1],
    )
    sMdfyCnfPrc: float = Field(
        ...,
        title="정정확인가 (Modify-confirm price)",
        description="Price confirmed for a modify event.",
        examples=[0.0, 181.0],
    )
    sCancCnfQty: int = Field(
        ...,
        title="취소확인수량 (Cancel-confirm quantity)",
        description="Quantity confirmed for a cancel event.",
        examples=[0, 1],
    )
    sRjtQty: int = Field(
        ...,
        title="거부수량 (Reject quantity)",
        description="Quantity rejected.",
        examples=[0, 1],
    )
    sOrdTrxPtnCode: str = Field(
        ...,
        title="주문처리유형코드 (Order-transaction-pattern code)",
        description=(
            "Order-transaction-pattern code. Complete enum mapping not declared "
            "in available source; consume as returned by LS."
        ),
        examples=["00", "01"],
    )
    sMtiordSeqno: str = Field(
        ...,
        title="복수주문일련번호 (Multi-order sequence number)",
        description="Multi-order (basket) sequence number; consume as returned by LS.",
        examples=[""],
    )
    sOrdCndi: str = Field(
        ...,
        title="주문조건 (Order condition)",
        description="Order time-in-force / condition flag; consume as returned by LS.",
        examples=["0"],
    )
    sOrdprcPtnCode: str = Field(
        ...,
        title="호가유형코드 (Order-price-pattern code)",
        description=(
            "Order-price pattern code (limit / market / etc). Complete enum "
            "mapping not declared in available source; consume as returned by LS."
        ),
        examples=["00", "03"],
    )
    sShtnIsuNo: str = Field(
        ...,
        title="단축종목번호 (Short issue / ticker code)",
        description="Short symbol / ticker.",
        examples=["AAPL", "TSLA"],
    )
    sOpDrtnNo: str = Field(
        ...,
        title="운용지시번호 (Operation-directive number)",
        description="Operation-directive number; consume as returned by LS.",
        examples=[""],
    )
    sUnercQty: int = Field(
        ...,
        title="미체결수량(주문) (Unfilled order quantity)",
        description="Quantity unfilled on this order after this event.",
        examples=[0, 5],
    )
    sOrgOrdUnercQty: int = Field(
        ...,
        title="원주문미체결수량 (Original-order unfilled quantity)",
        description="Unfilled quantity remaining on the original order.",
        examples=[0, 5],
    )
    sOrgOrdMdfyQty: int = Field(
        ...,
        title="원주문정정수량 (Original-order modified quantity)",
        description="Quantity that has been modified on the original order.",
        examples=[0, 1],
    )
    sOrgOrdCancQty: int = Field(
        ...,
        title="원주문취소수량 (Original-order cancelled quantity)",
        description="Quantity cancelled from the original order.",
        examples=[0, 1],
    )
    sOrdAvrExecPrc: float = Field(
        ...,
        title="주문평균체결가 (Order-average execution price)",
        description="Volume-weighted average execution price for this order so far.",
        examples=[0.0, 180.55],
    )
    sOrdAmt: float = Field(
        ...,
        title="주문금액 (Order amount)",
        description="Order amount before fees. Currency / scale not declared in available source.",
        examples=[0.0, 180.5],
    )
    sStdIsuNo: str = Field(
        ...,
        title="표준종목번호 (Standard issue code)",
        description="Standardised (e.g., ISIN-style) issue code.",
        examples=["US0378331005"],
    )
    sBnsTp: str = Field(
        ...,
        title="매매구분 (Buy/sell classifier)",
        description="Buy/sell classifier. '1' = sell (매도), '2' = buy (매수).",
        examples=["1", "2"],
    )
    sCommdaCode: str = Field(
        ...,
        title="통신매체코드 (Communication-media code)",
        description="Communication media code; consume as returned by LS.",
        examples=["41"],
    )
    sOrdAcntNo: str = Field(
        ...,
        title="주문계좌번호 (Order account number)",
        description="Order-side account number. Placeholder used in examples — never real.",
        examples=["12345678901"],
    )
    sAgrgtBrnNo: str = Field(
        ...,
        title="집계지점번호 (Aggregation branch number)",
        description="Aggregation branch number; consume as returned by LS.",
        examples=["001"],
    )
    sRegMktCode: str = Field(
        ...,
        title="등록시장코드 (Registered market code)",
        description="Registered market code; consume as returned by LS.",
        examples=["81", "82"],
    )
    sMnyMgnRat: float = Field(
        ...,
        title="현금증거금률 (Cash margin rate)",
        description="Cash margin rate. Scale not declared in available source.",
        examples=[0.0, 100.0],
    )
    sSubstMgnRat: float = Field(
        ...,
        title="대용증거금률 (Substitute margin rate)",
        description="Substitute-collateral margin rate. Scale not declared in available source.",
        examples=[0.0],
    )
    sMnyExecAmt: float = Field(
        ...,
        title="현금체결금액 (Cash execution amount)",
        description="Cash component of the executed amount.",
        examples=[0.0, 180.55],
    )
    sSubstExecAmt: float = Field(
        ...,
        title="대용체결금액 (Substitute execution amount)",
        description="Substitute-collateral component of the executed amount.",
        examples=[0.0],
    )
    sCmsnAmtExecAmt: float = Field(
        ...,
        title="수수료체결금액 (Commission execution amount)",
        description="Commission component captured at execution.",
        examples=[0.0, 0.99],
    )
    sPrdayRuseExecVal: float = Field(
        ...,
        title="전일재사용체결금액 (Prior-day reuse execution amount)",
        description="Reuse-funds executed amount carried from prior day.",
        examples=[0.0],
    )
    sCrdayRuseExecVal: float = Field(
        ...,
        title="금일재사용체결금액 (Current-day reuse execution amount)",
        description="Reuse-funds executed amount within current day.",
        examples=[0.0],
    )
    sSpotExecQty: int = Field(
        ...,
        title="실물체결수량 (Spot execution quantity)",
        description="Spot-execution quantity in shares.",
        examples=[0, 1],
    )
    sStslExecQty: int = Field(
        ...,
        title="공매도체결수량 (Short-sale execution quantity)",
        description="Short-sale execution quantity in shares.",
        examples=[0],
    )
    sStrtgCode: str = Field(
        ...,
        title="전략코드 (Strategy code)",
        description="Strategy code attached to the order; consume as returned by LS.",
        examples=[""],
    )
    sGrpId: str = Field(
        ...,
        title="그룹ID (Group ID)",
        description="Group ID for batched orders; consume as returned by LS.",
        examples=[""],
    )
    sOrdSeqno: str = Field(
        ...,
        title="주문회차 (Order sequence)",
        description="Order sequence number; consume as returned by LS.",
        examples=["0"],
    )
    sOrdUserId: str = Field(
        ...,
        title="주문자ID (Order-user ID)",
        description="Order-user (placing employee) ID.",
        examples=["USER01"],
    )
    sExecTime: str = Field(
        ...,
        title="체결시각 (Execution time)",
        description="Execution time stamp. Format / time zone not declared in available source.",
        examples=["093015"],
    )
    sRcptExecTime: str = Field(
        ...,
        title="거래소수신체결시각 (Exchange-received execution time)",
        description="Time stamp at which the exchange-confirmed execution was received.",
        examples=["093015"],
    )
    sRjtRsn: str = Field(
        ...,
        title="거부사유 (Reject reason)",
        description="Reject reason text / code; empty when not rejected.",
        examples=[""],
    )
    sSecBalQty: int = Field(
        ...,
        title="잔고수량 (Holding quantity)",
        description="Position holding quantity for the symbol after the fill.",
        examples=[0, 10],
    )
    sSpotOrdAbleQty: int = Field(
        ...,
        title="실물주문가능수량 (Spot-orderable quantity)",
        description="Quantity available for spot ordering.",
        examples=[0, 10],
    )
    sOrdAbleRuseQty: int = Field(
        ...,
        title="주문가능재사용수량 (Reuse-orderable quantity)",
        description="Reusable quantity available for ordering.",
        examples=[0],
    )
    sFlctQty: int = Field(
        ...,
        title="변동수량 (Change quantity)",
        description="Net change in quantity caused by this fill.",
        examples=[0, 1, -1],
    )
    sSecBalQtyD2: int = Field(
        ...,
        title="잔고수량(D2) (D+2 holding quantity)",
        description="D+2 settled holding quantity for the symbol.",
        examples=[0, 10],
    )
    sSellAbleQty: int = Field(
        ...,
        title="매도주문가능수량 (Sell-orderable quantity)",
        description="Quantity currently available to sell.",
        examples=[0, 10],
    )
    sUnercSellOrdQty: int = Field(
        ...,
        title="미체결매도주문수량 (Unfilled sell-order quantity)",
        description="Sell-side quantity currently unfilled.",
        examples=[0, 5],
    )
    sAvrPchsPrc: float = Field(
        ...,
        title="평균매입가 (Average purchase price)",
        description="Average purchase price for the holding.",
        examples=[0.0, 175.0],
    )
    sPchsAmt: float = Field(
        ...,
        title="매입금액 (Purchase amount)",
        description="Total purchase amount for the holding.",
        examples=[0.0, 1750.0],
    )
    sDeposit: float = Field(
        ...,
        title="예수금 (Deposit / cash)",
        description="Account cash deposit balance after the event.",
        examples=[0.0, 10000.0],
    )
    sSubstAmt: float = Field(
        ...,
        title="대용금 (Substitute amount)",
        description="Substitute-collateral balance available on the account.",
        examples=[0.0],
    )
    sCsgnMnyMgn: float = Field(
        ...,
        title="위탁현금증거금액 (Consigned cash margin)",
        description="Consigned cash margin amount.",
        examples=[0.0],
    )
    sCsgnSubstMgn: float = Field(
        ...,
        title="위탁대용증거금액 (Consigned substitute margin)",
        description="Consigned substitute-collateral margin amount.",
        examples=[0.0],
    )
    sOrdAbleMny: float = Field(
        ...,
        title="주문가능현금 (Orderable cash)",
        description="Cash currently available for new orders.",
        examples=[0.0, 10000.0],
    )
    sOrdAbleSubstAmt: float = Field(
        ...,
        title="주문가능대용금액 (Orderable substitute amount)",
        description="Substitute collateral currently available for new orders.",
        examples=[0.0],
    )
    sRuseAbleAmt: float = Field(
        ...,
        title="재사용가능금액 (Reusable amount)",
        description="Reusable funds currently available.",
        examples=[0.0],
    )
    sMgntrnCode: str = Field(
        ...,
        title="신용거래코드 (Margin-trade code)",
        description=(
            "Margin / credit trade classifier. Complete enum mapping not "
            "declared in available source; consume as returned by LS."
        ),
        examples=["00", "01"],
    )


class AS1RealResponse(BaseModel):
    header: Optional[AS1RealResponseHeader]
    body: Optional[AS1RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
