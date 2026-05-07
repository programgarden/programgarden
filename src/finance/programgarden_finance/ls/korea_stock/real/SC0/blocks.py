"""Pydantic models for LS Securities OpenAPI SC0 (Stock order acceptance push).

SC0 is a Real-time WebSocket TR that pushes per-event notifications when
a stock order (new / modify / cancel) is accepted by the exchange.
Subscription is account-keyed (``tr_type='1'`` to register, ``'2'`` to
unregister); a single SC0..SC4 registration enables all five
order-event streams.

The ``SC0RealRequestBody`` carries the WebSocket subscription envelope
(``tr_cd`` + optional ``tr_key`` — order events are account-scoped, so
``tr_key`` is typically left blank).  The ``SC0RealResponseBody``
combines two envelope sections preserved verbatim from the in-codebase
Korean source:

    1. **System header common fields** (~37 fields, ``lineseq`` …
       ``filler1``) — the standard LS WS frame header.
    2. **Order-specific fields** (~70 fields, ``ordchegb`` … ``ruseableamt``)
       — order acceptance details.

Field source policy (per CLAUDE.md ``feedback_no_inferred_formulas`` and
the 2026-05-06 finance TR field metadata plan):
    - Description text mirrors LS Korean source labels translated into
      English.  Korean source label is appended in parentheses inside
      ``title``.
    - LS-source-declared enums are preserved verbatim:
        * ``ordchegb`` (01=주문 / 02=정정 / 03=취소 / 11=체결 / 12=정정확인 /
          13=취소확인 / 14=거부 / A1=접수중 / AC=접수완료);
        * ``trcode`` (SONAT000=신규 / SONAT001=정정 / SONAT002=취소 /
          SONAS100=체결확인);
        * ``marketgb`` (10=KOSPI / 20=KOSDAQ / 23=KONEX);
        * ``ordgb`` (01=현금매도 / 02=현금매수 / 03=신용매도 / 04=신용매수);
        * ``hogagb`` (0=없음 / 1=IOC / 2=FOK);
        * ``etfhogagb`` (00=지정가 / 03=시장가 / 05=조건부지정가);
        * ``gmhogagb`` (0=일반 / 1=차입주식매도 / 2=기타공매도);
        * ``gmhogayn`` (0=일반 / 1=공매도);
        * ``cvrgordtp`` (0=일반 / 1=자동 / 2=지점 / 3=예비주문본주문);
        * ``lpgb`` (0=해당없음 / 1=유동성공급자);
        * ``bnstp`` (1=매도 / 2=매수);
    - Other flag / code fields (``pgmtype``, ``singb``, ``procgb``,
      ``futmarketgb``, ``tongsingb``, ``brwmgmyn``, ``mbrno``, …) are
      not declared as a complete enum in the available source —
      consume as returned by LS.
    - Several balance / position fields are flagged "실서버 미제공" (not
      provided on the live server) in the Korean source — preserved
      verbatim in ``description``.
    - ``shtcode`` prefix convention ('A' + 7-digit for stocks, 'J' +
      7-digit for ELW) is preserved verbatim.
    - Decimal scale and currency unit are NOT declared in the available
      source — examples use illustrative values only.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class SC0RealRequestHeader(BlockRealRequestHeader):
    """SC0 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class SC0RealResponseHeader(BlockRealResponseHeader):
    """SC0 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class SC0RealRequestBody(BaseModel):
    """SC0RealRequestBody — WebSocket subscription envelope for stock order acceptance push."""

    tr_cd: str = Field(
        default="SC0",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'SC0'.",
        examples=["SC0"],
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


class SC0RealRequest(BaseModel):
    """주식주문접수(SC0) 실시간 등록/해제 요청.

    Use ``tr_type='1'`` to register the account, ``'2'`` to unregister.
    A single SC0..SC4 registration enables all five order-event streams.
    """
    header: SC0RealRequestHeader = Field(
        SC0RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더 (Request header)",
        description="SC0 실시간 계좌등록/해제를 위한 헤더 블록"
    )
    body: SC0RealRequestBody = Field(
        SC0RealRequestBody(tr_cd="SC0", tr_key=""),
        title="요청 바디 (Request body)",
        description="주식주문접수 실시간 등록 바디"
    )


class SC0RealResponseBody(BaseModel):
    """SC0RealResponseBody — stock order acceptance push payload.

    System header (~37 fields, ``lineseq`` … ``filler1``) + order-specific
    fields (~70 fields, ``ordchegb`` … ``ruseableamt``) preserved verbatim
    from the in-codebase Korean source.
    """

    # ─── System header common fields ───
    lineseq: str = Field(..., title="라인일련번호 (Line sequence number)", description="Line sequence number assigned by LS.", examples=["1"])
    accno: str = Field(..., title="Push키 / 계좌번호 (Push key / account number)", description="Account number — used as the push subscription key.", examples=["12345678901"])
    user: str = Field(..., title="조작자ID (Operator user ID)", description="Operator user ID.", examples=[""])
    len: str = Field(..., title="헤더길이 (Header length)", description="Length of the header section.", examples=[""])
    gubun: str = Field(..., title="헤더구분 (Header type code)", description="Header type code — consume as returned by LS.", examples=[""])
    compress: str = Field(..., title="압축구분 (Compression flag)", description="Compression flag — consume as returned by LS.", examples=[""])
    encrypt: str = Field(..., title="암호구분 (Encryption flag)", description="Encryption flag — consume as returned by LS.", examples=[""])
    offset: str = Field(..., title="공통시작지점 (Common section offset)", description="Offset where the common section starts.", examples=[""])
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
    comid: str = Field(..., title="이용사번호 (Service company number)", description="Service company number.", examples=[""])
    userid: str = Field(..., title="사용자ID (User ID)", description="User ID for the originating session.", examples=[""])
    media: str = Field(..., title="접속매체 (Access medium code)", description="Access medium code — consume as returned by LS.", examples=[""])
    ifid: str = Field(..., title="I/F일련번호 (I/F sequence number)", description="Interface sequence number.", examples=[""])
    seq: str = Field(..., title="전문일련번호 (Message sequence number)", description="Sequence number of the message frame.", examples=[""])
    trid: str = Field(..., title="TR추적ID (TR trace ID)", description="TR tracing ID.", examples=[""])
    pubip: str = Field(..., title="공인IP (Public IP)", description="Public IP address.", examples=[""])
    prvip: str = Field(..., title="사설IP (Private IP)", description="Private IP address.", examples=[""])
    pcbpno: str = Field(..., title="처리지점번호 (Processing branch number)", description="Processing branch number.", examples=[""])
    bpno: str = Field(..., title="지점번호 (Branch number)", description="Branch number.", examples=[""])
    termno: str = Field(..., title="단말번호 (Terminal number)", description="Terminal number.", examples=[""])
    lang: str = Field(..., title="언어구분 (Language code)", description="Language code — consume as returned by LS.", examples=[""])
    proctm: str = Field(..., title="AP처리시간 (AP processing time)", description="AP processing time.", examples=[""])
    msgcode: str = Field(..., title="메세지코드 (Message code)", description="Message code returned by LS.", examples=[""])
    outgu: str = Field(..., title="메세지출력구분 (Message output flag)", description="Message output flag — consume as returned by LS.", examples=[""])
    compreq: str = Field(..., title="압축요청구분 (Compression request flag)", description="Compression request flag.", examples=[""])
    funckey: str = Field(..., title="기능키 (Function key)", description="Function key.", examples=[""])
    reqcnt: str = Field(..., title="요청레코드개수 (Request record count)", description="Request record count.", examples=[""])
    filler: str = Field(..., title="예비영역 (Reserved filler 1)", description="Reserved filler region — consume as returned by LS.", examples=[""])
    cont: str = Field(..., title="연속구분 (Continuation flag)", description="Continuation flag — consume as returned by LS.", examples=[""])
    contkey: str = Field(..., title="연속키값 (Continuation key)", description="Continuation key value.", examples=[""])
    varlen: str = Field(..., title="가변시스템길이 (Variable system length)", description="Variable system length.", examples=[""])
    varhdlen: str = Field(..., title="가변해더길이 (Variable header length)", description="Variable header length.", examples=[""])
    varmsglen: str = Field(..., title="가변메시지길이 (Variable message length)", description="Variable message length.", examples=[""])
    trsrc: str = Field(..., title="조회발원지 (Query origin)", description="Query origin code — consume as returned by LS.", examples=[""])
    eventid: str = Field(..., title="I/F이벤트ID (I/F event ID)", description="Interface event ID.", examples=[""])
    ifinfo: str = Field(..., title="I/F정보 (I/F info)", description="Interface info string.", examples=[""])
    filler1: str = Field(..., title="예비영역 (Reserved filler 2)", description="Reserved filler region — consume as returned by LS.", examples=[""])

    # ─── Order-specific fields ───
    ordchegb: str = Field(
        ...,
        title="주문체결구분 (Order / fill state code)",
        description=(
            "Order / fill state code. LS-source-declared values: "
            "'01'=주문, '02'=정정, '03'=취소, '11'=체결, '12'=정정확인, "
            "'13'=취소확인, '14'=거부, 'A1'=접수중, 'AC'=접수완료."
        ),
        examples=["01", "02", "03", "11", "AC"],
    )
    marketgb: str = Field(
        ...,
        title="시장구분 (Market code)",
        description=(
            "Market code. LS-source-declared values: '10'=KOSPI, '20'=KOSDAQ, "
            "'23'=KONEX. Other LS-defined codes may appear."
        ),
        examples=["10", "20", "23"],
    )
    ordgb: str = Field(
        ...,
        title="주문구분 (Order side / credit-trade type code)",
        description=(
            "Order side combined with credit-trade type. LS-source-declared "
            "values: '01'=현금매도, '02'=현금매수, '03'=신용매도, "
            "'04'=신용매수. Other LS-defined codes may appear."
        ),
        examples=["01", "02", "03", "04"],
    )
    orgordno: str = Field(..., title="원주문번호 (Parent order number)", description="Original order number for modify / cancel events.", examples=["0", "1234567"])
    accno1: str = Field(..., title="계좌번호 (Account number)", description="Account number.", examples=["12345678901"])
    accno2: str = Field(..., title="계좌번호 (Sub-account number)", description="Sub-account number suffix.", examples=[""])
    passwd: str = Field(..., title="비밀번호 (Account password — masked)", description="Account password (masked in the push).", examples=[""])
    expcode: str = Field(..., title="종목번호 (Standard symbol code, 12 chars)", description="Standard 12-character symbol code (e.g. 'KR7005930003').", examples=["KR7005930003"])
    shtcode: str = Field(
        ...,
        title="단축종목번호 (Short symbol code with prefix)",
        description=(
            "Short symbol code with prefix. LS-source-declared convention: "
            "stock = 'A' + 6-digit code (7 chars total); ELW = 'J' + 6-digit "
            "code."
        ),
        examples=["A005930", "A035420"],
    )
    hname: str = Field(..., title="종목명 (Symbol name)", description="Symbol name in Korean.", examples=["삼성전자"])
    ordqty: str = Field(..., title="주문수량 (Order quantity)", description="Order quantity.", examples=["10", "100"])
    ordprice: str = Field(..., title="주문가격 (Order price)", description="Order price. Decimal scale not declared.", examples=["73500", "0"])
    hogagb: str = Field(
        ...,
        title="주문조건 (Order condition)",
        description=(
            "Order condition. LS-source-declared values: '0'=none, '1'=IOC, "
            "'2'=FOK."
        ),
        examples=["0", "1", "2"],
    )
    etfhogagb: str = Field(
        ...,
        title="호가유형코드 (Order-price type code)",
        description=(
            "Order-price type code. LS-source-declared values: '00'=지정가, "
            "'03'=시장가, '05'=조건부지정가. Other LS-defined codes may appear."
        ),
        examples=["00", "03", "05"],
    )
    pgmtype: str = Field(
        ...,
        title="프로그램호가구분 (Program-trade order code)",
        description=(
            "Program-trade order code. LS-source-declared value: '00'=일반. "
            "Other LS-defined codes may appear — consume as returned."
        ),
        examples=["00"],
    )
    gmhogagb: str = Field(
        ...,
        title="공매도호가구분 (Short-sell order code)",
        description=(
            "Short-sell order code. LS-source-declared values: '0'=일반, "
            "'1'=차입주식매도, '2'=기타공매도."
        ),
        examples=["0", "1", "2"],
    )
    gmhogayn: str = Field(
        ...,
        title="공매도가능여부 (Short-sell eligibility flag)",
        description="Short-sell eligibility flag. LS-source-declared values: '0'=일반, '1'=공매도.",
        examples=["0", "1"],
    )
    singb: str = Field(
        ...,
        title="신용구분 (Credit-trade type code)",
        description=(
            "Credit-trade type code. LS-source-declared value: '000'=보통. "
            "Other LS-defined codes may appear — consume as returned."
        ),
        examples=["000"],
    )
    loandt: str = Field(..., title="대출일 (Loan date)", description="Loan date in YYYYMMDD format.", examples=["", "20260101"])
    cvrgordtp: str = Field(
        ...,
        title="반대매매주문구분 (Liquidation-order code)",
        description=(
            "Liquidation-order code. LS-source-declared values: '0'=일반, "
            "'1'=자동, '2'=지점, '3'=예비주문본주문."
        ),
        examples=["0", "1", "2", "3"],
    )
    strtgcode: str = Field(..., title="전략코드 (Strategy code)", description="Strategy code — consume as returned by LS.", examples=[""])
    groupid: str = Field(..., title="그룹ID (Group ID)", description="Group ID.", examples=[""])
    ordseqno: str = Field(..., title="주문회차 (Order sequence)", description="Order sequence within the parent order.", examples=["1"])
    prtno: str = Field(..., title="포트폴리오번호 (Portfolio number)", description="Portfolio number.", examples=[""])
    basketno: str = Field(..., title="바스켓번호 (Basket number)", description="Basket number.", examples=[""])
    trchno: str = Field(..., title="트렌치번호 (Tranche number)", description="Tranche number.", examples=[""])
    itemno: str = Field(..., title="아이템번호 (Item number)", description="Item number.", examples=[""])
    brwmgmyn: str = Field(..., title="차입구분 (Borrow flag)", description="Borrow management flag — consume as returned by LS.", examples=[""])
    mbrno: str = Field(..., title="회원사번호 (Member firm number)", description="Member firm number.", examples=[""])
    procgb: str = Field(..., title="처리구분 (Processing flag)", description="Processing flag — consume as returned by LS.", examples=[""])
    admbrchno: str = Field(..., title="관리지점번호 (Managing branch number)", description="Managing branch number.", examples=[""])
    futaccno: str = Field(..., title="선물계좌번호 (Futures account number)", description="Linked futures account number.", examples=[""])
    futmarketgb: str = Field(..., title="선물상품구분 (Futures product code)", description="Futures product code — consume as returned by LS.", examples=[""])
    tongsingb: str = Field(..., title="통신매체구분 (Comms-medium code)", description="Comms-medium code — consume as returned by LS.", examples=[""])
    lpgb: str = Field(
        ...,
        title="유동성공급자구분 (Liquidity-provider flag)",
        description="LP flag. LS-source-declared values: '0'=해당없음, '1'=유동성공급자.",
        examples=["0", "1"],
    )
    dummy: str = Field(..., title="DUMMY (Reserved)", description="Reserved DUMMY field.", examples=[""])
    ordno: str = Field(..., title="주문번호 (Order number)", description="Accepted order number assigned by LS.", examples=["1234567"])
    ordtm: str = Field(..., title="주문시각 (Order time)", description="Order timestamp in HHMMSSMMM format.", examples=["090015123"])
    prntordno: str = Field(..., title="모주문번호 (Parent order number)", description="Parent order number for chained orders.", examples=["0", "1234567"])
    mgempno: str = Field(..., title="관리사원번호 (Managing employee number)", description="Managing employee number.", examples=[""])
    orgordundrqty: str = Field(..., title="원주문미체결수량 (Parent unfilled quantity)", description="Parent order unfilled quantity at the time of this event.", examples=["0", "10"])
    orgordmdfyqty: str = Field(..., title="원주문정정수량 (Parent modified quantity)", description="Parent order modified quantity.", examples=["0"])
    ordordcancelqty: str = Field(..., title="원주문취소수량 (Parent cancelled quantity)", description="Parent order cancelled quantity.", examples=["0"])
    nmcpysndno: str = Field(..., title="비회원사송신번호 (Non-member firm send number)", description="Non-member firm send number.", examples=[""])
    ordamt: str = Field(..., title="주문금액 (Order amount)", description="Order amount. Decimal scale not declared.", examples=["735000"])
    bnstp: str = Field(
        ...,
        title="매매구분 (Buy / sell side)",
        description="Buy / sell side. LS-source-declared values: '1'=sell, '2'=buy.",
        examples=["1", "2"],
    )
    spareordno: str = Field(..., title="예비주문번호 (Reserved order number)", description="Reserved order number.", examples=["0"])
    cvrgseqno: str = Field(..., title="반대매매일련번호 (Liquidation sequence)", description="Liquidation order sequence.", examples=["0"])
    rsvordno: str = Field(..., title="예약주문번호 (Reserved-order number)", description="Reserved-order number for queued orders.", examples=["0"])
    mtordseqno: str = Field(..., title="복수주문일련번호 (Multi-order sequence)", description="Multi-order sequence within a batch.", examples=["0"])
    spareordqty: str = Field(..., title="예비주문수량 (Reserved-order quantity)", description="Reserved-order quantity.", examples=["0"])
    orduserid: str = Field(..., title="주문사원번호 (Order employee number)", description="Order-placing employee number.", examples=[""])
    spotordqty: str = Field(..., title="실물주문수량 (Spot order quantity)", description="Spot order quantity (physical settlement).", examples=["0"])
    ordruseqty: str = Field(..., title="재사용주문수량 (Reused order quantity)", description="Reused order quantity.", examples=["0"])
    mnyordamt: str = Field(..., title="현금주문금액 (Cash order amount)", description="Cash component of the order amount.", examples=["735000"])
    ordsubstamt: str = Field(..., title="주문대용금액 (Order substitute-collateral amount)", description="Order substitute-collateral amount.", examples=["0"])
    ruseordamt: str = Field(..., title="재사용주문금액 (Reused order amount)", description="Reused order amount.", examples=["0"])
    ordcmsnamt: str = Field(..., title="수수료주문금액 (Order commission amount)", description="Order commission amount.", examples=["0"])
    crdtuseamt: str = Field(..., title="사용신용담보재사용금 (Used credit collateral reuse amount)", description="Used credit collateral reuse amount.", examples=["0"])
    secbalqty: str = Field(..., title="잔고수량 (Balance quantity, 실서버 미제공)", description="Balance quantity. Not provided on the live server (실서버 미제공) — preserved verbatim.", examples=["0"])
    spotordableqty: str = Field(..., title="실물가능수량 (Spot-orderable quantity, 실서버 미제공)", description="Spot-orderable quantity. Not provided on the live server (실서버 미제공) — preserved verbatim.", examples=["0"])
    ordableruseqty: str = Field(..., title="재사용가능수량(매도) (Sell-side reuse-orderable quantity, 실서버 미제공)", description="Sell-side reuse-orderable quantity. Not provided on the live server (실서버 미제공) — preserved verbatim.", examples=["0"])
    flctqty: str = Field(..., title="변동수량 (Delta quantity)", description="Delta quantity for this event.", examples=["10"])
    secbalqtyd2: str = Field(..., title="잔고수량(D2) (D+2 balance quantity, 실서버 미제공)", description="D+2 balance quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    sellableqty: str = Field(..., title="매도주문가능수량 (Sell-orderable quantity, 실서버 미제공)", description="Sell-orderable quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    unercsellordqty: str = Field(..., title="미체결매도주문수량 (Unfilled sell-order quantity, 실서버 미제공)", description="Unfilled sell-order quantity. Not provided on the live server — preserved verbatim.", examples=["0"])
    avrpchsprc: str = Field(..., title="평균매입가 (Average purchase price, 실서버 미제공)", description="Average purchase price. Not provided on the live server — preserved verbatim.", examples=["0"])
    pchsamt: str = Field(..., title="매입금액 (Purchase amount, 실서버 미제공)", description="Purchase amount. Not provided on the live server — preserved verbatim.", examples=["0"])
    deposit: str = Field(..., title="예수금 (Deposit balance)", description="Deposit balance.", examples=["10000000"])
    substamt: str = Field(..., title="대용금 (Substitute collateral)", description="Substitute collateral amount.", examples=["0"])
    csgnmnymgn: str = Field(..., title="위탁증거금현금 (Consigned cash margin)", description="Consigned cash margin.", examples=["0"])
    csgnsubstmgn: str = Field(..., title="위탁증거금대용 (Consigned substitute margin)", description="Consigned substitute margin.", examples=["0"])
    crdtpldgruseamt: str = Field(..., title="신용담보재사용금 (Credit collateral reuse amount)", description="Credit collateral reuse amount.", examples=["0"])
    ordablemny: str = Field(..., title="주문가능현금 (Orderable cash)", description="Cash available for order.", examples=["10000000"])
    ordablesubstamt: str = Field(..., title="주문가능대용 (Orderable substitute)", description="Substitute collateral available for order.", examples=["0"])
    ruseableamt: str = Field(..., title="재사용가능금액 (Reusable amount)", description="Reusable amount for subsequent orders.", examples=["0"])


class SC0RealResponse(BaseModel):
    """주식주문접수(SC0) 실시간 응답.

    Complete response model for SC0 real-time stock order acceptance data.
    """
    header: Optional[SC0RealResponseHeader]
    body: Optional[SC0RealResponseBody]

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
