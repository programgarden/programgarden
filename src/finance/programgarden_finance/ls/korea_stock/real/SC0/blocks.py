"""주식주문접수(SC0) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the SC0 (Stock Order Acceptance) real-time WebSocket stream.
    Receives real-time notifications when a stock order (buy/sell/modify/cancel)
    is accepted by the exchange. Requires account registration (tr_type='1').

KO:
    주식 주문(매수/매도/정정/취소) 접수 시 실시간 알림을 수신하기 위한
    WebSocket 요청/응답 모델입니다. 계좌등록(tr_type='1')이 필요합니다.
    헤더 공통 필드 36개 + 주문 관련 필드 약 70개로 구성됩니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class SC0RealRequestHeader(BlockRealRequestHeader):
    pass


class SC0RealResponseHeader(BlockRealResponseHeader):
    pass


class SC0RealRequestBody(BaseModel):
    tr_cd: str = Field("SC0", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드 (계좌등록/해제 시 필수값 아님)")


class SC0RealRequest(BaseModel):
    """주식주문접수(SC0) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for stock order acceptance notifications.
        Use tr_type='1' to register account, '2' to unregister.
        SC0/SC1/SC2/SC3/SC4 share the same registration - registering any one
        automatically enables all five order event types.

    KO:
        주식주문접수 실시간 알림을 위한 WebSocket 등록/해제 요청입니다.
        tr_type '1'로 계좌등록, '2'로 해제합니다.
        SC0/SC1/SC2/SC3/SC4는 하나만 등록해도 5개 주문 이벤트가 모두 활성화됩니다.
    """
    header: SC0RealRequestHeader = Field(
        SC0RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더",
        description="SC0 실시간 계좌등록/해제를 위한 헤더 블록"
    )
    body: SC0RealRequestBody = Field(
        SC0RealRequestBody(tr_cd="SC0", tr_key=""),
        title="요청 바디",
        description="주식주문접수 실시간 등록 바디"
    )


class SC0RealResponseBody(BaseModel):
    """주식주문접수(SC0) 실시간 응답 바디

    EN:
        Real-time stock order acceptance data body.
        Contains system header fields (36) and order-specific fields (~70).
        All fields are str type. Key fields: ordchegb (order type),
        ordgb (buy/sell), ordno (order number), shtcode (stock code).

    KO:
        주식주문접수 실시간 데이터 바디입니다.
        시스템 헤더 필드 36개와 주문 관련 필드 약 70개로 구성됩니다.
        모든 필드는 str 타입입니다. 주요 필드: ordchegb(주문체결구분),
        ordgb(주문구분), ordno(주문번호), shtcode(단축종목번호).
    """
    # ─── 시스템 헤더 공통 필드 ───
    lineseq: str = Field(..., title="라인일련번호", description="라인일련번호")
    """라인일련번호"""
    accno: str = Field(..., title="Push키", description="계좌번호 (Push키)")
    """Push키"""
    user: str = Field(..., title="조작자ID", description="조작자ID")
    """조작자ID"""
    len: str = Field(..., title="헤더길이", description="헤더길이")
    """헤더길이"""
    gubun: str = Field(..., title="헤더구분", description="헤더구분")
    """헤더구분"""
    compress: str = Field(..., title="압축구분", description="압축구분")
    """압축구분"""
    encrypt: str = Field(..., title="암호구분", description="암호구분")
    """암호구분"""
    offset: str = Field(..., title="공통시작지점", description="공통시작지점")
    """공통시작지점"""
    trcode: str = Field(..., title="TRCODE", description="TRCODE (SONAT000:신규, SONAT001:정정, SONAT002:취소, SONAS100:체결확인)")
    """TRCODE"""
    comid: str = Field(..., title="이용사번호", description="이용사번호")
    """이용사번호"""
    userid: str = Field(..., title="사용자ID", description="사용자ID")
    """사용자ID"""
    media: str = Field(..., title="접속매체", description="접속매체")
    """접속매체"""
    ifid: str = Field(..., title="I/F일련번호", description="I/F일련번호")
    """I/F일련번호"""
    seq: str = Field(..., title="전문일련번호", description="전문일련번호")
    """전문일련번호"""
    trid: str = Field(..., title="TR추적ID", description="TR추적ID")
    """TR추적ID"""
    pubip: str = Field(..., title="공인IP", description="공인IP")
    """공인IP"""
    prvip: str = Field(..., title="사설IP", description="사설IP")
    """사설IP"""
    pcbpno: str = Field(..., title="처리지점번호", description="처리지점번호")
    """처리지점번호"""
    bpno: str = Field(..., title="지점번호", description="지점번호")
    """지점번호"""
    termno: str = Field(..., title="단말번호", description="단말번호")
    """단말번호"""
    lang: str = Field(..., title="언어구분", description="언어구분")
    """언어구분"""
    proctm: str = Field(..., title="AP처리시간", description="AP처리시간")
    """AP처리시간"""
    msgcode: str = Field(..., title="메세지코드", description="메세지코드")
    """메세지코드"""
    outgu: str = Field(..., title="메세지출력구분", description="메세지출력구분")
    """메세지출력구분"""
    compreq: str = Field(..., title="압축요청구분", description="압축요청구분")
    """압축요청구분"""
    funckey: str = Field(..., title="기능키", description="기능키")
    """기능키"""
    reqcnt: str = Field(..., title="요청레코드개수", description="요청레코드개수")
    """요청레코드개수"""
    filler: str = Field(..., title="예비영역", description="예비영역")
    """예비영역"""
    cont: str = Field(..., title="연속구분", description="연속구분")
    """연속구분"""
    contkey: str = Field(..., title="연속키값", description="연속키값")
    """연속키값"""
    varlen: str = Field(..., title="가변시스템길이", description="가변시스템길이")
    """가변시스템길이"""
    varhdlen: str = Field(..., title="가변해더길이", description="가변해더길이")
    """가변해더길이"""
    varmsglen: str = Field(..., title="가변메시지길이", description="가변메시지길이")
    """가변메시지길이"""
    trsrc: str = Field(..., title="조회발원지", description="조회발원지")
    """조회발원지"""
    eventid: str = Field(..., title="I/F이벤트ID", description="I/F이벤트ID")
    """I/F이벤트ID"""
    ifinfo: str = Field(..., title="I/F정보", description="I/F정보")
    """I/F정보"""
    filler1: str = Field(..., title="예비영역", description="예비영역")
    """예비영역"""

    # ─── 주문 관련 필드 ───
    ordchegb: str = Field(..., title="주문체결구분", description="주문체결구분 (01:주문, 02:정정, 03:취소, 11:체결, 12:정정확인, 13:취소확인, 14:거부, A1:접수중, AC:접수완료)")
    """주문체결구분"""
    marketgb: str = Field(..., title="시장구분", description="시장구분 (10:코스피, 20:코스닥, 23:코넥스 등)")
    """시장구분"""
    ordgb: str = Field(..., title="주문구분", description="주문구분 (01:현금매도, 02:현금매수, 03:신용매도, 04:신용매수 등)")
    """주문구분"""
    orgordno: str = Field(..., title="원주문번호", description="원주문번호 (정정/취소 시 원래 주문번호)")
    """원주문번호"""
    accno1: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
    accno2: str = Field(..., title="계좌번호", description="계좌번호 부번")
    """계좌번호"""
    passwd: str = Field(..., title="비밀번호", description="비밀번호 (마스킹)")
    """비밀번호"""
    expcode: str = Field(..., title="종목번호", description="표준코드 12자리 (예: 'KR7005930003')")
    """종목번호"""
    shtcode: str = Field(..., title="단축종목번호", description="주식: 'A'+단축코드 7자리, ELW: 'J'+단축코드 7자리")
    """단축종목번호"""
    hname: str = Field(..., title="종목명", description="종목명 (예: '삼성전자')")
    """종목명"""
    ordqty: str = Field(..., title="주문수량", description="주문수량")
    """주문수량"""
    ordprice: str = Field(..., title="주문가격", description="주문가격")
    """주문가격"""
    hogagb: str = Field(..., title="주문조건", description="주문조건 (0:없음, 1:IOC, 2:FOK)")
    """주문조건"""
    etfhogagb: str = Field(..., title="호가유형코드", description="호가유형코드 (00:지정가, 03:시장가, 05:조건부지정가 등)")
    """호가유형코드"""
    pgmtype: str = Field(..., title="프로그램호가구분", description="프로그램호가구분 (00:일반 등)")
    """프로그램호가구분"""
    gmhogagb: str = Field(..., title="공매도호가구분", description="공매도호가구분 (0:일반, 1:차입주식매도, 2:기타공매도)")
    """공매도호가구분"""
    gmhogayn: str = Field(..., title="공매도가능여부", description="공매도가능여부 (0:일반, 1:공매도)")
    """공매도가능여부"""
    singb: str = Field(..., title="신용구분", description="신용구분 (000:보통 등)")
    """신용구분"""
    loandt: str = Field(..., title="대출일", description="대출일 (YYYYMMDD)")
    """대출일"""
    cvrgordtp: str = Field(..., title="반대매매주문구분", description="반대매매주문구분 (0:일반, 1:자동, 2:지점, 3:예비주문본주문)")
    """반대매매주문구분"""
    strtgcode: str = Field(..., title="전략코드", description="전략코드")
    """전략코드"""
    groupid: str = Field(..., title="그룹ID", description="그룹ID")
    """그룹ID"""
    ordseqno: str = Field(..., title="주문회차", description="주문회차")
    """주문회차"""
    prtno: str = Field(..., title="포트폴리오번호", description="포트폴리오번호")
    """포트폴리오번호"""
    basketno: str = Field(..., title="바스켓번호", description="바스켓번호")
    """바스켓번호"""
    trchno: str = Field(..., title="트렌치번호", description="트렌치번호")
    """트렌치번호"""
    itemno: str = Field(..., title="아이템번호", description="아이템번호")
    """아이템번호"""
    brwmgmyn: str = Field(..., title="차입구분", description="차입구분")
    """차입구분"""
    mbrno: str = Field(..., title="회원사번호", description="회원사번호")
    """회원사번호"""
    procgb: str = Field(..., title="처리구분", description="처리구분")
    """처리구분"""
    admbrchno: str = Field(..., title="관리지점번호", description="관리지점번호")
    """관리지점번호"""
    futaccno: str = Field(..., title="선물계좌번호", description="선물계좌번호")
    """선물계좌번호"""
    futmarketgb: str = Field(..., title="선물상품구분", description="선물상품구분")
    """선물상품구분"""
    tongsingb: str = Field(..., title="통신매체구분", description="통신매체구분")
    """통신매체구분"""
    lpgb: str = Field(..., title="유동성공급자구분", description="유동성공급자구분 (0:해당없음, 1:유동성공급자)")
    """유동성공급자구분"""
    dummy: str = Field(..., title="DUMMY", description="DUMMY 예비 필드")
    """DUMMY"""
    ordno: str = Field(..., title="주문번호", description="접수된 주문번호")
    """주문번호"""
    ordtm: str = Field(..., title="주문시각", description="주문시각 (HHMMSSMMM)")
    """주문시각"""
    prntordno: str = Field(..., title="모주문번호", description="모주문번호")
    """모주문번호"""
    mgempno: str = Field(..., title="관리사원번호", description="관리사원번호")
    """관리사원번호"""
    orgordundrqty: str = Field(..., title="원주문미체결수량", description="원주문미체결수량")
    """원주문미체결수량"""
    orgordmdfyqty: str = Field(..., title="원주문정정수량", description="원주문정정수량")
    """원주문정정수량"""
    ordordcancelqty: str = Field(..., title="원주문취소수량", description="원주문취소수량")
    """원주문취소수량"""
    nmcpysndno: str = Field(..., title="비회원사송신번호", description="비회원사송신번호")
    """비회원사송신번호"""
    ordamt: str = Field(..., title="주문금액", description="주문금액")
    """주문금액"""
    bnstp: str = Field(..., title="매매구분", description="매매구분 (1:매도, 2:매수)")
    """매매구분"""
    spareordno: str = Field(..., title="예비주문번호", description="예비주문번호")
    """예비주문번호"""
    cvrgseqno: str = Field(..., title="반대매매일련번호", description="반대매매일련번호")
    """반대매매일련번호"""
    rsvordno: str = Field(..., title="예약주문번호", description="예약주문번호")
    """예약주문번호"""
    mtordseqno: str = Field(..., title="복수주문일련번호", description="복수주문일련번호")
    """복수주문일련번호"""
    spareordqty: str = Field(..., title="예비주문수량", description="예비주문수량")
    """예비주문수량"""
    orduserid: str = Field(..., title="주문사원번호", description="주문사원번호")
    """주문사원번호"""
    spotordqty: str = Field(..., title="실물주문수량", description="실물주문수량")
    """실물주문수량"""
    ordruseqty: str = Field(..., title="재사용주문수량", description="재사용주문수량")
    """재사용주문수량"""
    mnyordamt: str = Field(..., title="현금주문금액", description="현금주문금액")
    """현금주문금액"""
    ordsubstamt: str = Field(..., title="주문대용금액", description="주문대용금액")
    """주문대용금액"""
    ruseordamt: str = Field(..., title="재사용주문금액", description="재사용주문금액")
    """재사용주문금액"""
    ordcmsnamt: str = Field(..., title="수수료주문금액", description="수수료주문금액")
    """수수료주문금액"""
    crdtuseamt: str = Field(..., title="사용신용담보재사용금", description="사용신용담보재사용금")
    """사용신용담보재사용금"""
    secbalqty: str = Field(..., title="잔고수량", description="잔고수량 (실서버 미제공)")
    """잔고수량"""
    spotordableqty: str = Field(..., title="실물가능수량", description="실물가능수량 (실서버 미제공)")
    """실물가능수량"""
    ordableruseqty: str = Field(..., title="재사용가능수량(매도)", description="재사용가능수량 (실서버 미제공)")
    """재사용가능수량(매도)"""
    flctqty: str = Field(..., title="변동수량", description="변동수량")
    """변동수량"""
    secbalqtyd2: str = Field(..., title="잔고수량(D2)", description="잔고수량(D2) (실서버 미제공)")
    """잔고수량(D2)"""
    sellableqty: str = Field(..., title="매도주문가능수량", description="매도주문가능수량 (실서버 미제공)")
    """매도주문가능수량"""
    unercsellordqty: str = Field(..., title="미체결매도주문수량", description="미체결매도주문수량 (실서버 미제공)")
    """미체결매도주문수량"""
    avrpchsprc: str = Field(..., title="평균매입가", description="평균매입가 (실서버 미제공)")
    """평균매입가"""
    pchsamt: str = Field(..., title="매입금액", description="매입금액 (실서버 미제공)")
    """매입금액"""
    deposit: str = Field(..., title="예수금", description="예수금")
    """예수금"""
    substamt: str = Field(..., title="대용금", description="대용금")
    """대용금"""
    csgnmnymgn: str = Field(..., title="위탁증거금현금", description="위탁증거금현금")
    """위탁증거금현금"""
    csgnsubstmgn: str = Field(..., title="위탁증거금대용", description="위탁증거금대용")
    """위탁증거금대용"""
    crdtpldgruseamt: str = Field(..., title="신용담보재사용금", description="신용담보재사용금")
    """신용담보재사용금"""
    ordablemny: str = Field(..., title="주문가능현금", description="주문가능현금")
    """주문가능현금"""
    ordablesubstamt: str = Field(..., title="주문가능대용", description="주문가능대용")
    """주문가능대용"""
    ruseableamt: str = Field(..., title="재사용가능금액", description="재사용가능금액")
    """재사용가능금액"""


class SC0RealResponse(BaseModel):
    """주식주문접수(SC0) 실시간 응답

    EN:
        Complete response model for SC0 real-time stock order acceptance data.
        Contains header (TR code) and body (order acceptance details).

    KO:
        주식주문접수 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드, body에 주문접수 상세 데이터가 포함됩니다.
    """
    header: Optional[SC0RealResponseHeader]
    body: Optional[SC0RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    """응답 코드"""
    rsp_msg: str = Field(..., title="응답 메시지")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
