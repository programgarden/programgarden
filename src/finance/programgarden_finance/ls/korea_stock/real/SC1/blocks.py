"""Pydantic models for LS Securities OpenAPI SC1 (Stock order execution push).

SC1 is a Real-time WebSocket TR that pushes per-event notifications when
a stock order is executed (filled).  Subscription is account-keyed
(``tr_type='1'`` to register, ``'2'`` to unregister); a single SC0..SC4
registration enables all five order-event streams.

The ``SC1RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + optional ``tr_key`` — order events are account-scoped, so
``tr_key`` is typically left blank).  The ``SC1RealResponseBody`` is
also reused (via inheritance) by:

    * ``SC2RealResponseBody`` — modify-confirm (ordxctptncode='12')
    * ``SC3RealResponseBody`` — cancel-confirm  (ordxctptncode='13')
    * ``SC4RealResponseBody`` — order-reject    (ordxctptncode='14')

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - LS-source-declared enums are preserved verbatim:
        * ``ordxctptncode`` (01=주문 / 02=정정 / 03=취소 / 11=체결 /
          12=정정확인 / 13=취소확인 / 14=거부);
        * ``trcode`` (SONAT000=신규 / SONAT001=정정 / SONAT002=취소 /
          SONAS100=체결확인);
        * ``ordprcptncode`` (00=지정가 / 03=시장가);
        * ``ordtrdptncode`` (00=위탁 / 01=신용 / 04=선물대용);
        * ``ordmktcode`` (10=KOSPI / 20=KOSDAQ);
        * ``ordptncode`` (01=현금매도 / 02=현금매수);
        * ``ordcndi`` (0=없음 / 1=IOC / 2=FOK);
        * ``mgntrncode`` (000=보통);
        * ``cvrgordtp`` (0=일반 / 1=자동 / 2=지점 / 3=예비주문본주문);
        * ``bnstp`` (1=매도 / 2=매수);
    - Other flag / code fields are not declared as a complete enum in
      the available source — consume as returned by LS.
    - Several balance / position fields are flagged "실서버 미제공" (not
      provided on the live server) in the Korean source — preserved
      verbatim in ``description``.
    - ``shtnIsuno`` 'A' + 7-digit (stocks) / 'J' + 7-digit (ELW) prefix
      convention is preserved verbatim.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class SC1RealRequestHeader(BlockRealRequestHeader):
    """SC1 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class SC1RealResponseHeader(BlockRealResponseHeader):
    """SC1 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class SC1RealRequestBody(BaseModel):
    """SC1RealRequestBody — WebSocket subscription envelope for stock order execution push."""

    tr_cd: str = Field(
        default="SC1",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'SC1'.",
        examples=["SC1"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short symbol code, optional)",
        description=(
            "Optional short symbol code. SC0..SC4 subscriptions are "
            "account-scoped (``tr_type='1'``) so this is typically left "
            "blank — LS does not require a per-symbol key for order-event "
            "registration."
        ),
        examples=["", "005930"],
    )


class SC1RealRequest(BaseModel):
    """SC1 (stock-order execution) real-time subscription request.

    Use ``tr_type='1'`` to register the account, ``'2'`` to unregister.
    """
    header: SC1RealRequestHeader = Field(
        SC1RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더 (Request header)",
        description="SC1 WebSocket subscription header block (token + tr_type; tr_type='1' register account / '2' unregister)."
    )
    body: SC1RealRequestBody = Field(
        SC1RealRequestBody(tr_cd="SC1", tr_key=""),
        title="요청 바디 (Request body)",
        description="SC1 input body — TR code 'SC1' for stock-order execution events; tr_key empty (account-level subscription)."
    )


class SC1RealResponseBody(BaseModel):
    """SC1RealResponseBody — stock order execution push payload (~130 fields).

    Inherited by SC2 / SC3 / SC4 RealResponseBody.  ``ordxctptncode`` value
    differentiates the subtype: '11'=fill, '12'=modify-confirm,
    '13'=cancel-confirm, '14'=reject.
    """

    grpId: str = Field(..., title="그룹Id (Group ID)", description="Group ID for batched order tracking.", examples=[""])
    trchno: str = Field(..., title="트렌치번호 (Tranche number)", description="Tranche number.", examples=[""])
    trtzxLevytp: str = Field(..., title="거래세징수구분 (Trade-tax levy code)", description="Trade-tax levy code — consume as returned by LS.", examples=[""])
    ordtrxptncode: str = Field(..., title="주문처리유형코드 (Order-handling type code)", description="Order-handling type code — consume as returned by LS.", examples=[""])
    acntnm: str = Field(..., title="계좌명 (Account name)", description="Account name.", examples=[""])
    trcode: str = Field(
        ...,
        title="TRCODE (TR code)",
        description=(
            "TR code that originated this event. LS-source-declared values: "
            "'SONAT000'=신규, 'SONAT001'=정정, 'SONAT002'=취소, "
            "'SONAS100'=체결확인."
        ),
        examples=["SONAT000", "SONAT001", "SONAT002", "SONAS100"],
    )
    userid: str = Field(..., title="사용자ID (User ID)", description="User ID.", examples=[""])
    agrgbrnno: str = Field(..., title="집계지점번호 (Aggregation branch number)", description="Aggregation branch number.", examples=[""])
    regmktcode: str = Field(..., title="등록시장코드 (Registered market code)", description="Registered market code — consume as returned by LS.", examples=[""])
    len: str = Field(..., title="헤더길이 (Header length)", description="Length of the header section.", examples=[""])
    opdrtnno: str = Field(..., title="운용지시번호 (Operation directive number)", description="Operation directive number.", examples=[""])
    orgordmdfyqty: str = Field(..., title="원주문정정수량 (Parent modified quantity)", description="Parent order modified quantity.", examples=["0"])
    avrpchsprc: str = Field(..., title="평균매입가 (Average purchase price, 실서버 미제공)", description="Average purchase price. Not provided on the live server — preserved verbatim.", examples=["0"])
    exectime: str = Field(..., title="체결시각 (Fill time)", description="Fill timestamp in HHMMSSMMM format.", examples=["091532123"])
    cont: str = Field(..., title="연속구분 (Continuation flag)", description="Continuation flag — consume as returned by LS.", examples=[""])
    mnymgnrat: str = Field(..., title="현금증거금률 (Cash margin rate)", description="Cash margin rate.", examples=[""])
    mdfycnfqty: str = Field(..., title="정정확인수량 (Modify-confirm quantity)", description="Confirmed quantity for a modify event (relevant for ordxctptncode='12').", examples=["0", "10"])
    orgordcancqty: str = Field(..., title="원주문취소수량 (Parent cancelled quantity)", description="Parent order cancelled quantity.", examples=["0"])
    compress: str = Field(..., title="압축구분 (Compression flag)", description="Compression flag.", examples=[""])
    execprc: str = Field(..., title="체결가격 (Fill price)", description="Fill price for this event. Decimal scale not declared.", examples=["73500"])
    mdfycnfprc: str = Field(..., title="정정확인가격 (Modify-confirm price)", description="Confirmed price for a modify event.", examples=["0", "73600"])
    unercsellordqty: str = Field(..., title="미체결매도주문수량 (Unfilled sell-order quantity, 실서버 미제공)", description="Unfilled sell-order quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    cmsnamtexecamt: str = Field(..., title="수수료체결금액 (Commission fill amount)", description="Commission portion of the fill amount.", examples=["0"])
    ruseableamt: str = Field(..., title="재사용가능금액 (Reusable amount)", description="Reusable amount for subsequent orders.", examples=["0"])
    gubun: str = Field(..., title="헤더구분 (Header type code)", description="Header type code — consume as returned by LS.", examples=[""])
    trid: str = Field(..., title="TR추적ID (TR trace ID)", description="TR tracing ID.", examples=[""])
    flctqty: str = Field(..., title="변동수량 (Delta quantity)", description="Delta quantity for this event.", examples=["10"])
    execno: str = Field(..., title="체결번호 (Fill number)", description="Fill number assigned by LS.", examples=["1234567"])
    lptp: str = Field(..., title="유동성공급자구분 (Liquidity-provider code)", description="LP code — consume as returned by LS.", examples=[""])
    varmsglen: str = Field(..., title="가변메시지길이 (Variable message length)", description="Variable message length.", examples=[""])
    ordno: str = Field(..., title="주문번호 (Order number)", description="Order number assigned by LS.", examples=["1234567"])
    futsmkttp: str = Field(..., title="선물시장구분 (Futures market code)", description="Futures market code — consume as returned by LS.", examples=[""])
    crdtexecamt: str = Field(..., title="신용체결금액 (Credit fill amount)", description="Credit-trade fill amount.", examples=["0"])
    deposit: str = Field(..., title="예수금 (Deposit balance)", description="Deposit balance.", examples=["10000000"])
    frgrunqno: str = Field(..., title="외국인고유번호 (Foreign-investor unique number)", description="Foreign-investor unique number.", examples=[""])
    crdayruseexecval: str = Field(..., title="금일재사용체결금액 (Same-day reuse fill amount)", description="Same-day reuse fill amount.", examples=["0"])
    trsrc: str = Field(..., title="조회발원지 (Query origin)", description="Query origin code.", examples=[""])
    ordacntno: str = Field(..., title="주문계좌번호 (Order account number)", description="Order account number.", examples=["12345678901"])
    reqcnt: str = Field(..., title="요청레코드개수 (Request record count)", description="Request record count.", examples=[""])
    shtnIsuno: str = Field(
        ...,
        title="단축종목번호 (Short symbol code with prefix)",
        description=(
            "Short symbol code with prefix. LS-source-declared convention: "
            "stock = 'A' + 6-digit code; ELW = 'J' + 6-digit code."
        ),
        examples=["A005930", "A035420"],
    )
    accno1: str = Field(..., title="계좌번호 (Account number)", description="Account number.", examples=["12345678901"])
    strtgcode: str = Field(..., title="전략코드 (Strategy code)", description="Strategy code — consume as returned by LS.", examples=[""])
    ordseqno: str = Field(..., title="주문회차 (Order sequence)", description="Order sequence within parent order.", examples=["1"])
    Isunm: str = Field(..., title="종목명 (Symbol name)", description="Symbol name in Korean.", examples=["삼성전자"])
    ordablesubstamt: str = Field(..., title="주문가능대용 (Orderable substitute)", description="Substitute collateral available for order.", examples=["0"])
    encrypt: str = Field(..., title="암호구분 (Encryption flag)", description="Encryption flag.", examples=[""])
    Isuno: str = Field(..., title="종목번호 (Standard symbol code, 12 chars)", description="Standard 12-character symbol code (e.g. 'KR7005930003').", examples=["KR7005930003"])
    accno2: str = Field(..., title="계좌번호 (Sub-account number)", description="Sub-account number suffix.", examples=[""])
    contkey: str = Field(..., title="연속키값 (Continuation key)", description="Continuation key value.", examples=[""])
    Loandt: str = Field(..., title="대출일 (Loan date)", description="Loan date in YYYYMMDD format.", examples=["", "20260101"])
    seq: str = Field(..., title="전문일련번호 (Message sequence number)", description="Message frame sequence number.", examples=[""])
    lineseq: str = Field(..., title="라인일련번호 (Line sequence number)", description="Line sequence number.", examples=["1"])
    varlen: str = Field(..., title="가변시스템길이 (Variable system length)", description="Variable system length.", examples=[""])
    orduserId: str = Field(..., title="주문자Id (Order user ID)", description="Order-placing user ID.", examples=[""])
    mgmtbrnno: str = Field(..., title="관리지점번호 (Managing branch number)", description="Managing branch number.", examples=[""])
    rjtqty: str = Field(..., title="거부수량 (Reject quantity)", description="Rejected quantity (relevant for ordxctptncode='14').", examples=["0", "10"])
    ordprcptncode: str = Field(
        ...,
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type code. LS-source-declared values: '00'=지정가, "
            "'03'=시장가. Other LS-defined codes may appear."
        ),
        examples=["00", "03"],
    )
    stdIsuno: str = Field(..., title="표준종목번호 (Standard symbol code, 12 chars)", description="Standard 12-character symbol code.", examples=["KR7005930003"])
    pchsant: str = Field(..., title="매입금액 (Purchase amount, 실서버 미제공)", description="Purchase amount. Not provided on the live server — preserved verbatim.", examples=["0"])
    filler: str = Field(..., title="예비영역 (Reserved filler)", description="Reserved filler region.", examples=[""])
    secbalqty: str = Field(..., title="잔고수량 (Balance quantity, 실서버 미제공)", description="Balance quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    ordxctptncode: str = Field(
        ...,
        title="주문체결유형코드 (Order / fill subtype code)",
        description=(
            "Order / fill subtype code. LS-source-declared values: "
            "'01'=주문, '02'=정정, '03'=취소, '11'=체결, '12'=정정확인, "
            "'13'=취소확인, '14'=거부."
        ),
        examples=["11", "12", "13", "14"],
    )
    canccnfqty: str = Field(..., title="취소확인수량 (Cancel-confirm quantity)", description="Confirmed quantity for a cancel event (ordxctptncode='13').", examples=["0", "10"])
    ordablemny: str = Field(..., title="주문가능현금 (Orderable cash)", description="Cash available for order.", examples=["10000000"])
    pubip: str = Field(..., title="공인IP (Public IP)", description="Public IP address.", examples=[""])
    prvip: str = Field(..., title="사설IP (Private IP)", description="Private IP address.", examples=[""])
    funckey: str = Field(..., title="기능키 (Function key)", description="Function key.", examples=[""])
    accno: str = Field(..., title="계좌번호 (Account number)", description="Account number.", examples=["12345678901"])
    compreq: str = Field(..., title="압축요청구분 (Compression request flag)", description="Compression request flag.", examples=[""])
    crdtpldgruseamt: str = Field(..., title="신용담보재사용금 (Credit collateral reuse amount)", description="Credit collateral reuse amount.", examples=["0"])
    ordamt: str = Field(..., title="주문금액 (Order amount)", description="Order amount.", examples=["735000"])
    termno: str = Field(..., title="단말번호 (Terminal number)", description="Terminal number.", examples=[""])
    crdtpldgexecamt: str = Field(..., title="신용담보체결금액 (Credit collateral fill amount)", description="Credit collateral fill amount.", examples=["0"])
    ordcndi: str = Field(
        ...,
        title="주문조건 (Order condition)",
        description="Order condition. LS-source-declared values: '0'=none, '1'=IOC, '2'=FOK.",
        examples=["0", "1", "2"],
    )
    rmndLoanamt: str = Field(..., title="잔여대출금액 (Remaining loan amount, 실서버 미제공)", description="Remaining loan amount. Not provided on the live server — preserved verbatim.", examples=["0"])
    bpno: str = Field(..., title="지점번호 (Branch number)", description="Branch number.", examples=[""])
    substamt: str = Field(..., title="대용금 (Substitute collateral)", description="Substitute collateral amount.", examples=["0"])
    mgempno: str = Field(..., title="관리사원번호 (Managing employee number)", description="Managing employee number.", examples=[""])
    csgnsubstmgn: str = Field(..., title="위탁증거금대용 (Consigned substitute margin)", description="Consigned substitute margin.", examples=["0"])
    offset: str = Field(..., title="공통시작지점 (Common section offset)", description="Offset where the common section starts.", examples=[""])
    rcptexectime: str = Field(..., title="거래소수신체결시각 (Exchange-received fill time)", description="Exchange-received fill timestamp in HHMMSSMMM format.", examples=["091532001"])
    sellableqty: str = Field(..., title="매도주문가능수량 (Sell-orderable quantity, 실서버 미제공)", description="Sell-orderable quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    spotexecqty: str = Field(..., title="실물체결수량 (Spot fill quantity)", description="Spot fill quantity (physical settlement).", examples=["0"])
    varhdlen: str = Field(..., title="가변해더길이 (Variable header length)", description="Variable header length.", examples=[""])
    substmgnrat: str = Field(..., title="대용증거금률 (Substitute margin rate)", description="Substitute margin rate.", examples=[""])
    ordavrexecprc: str = Field(..., title="주문평균체결가격 (Order average fill price)", description="Average fill price across the order's fills.", examples=["73500"])
    itemno: str = Field(..., title="아이템번호 (Item number)", description="Item number.", examples=[""])
    mgntrncode: str = Field(
        ...,
        title="신용거래코드 (Credit-trade code)",
        description=(
            "Credit-trade code. LS-source-declared value: '000'=보통. Other "
            "LS-defined codes may appear — consume as returned."
        ),
        examples=["000"],
    )
    nsavtrdqty: str = Field(..., title="비저축체결수량 (Non-savings fill quantity)", description="Non-savings fill quantity.", examples=["0"])
    ifinfo: str = Field(..., title="I/F정보 (I/F info)", description="Interface info string.", examples=[""])
    ordableruseqty: str = Field(..., title="재사용가능수량(매도) (Sell-side reuse-orderable quantity, 실서버 미제공)", description="Sell-side reuse-orderable quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    ptflno: str = Field(..., title="포트폴리오번호 (Portfolio number)", description="Portfolio number.", examples=[""])
    secbalqtyd2: str = Field(..., title="잔고수량(d2) (D+2 balance quantity, 실서버 미제공)", description="D+2 balance quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    brwmgmtYn: str = Field(..., title="차입관리여부 (Borrow management flag)", description="Borrow management flag.", examples=[""])
    eventid: str = Field(..., title="I/F이벤트ID (I/F event ID)", description="Interface event ID.", examples=[""])
    csgnmnymgn: str = Field(..., title="위탁증거금현금 (Consigned cash margin)", description="Consigned cash margin.", examples=["0"])
    pcbpno: str = Field(..., title="처리지점번호 (Processing branch number)", description="Processing branch number.", examples=[""])
    orgordno: str = Field(..., title="원주문번호 (Parent order number)", description="Original order number for modify / cancel events.", examples=["0", "1234567"])
    ifid: str = Field(..., title="I/F일련번호 (I/F sequence number)", description="Interface sequence number.", examples=[""])
    media: str = Field(..., title="접속매체 (Access medium)", description="Access medium code.", examples=[""])
    mtiordseqno: str = Field(..., title="복수주문일련번호 (Multi-order sequence)", description="Multi-order sequence within a batch.", examples=["0"])
    filler1: str = Field(..., title="예비영역 (Reserved filler)", description="Reserved filler region.", examples=[""])
    orgordunercqty: str = Field(..., title="원주문미체결수량 (Parent unfilled quantity)", description="Parent order unfilled quantity at the time of this event.", examples=["0", "10"])
    mbrnmbrno: str = Field(..., title="회원/비회원사번호 (Member / non-member firm number)", description="Member or non-member firm number.", examples=[""])
    futsLnkbrnno: str = Field(..., title="선물연계지점번호 (Futures-linked branch number)", description="Futures-linked branch number.", examples=[""])
    commdacode: str = Field(..., title="통신매체코드 (Comms-medium code)", description="Comms-medium code — consume as returned by LS.", examples=[""])
    stslexecqty: str = Field(..., title="공매도체결수량 (Short-sell fill quantity)", description="Short-sell fill quantity.", examples=["0"])
    proctm: str = Field(..., title="AP처리시간 (AP processing time)", description="AP processing time.", examples=[""])
    bfstdIsuno: str = Field(..., title="전표준종목번호 (Prior standard symbol code, 12 chars)", description="Prior 12-character standard symbol code.", examples=[""])
    futsLnkacntno: str = Field(..., title="선물연계계좌번호 (Futures-linked account number)", description="Futures-linked account number.", examples=[""])
    lang: str = Field(..., title="언어구분 (Language code)", description="Language code.", examples=[""])
    unercqty: str = Field(..., title="미체결수량(주문) (Unfilled quantity)", description="Unfilled quantity remaining on the order.", examples=["0", "90"])
    execqty: str = Field(..., title="체결수량 (Fill quantity)", description="Fill quantity for this event.", examples=["10"])
    adduptp: str = Field(..., title="수수료합산코드 (Commission-add-up code)", description="Commission-add-up code — consume as returned by LS.", examples=[""])
    bskno: str = Field(..., title="바스켓번호 (Basket number)", description="Basket number.", examples=[""])
    spotordableqty: str = Field(..., title="실물가능수량 (Spot-orderable quantity, 실서버 미제공)", description="Spot-orderable quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    ubstexecamt: str = Field(..., title="대용체결금액 (Substitute fill amount)", description="Substitute fill amount.", examples=["0"])
    cvrgordtp: str = Field(
        ...,
        title="반대매매주문구분 (Liquidation-order code)",
        description=(
            "Liquidation-order code. LS-source-declared values: '0'=일반, "
            "'1'=자동, '2'=지점, '3'=예비주문본주문."
        ),
        examples=["0", "1", "2", "3"],
    )
    ordqty: str = Field(..., title="주문수량 (Order quantity)", description="Order quantity.", examples=["10", "100"])
    mnyexecamt: str = Field(..., title="현금체결금액 (Cash fill amount)", description="Cash component of the fill amount.", examples=["735000"])
    outgu: str = Field(..., title="메세지출력구분 (Message output flag)", description="Message output flag.", examples=[""])
    msgcode: str = Field(..., title="메세지코드 (Message code)", description="Message code.", examples=[""])
    ordtrdptncode: str = Field(
        ...,
        title="주문거래유형코드 (Order trade-type code)",
        description=(
            "Order trade-type code. LS-source-declared values: '00'=위탁, "
            "'01'=신용, '04'=선물대용. Other LS-defined codes may appear."
        ),
        examples=["00", "01", "04"],
    )
    ordmktcode: str = Field(
        ...,
        title="주문시장코드 (Order market code)",
        description=(
            "Order market code. LS-source-declared values: '10'=KOSPI, "
            "'20'=KOSDAQ. Other LS-defined codes may appear."
        ),
        examples=["10", "20"],
    )
    ordptncode: str = Field(
        ...,
        title="주문유형코드 (Order pattern code)",
        description=(
            "Order pattern code. LS-source-declared values: '01'=현금매도, "
            "'02'=현금매수. Other LS-defined codes may appear."
        ),
        examples=["01", "02"],
    )
    prdayruseexecval: str = Field(..., title="전일재사용체결금액 (Prior-day reuse fill amount)", description="Prior-day reuse fill amount.", examples=["0"])
    comid: str = Field(..., title="COM ID / 이용사번호 (Service company number)", description="Service company number.", examples=[""])
    bnstp: str = Field(
        ...,
        title="매매구분 (Buy / sell side)",
        description="Buy / sell side. LS-source-declared values: '1'=sell, '2'=buy.",
        examples=["1", "2"],
    )
    user: str = Field(..., title="조작자ID (Operator user ID)", description="Operator user ID.", examples=[""])
    ordprc: str = Field(..., title="주문가격 (Order price)", description="Order price. Decimal scale not declared.", examples=["73500", "0"])


class SC1RealResponse(BaseModel):
    """SC1 (stock-order execution) real-time response.

    Complete response model for SC1 real-time stock order execution data.
    """
    header: Optional[SC1RealResponseHeader]
    body: Optional[SC1RealResponseBody]

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
