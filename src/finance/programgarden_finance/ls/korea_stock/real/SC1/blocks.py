"""주식주문체결(SC1) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the SC1 (Stock Order Execution) real-time WebSocket stream.
    Receives real-time notifications when a stock order is executed (filled).
    Requires account registration (tr_type='1'). Contains ~107 fields including
    execution price, quantity, and account balance information.

KO:
    주식 주문체결 시 실시간 알림을 수신하기 위한 WebSocket 요청/응답 모델입니다.
    계좌등록(tr_type='1')이 필요합니다. 체결가격, 체결수량, 계좌잔고 정보 등
    약 107개 필드를 포함합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class SC1RealRequestHeader(BlockRealRequestHeader):
    pass


class SC1RealResponseHeader(BlockRealResponseHeader):
    pass


class SC1RealRequestBody(BaseModel):
    tr_cd: str = Field("SC1", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드 (계좌등록/해제 시 필수값 아님)")


class SC1RealRequest(BaseModel):
    """주식주문체결(SC1) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for stock order execution notifications.
        Use tr_type='1' to register account, '2' to unregister.
        SC0-SC4 share the same registration - registering any one enables all five.

    KO:
        주식주문체결 실시간 알림을 위한 WebSocket 등록/해제 요청입니다.
        tr_type '1'로 계좌등록, '2'로 해제합니다.
        SC0-SC4는 하나만 등록해도 5개 주문 이벤트가 모두 활성화됩니다.
    """
    header: SC1RealRequestHeader = Field(
        SC1RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더",
        description="SC1 실시간 계좌등록/해제를 위한 헤더 블록"
    )
    body: SC1RealRequestBody = Field(
        SC1RealRequestBody(tr_cd="SC1", tr_key=""),
        title="요청 바디",
        description="주식주문체결 실시간 등록 바디"
    )


class SC1RealResponseBody(BaseModel):
    """주식주문체결(SC1) 실시간 응답 바디

    EN:
        Real-time stock order execution data body containing ~107 fields.
        All fields are str type. Key fields: ordxctptncode (execution type),
        ordno (order number), execprc (execution price), execqty (execution quantity),
        shtnIsuno (stock code), Isunm (stock name), bnstp (buy/sell).
        SC2(정정), SC3(취소), SC4(거부)도 동일한 필드 구조를 사용합니다.

    KO:
        주식주문체결 실시간 데이터 바디입니다. 약 107개 필드로 구성됩니다.
        모든 필드는 str 타입입니다. 주요 필드: ordxctptncode(주문체결유형코드),
        ordno(주문번호), execprc(체결가격), execqty(체결수량),
        shtnIsuno(단축종목번호), Isunm(종목명), bnstp(매매구분).
    """
    # ─── SC1 고유 필드 (SC0과 다른 구조) ───
    grpId: str = Field(..., title="그룹Id", description="그룹ID")
    """그룹Id"""
    trchno: str = Field(..., title="트렌치번호", description="트렌치번호")
    """트렌치번호"""
    trtzxLevytp: str = Field(..., title="거래세징수구분", description="거래세징수구분")
    """거래세징수구분"""
    ordtrxptncode: str = Field(..., title="주문처리유형코드", description="주문처리유형코드")
    """주문처리유형코드"""
    acntnm: str = Field(..., title="계좌명", description="계좌명")
    """계좌명"""
    trcode: str = Field(..., title="TRCODE", description="TRCODE (SONAT000:신규, SONAT001:정정, SONAT002:취소, SONAS100:체결확인)")
    """TRCODE"""
    userid: str = Field(..., title="사용자ID", description="사용자ID")
    """사용자ID"""
    agrgbrnno: str = Field(..., title="집계지점번호", description="집계지점번호")
    """집계지점번호"""
    regmktcode: str = Field(..., title="등록시장코드", description="등록시장코드")
    """등록시장코드"""
    len: str = Field(..., title="헤더길이", description="헤더길이")
    """헤더길이"""
    opdrtnno: str = Field(..., title="운용지시번호", description="운용지시번호")
    """운용지시번호"""
    orgordmdfyqty: str = Field(..., title="원주문정정수량", description="원주문정정수량")
    """원주문정정수량"""
    avrpchsprc: str = Field(..., title="평균매입가", description="평균매입가 (실서버 미제공)")
    """평균매입가"""
    exectime: str = Field(..., title="체결시각", description="체결시각 (HHMMSSMMM)")
    """체결시각"""
    cont: str = Field(..., title="연속구분", description="연속구분")
    """연속구분"""
    mnymgnrat: str = Field(..., title="현금증거금률", description="현금증거금률")
    """현금증거금률"""
    mdfycnfqty: str = Field(..., title="정정확인수량", description="정정확인수량")
    """정정확인수량"""
    orgordcancqty: str = Field(..., title="원주문취소수량", description="원주문취소수량")
    """원주문취소수량"""
    compress: str = Field(..., title="압축구분", description="압축구분")
    """압축구분"""
    execprc: str = Field(..., title="체결가격", description="체결가격")
    """체결가격"""
    mdfycnfprc: str = Field(..., title="정정확인가격", description="정정확인가격")
    """정정확인가격"""
    unercsellordqty: str = Field(..., title="미체결매도주문수량", description="미체결매도주문수량 (실서버 미제공)")
    """미체결매도주문수량"""
    cmsnamtexecamt: str = Field(..., title="수수료체결금액", description="수수료체결금액")
    """수수료체결금액"""
    ruseableamt: str = Field(..., title="재사용가능금액", description="재사용가능금액")
    """재사용가능금액"""
    gubun: str = Field(..., title="헤더구분", description="헤더구분")
    """헤더구분"""
    trid: str = Field(..., title="TR추적ID", description="TR추적ID")
    """TR추적ID"""
    flctqty: str = Field(..., title="변동수량", description="변동수량")
    """변동수량"""
    execno: str = Field(..., title="체결번호", description="체결번호")
    """체결번호"""
    lptp: str = Field(..., title="유동성공급자구분", description="유동성공급자구분")
    """유동성공급자구분"""
    varmsglen: str = Field(..., title="가변메시지길이", description="가변메시지길이")
    """가변메시지길이"""
    ordno: str = Field(..., title="주문번호", description="주문번호")
    """주문번호"""
    futsmkttp: str = Field(..., title="선물시장구분", description="선물시장구분")
    """선물시장구분"""
    crdtexecamt: str = Field(..., title="신용체결금액", description="신용체결금액")
    """신용체결금액"""
    deposit: str = Field(..., title="예수금", description="예수금")
    """예수금"""
    frgrunqno: str = Field(..., title="외국인고유번호", description="외국인고유번호")
    """외국인고유번호"""
    crdayruseexecval: str = Field(..., title="금일재사용체결금액", description="금일재사용체결금액")
    """금일재사용체결금액"""
    trsrc: str = Field(..., title="조회발원지", description="조회발원지")
    """조회발원지"""
    ordacntno: str = Field(..., title="주문계좌번호", description="주문계좌번호")
    """주문계좌번호"""
    reqcnt: str = Field(..., title="요청레코드개수", description="요청레코드개수")
    """요청레코드개수"""
    shtnIsuno: str = Field(..., title="단축종목번호", description="단축종목번호 (예: 'A005930')")
    """단축종목번호"""
    accno1: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
    strtgcode: str = Field(..., title="전략코드", description="전략코드")
    """전략코드"""
    ordseqno: str = Field(..., title="주문회차", description="주문회차")
    """주문회차"""
    Isunm: str = Field(..., title="종목명", description="종목명 (예: '삼성전자')")
    """종목명"""
    ordablesubstamt: str = Field(..., title="주문가능대용", description="주문가능대용")
    """주문가능대용"""
    encrypt: str = Field(..., title="암호구분", description="암호구분")
    """암호구분"""
    Isuno: str = Field(..., title="종목번호", description="표준종목번호 12자리 (예: 'KR7005930003')")
    """종목번호"""
    accno2: str = Field(..., title="계좌번호", description="계좌번호 부번")
    """계좌번호"""
    contkey: str = Field(..., title="연속키값", description="연속키값")
    """연속키값"""
    Loandt: str = Field(..., title="대출일", description="대출일 (YYYYMMDD)")
    """대출일"""
    seq: str = Field(..., title="전문일련번호", description="전문일련번호")
    """전문일련번호"""
    lineseq: str = Field(..., title="라인일련번호", description="라인일련번호")
    """라인일련번호"""
    varlen: str = Field(..., title="가변시스템길이", description="가변시스템길이")
    """가변시스템길이"""
    orduserId: str = Field(..., title="주문자Id", description="주문자ID")
    """주문자Id"""
    mgmtbrnno: str = Field(..., title="관리지점번호", description="관리지점번호")
    """관리지점번호"""
    rjtqty: str = Field(..., title="거부수량", description="거부수량")
    """거부수량"""
    ordprcptncode: str = Field(..., title="호가유형코드", description="호가유형코드 (00:지정가, 03:시장가 등)")
    """호가유형코드"""
    stdIsuno: str = Field(..., title="표준종목번호", description="표준종목번호 12자리")
    """표준종목번호"""
    pchsant: str = Field(..., title="매입금액", description="매입금액 (실서버 미제공)")
    """매입금액"""
    filler: str = Field(..., title="예비영역", description="예비영역")
    """예비영역"""
    secbalqty: str = Field(..., title="잔고수량", description="잔고수량 (실서버 미제공)")
    """잔고수량"""
    ordxctptncode: str = Field(..., title="주문체결유형코드", description="주문체결유형코드 (01:주문, 02:정정, 03:취소, 11:체결, 12:정정확인, 13:취소확인, 14:거부)")
    """주문체결유형코드"""
    canccnfqty: str = Field(..., title="취소확인수량", description="취소확인수량")
    """취소확인수량"""
    ordablemny: str = Field(..., title="주문가능현금", description="주문가능현금")
    """주문가능현금"""
    pubip: str = Field(..., title="공인IP", description="공인IP")
    """공인IP"""
    prvip: str = Field(..., title="사설IP", description="사설IP")
    """사설IP"""
    funckey: str = Field(..., title="기능키", description="기능키")
    """기능키"""
    accno: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
    compreq: str = Field(..., title="압축요청구분", description="압축요청구분")
    """압축요청구분"""
    crdtpldgruseamt: str = Field(..., title="신용담보재사용금", description="신용담보재사용금")
    """신용담보재사용금"""
    ordamt: str = Field(..., title="주문금액", description="주문금액")
    """주문금액"""
    termno: str = Field(..., title="단말번호", description="단말번호")
    """단말번호"""
    crdtpldgexecamt: str = Field(..., title="신용담보체결금액", description="신용담보체결금액")
    """신용담보체결금액"""
    ordcndi: str = Field(..., title="주문조건", description="주문조건 (0:없음, 1:IOC, 2:FOK)")
    """주문조건"""
    rmndLoanamt: str = Field(..., title="잔여대출금액", description="잔여대출금액 (실서버 미제공)")
    """잔여대출금액"""
    bpno: str = Field(..., title="지점번호", description="지점번호")
    """지점번호"""
    substamt: str = Field(..., title="대용금", description="대용금")
    """대용금"""
    mgempno: str = Field(..., title="관리사원번호", description="관리사원번호")
    """관리사원번호"""
    csgnsubstmgn: str = Field(..., title="위탁증거금대용", description="위탁증거금대용")
    """위탁증거금대용"""
    offset: str = Field(..., title="공통시작지점", description="공통시작지점")
    """공통시작지점"""
    rcptexectime: str = Field(..., title="거래소수신체결시각", description="거래소수신체결시각 (HHMMSSMMM)")
    """거래소수신체결시각"""
    sellableqty: str = Field(..., title="매도주문가능수량", description="매도주문가능수량 (실서버 미제공)")
    """매도주문가능수량"""
    spotexecqty: str = Field(..., title="실물체결수량", description="실물체결수량")
    """실물체결수량"""
    varhdlen: str = Field(..., title="가변해더길이", description="가변해더길이")
    """가변해더길이"""
    substmgnrat: str = Field(..., title="대용증거금률", description="대용증거금률")
    """대용증거금률"""
    ordavrexecprc: str = Field(..., title="주문평균체결가격", description="주문평균체결가격")
    """주문평균체결가격"""
    itemno: str = Field(..., title="아이템번호", description="아이템번호")
    """아이템번호"""
    mgntrncode: str = Field(..., title="신용거래코드", description="신용거래코드 (000:보통 등)")
    """신용거래코드"""
    nsavtrdqty: str = Field(..., title="비저축체결수량", description="비저축체결수량")
    """비저축체결수량"""
    ifinfo: str = Field(..., title="I/F정보", description="I/F정보")
    """I/F정보"""
    ordableruseqty: str = Field(..., title="재사용가능수량(매도)", description="재사용가능수량 (실서버 미제공)")
    """재사용가능수량(매도)"""
    ptflno: str = Field(..., title="포트폴리오번호", description="포트폴리오번호")
    """포트폴리오번호"""
    secbalqtyd2: str = Field(..., title="잔고수량(d2)", description="잔고수량(D2) (실서버 미제공)")
    """잔고수량(d2)"""
    brwmgmtYn: str = Field(..., title="차입관리여부", description="차입관리여부")
    """차입관리여부"""
    eventid: str = Field(..., title="I/F이벤트ID", description="I/F이벤트ID")
    """I/F이벤트ID"""
    csgnmnymgn: str = Field(..., title="위탁증거금현금", description="위탁증거금현금")
    """위탁증거금현금"""
    pcbpno: str = Field(..., title="처리지점번호", description="처리지점번호")
    """처리지점번호"""
    orgordno: str = Field(..., title="원주문번호", description="원주문번호")
    """원주문번호"""
    ifid: str = Field(..., title="I/F일련번호", description="I/F일련번호")
    """I/F일련번호"""
    media: str = Field(..., title="접속매체", description="접속매체")
    """접속매체"""
    mtiordseqno: str = Field(..., title="복수주문일련번호", description="복수주문일련번호")
    """복수주문일련번호"""
    filler1: str = Field(..., title="예비영역", description="예비영역")
    """예비영역"""
    orgordunercqty: str = Field(..., title="원주문미체결수량", description="원주문미체결수량")
    """원주문미체결수량"""
    mbrnmbrno: str = Field(..., title="회원/비회원사번호", description="회원/비회원사번호")
    """회원/비회원사번호"""
    futsLnkbrnno: str = Field(..., title="선물연계지점번호", description="선물연계지점번호")
    """선물연계지점번호"""
    commdacode: str = Field(..., title="통신매체코드", description="통신매체코드")
    """통신매체코드"""
    stslexecqty: str = Field(..., title="공매도체결수량", description="공매도체결수량")
    """공매도체결수량"""
    proctm: str = Field(..., title="AP처리시간", description="AP처리시간")
    """AP처리시간"""
    bfstdIsuno: str = Field(..., title="전표준종목번호", description="전표준종목번호 12자리")
    """전표준종목번호"""
    futsLnkacntno: str = Field(..., title="선물연계계좌번호", description="선물연계계좌번호")
    """선물연계계좌번호"""
    lang: str = Field(..., title="언어구분", description="언어구분")
    """언어구분"""
    unercqty: str = Field(..., title="미체결수량(주문)", description="미체결수량")
    """미체결수량(주문)"""
    execqty: str = Field(..., title="체결수량", description="이번 체결의 체결수량")
    """체결수량"""
    adduptp: str = Field(..., title="수수료합산코드", description="수수료합산코드")
    """수수료합산코드"""
    bskno: str = Field(..., title="바스켓번호", description="바스켓번호")
    """바스켓번호"""
    spotordableqty: str = Field(..., title="실물가능수량", description="실물가능수량 (실서버 미제공)")
    """실물가능수량"""
    ubstexecamt: str = Field(..., title="대용체결금액", description="대용체결금액")
    """대용체결금액"""
    cvrgordtp: str = Field(..., title="반대매매주문구분", description="반대매매주문구분 (0:일반, 1:자동, 2:지점, 3:예비주문본주문)")
    """반대매매주문구분"""
    ordqty: str = Field(..., title="주문수량", description="주문수량")
    """주문수량"""
    mnyexecamt: str = Field(..., title="현금체결금액", description="현금체결금액")
    """현금체결금액"""
    outgu: str = Field(..., title="메세지출력구분", description="메세지출력구분")
    """메세지출력구분"""
    msgcode: str = Field(..., title="메세지코드", description="메세지코드")
    """메세지코드"""
    ordtrdptncode: str = Field(..., title="주문거래유형코드", description="주문거래유형코드 (00:위탁, 01:신용, 04:선물대용)")
    """주문거래유형코드"""
    ordmktcode: str = Field(..., title="주문시장코드", description="주문시장코드 (10:코스피, 20:코스닥 등)")
    """주문시장코드"""
    ordptncode: str = Field(..., title="주문유형코드", description="주문유형코드 (01:현금매도, 02:현금매수 등)")
    """주문유형코드"""
    prdayruseexecval: str = Field(..., title="전일재사용체결금액", description="전일재사용체결금액")
    """전일재사용체결금액"""
    comid: str = Field(..., title="COM ID", description="이용사번호")
    """COM ID"""
    bnstp: str = Field(..., title="매매구분", description="매매구분 (1:매도, 2:매수)")
    """매매구분"""
    user: str = Field(..., title="조작자ID", description="조작자ID")
    """조작자ID"""
    ordprc: str = Field(..., title="주문가격", description="주문가격")
    """주문가격"""


class SC1RealResponse(BaseModel):
    """주식주문체결(SC1) 실시간 응답

    EN:
        Complete response model for SC1 real-time stock order execution data.
        Contains header (TR code) and body (execution details with ~107 fields).

    KO:
        주식주문체결 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드, body에 체결 상세 데이터(약 107개 필드)가 포함됩니다.
    """
    header: Optional[SC1RealResponseHeader]
    body: Optional[SC1RealResponseBody]

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
