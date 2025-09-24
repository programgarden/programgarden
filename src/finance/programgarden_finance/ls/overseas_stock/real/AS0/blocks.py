from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class AS0RealRequestHeader(BlockRealRequestHeader):
    pass


class AS0RealResponseHeader(BlockRealResponseHeader):
    pass


class AS0RealRequestBody(BaseModel):
    tr_cd: str = Field("AS0", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드")


class AS0RealRequest(BaseModel):
    """
    해외주식주문접수(미국) 실시간 요청
    """
    header: AS0RealRequestHeader = Field(
        AS0RealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록",
        description="AS0 API 요청을 위한 헤더 데이터 블록"
    )
    body: AS0RealRequestBody = Field(
        AS0RealRequestBody(
            tr_cd="AS0",
            tr_key=""
        ),
        title="입력 데이터 블록",
        description="해외주식주문접수(미국) 입력 데이터 블록",
    )


class AS0RealResponseBody(BaseModel):
    """
    AS0 응답 바디 모델
    """
    lineseq: str = Field(..., title="라인일련번호", description="라인일련번호")
    """라인일련번호"""
    accno: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
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
    trcode: str = Field(..., title="TRCODE", description="TRCODE")
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

    # 주문 관련 필드
    sOrdxctPtnCode: str = Field(..., title="주문체결유형코드", description="주문체결유형코드")
    """주문체결유형코드 (01: 신규매매접수, 03: 취소주문접수, 12: 정정완료, 13: 취소완료, 14: 거부완료)"""
    sOrdMktCode: str = Field(..., title="주문시장코드", description="주문시장코드")
    """주문시장코드"""
    sOrdPtnCode: str = Field(..., title="주문유형코드", description="주문유형코드 (01: 매도, 02: 매수)")
    """주문유형코드 (01: 매도, 02: 매수)"""
    sOrgOrdNo: int = Field(..., title="원주문번호", description="원주문번호")
    """원주문번호"""
    sAcntNo: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
    sPwd: str = Field(..., title="비밀번호", description="비밀번호")
    """비밀번호"""
    sIsuNo: str = Field(..., title="종목번호", description="종목번호")
    """종목번호"""
    sShtnIsuNo: str = Field(..., title="단축종목번호", description="단축종목번호")
    """단축종목번호"""
    sIsuNm: str = Field(..., title="종목명", description="종목명")
    """종목명"""
    sOrdQty: str = Field(..., title="주문수량", description="주문수량")
    """주문수량"""
    sOrdPrc: float = Field(..., title="주문가", description="주문가")
    """주문가"""
    sOrdCndi: str = Field(..., title="주문조건", description="주문조건")
    """주문조건"""
    sOrdprcPtnCode: str = Field(..., title="호가유형코드", description="호가유형코드")
    """호가유형코드"""
    sStrtgCode: str = Field(..., title="전략코드", description="전략코드")
    """전략코드"""
    sGrpId: str = Field(..., title="그룹ID", description="그룹ID")
    """그룹ID"""
    sOrdSeqno: str = Field(..., title="주문회차", description="주문회차")
    """주문회차"""
    sCommdaCode: str = Field(..., title="통신매체코드", description="통신매체코드")
    """통신매체코드"""
    sOrdNo: int = Field(..., title="주문번호", description="주문번호")
    """주문번호"""
    sOrdTime: str = Field(..., title="주문시각", description="주문시각")
    """주문시각"""
    sPrntOrdNo: str = Field(..., title="모주문번호", description="모주문번호")
    """모주문번호"""
    sOrgOrdUnercQty: int = Field(..., title="원주문미체결수량", description="원주문미체결수량")
    """원주문미체결수량"""
    sOrgOrdMdfyQty: int = Field(..., title="원주문정정수량", description="원주문정정수량")
    """원주문정정수량"""
    sOrgOrdCancQty: int = Field(..., title="원주문취소수량", description="원주문취소수량")
    """원주문취소수량"""
    sNmcpySndNo: str = Field(..., title="비회원사송신번호", description="비회원사송신번호")
    """비회원사송신번호"""
    sOrdAmt: float = Field(..., title="주문금액", description="주문금액")
    """주문금액"""
    sBnsTp: str = Field(..., title="매매구분", description="매매구분")
    """매매구분"""
    sMtiordSeqno: str = Field(..., title="복수주문일련번호", description="복수주문일련번호")
    """복수주문일련번호"""
    sOrdUserId: str = Field(..., title="주문사원번호", description="주문사원번호")
    """주문사원번호"""
    sSpotOrdQty: int = Field(..., title="실물주문수량", description="실물주문수량")
    """실물주문수량"""
    sRuseOrdQty: int = Field(..., title="재사용주문수량", description="재사용주문수량")
    """재사용주문수량"""
    sOrdMny: float = Field(..., title="주문현금", description="주문현금")
    """주문현금"""
    sOrdSubstAmt: float = Field(..., title="주문대용금액", description="주문대용금액")
    """주문대용금액"""
    sOrdRuseAmt: float = Field(..., title="주문재사용금액", description="주문재사용금액")
    """주문재사용금액"""
    sUseCmsnAmt: float = Field(..., title="사용수수료", description="사용수수료")
    """사용수수료"""
    sSecBalQty: int = Field(..., title="잔고수량", description="잔고수량")
    """잔고수량"""
    sSpotOrdAbleQty: int = Field(..., title="실물주문가능수량", description="실물주문가능수량")
    """실물주문가능수량"""
    sOrdAbleRuseQty: int = Field(..., title="주문가능재사용수량", description="주문가능재사용수량")
    """주문가능재사용수량"""
    sFlctQty: int = Field(..., title="변동수량", description="변동수량")
    """변동수량"""
    sSecBalQtyD2: int = Field(..., title="잔고수량(D2)", description="잔고수량(D2)")
    """잔고수량(D2)"""
    sSellAbleQty: int = Field(..., title="매도주문가능수량", description="매도주문가능수량")
    """매도주문가능수량"""
    sUnercSellOrdQty: int = Field(..., title="미체결매도주문수량", description="미체결매도주문수량")
    """미체결매도주문수량"""
    sAvrPchsPrc: float = Field(..., title="평균매입가", description="평균매입가")
    """평균매입가"""
    sPchsAmt: float = Field(..., title="매입금액", description="매입금액")
    """매입금액"""
    sDeposit: float = Field(..., title="예수금", description="예수금")
    """예수금"""
    sSubstAmt: float = Field(..., title="대용금", description="대용금")
    """대용금"""
    sCsgnMnyMgn: float = Field(..., title="위탁현금증거금액", description="위탁현금증거금액")
    """위탁현금증거금액"""
    sCsgnSubstMgn: float = Field(..., title="위탁대용증거금액", description="위탁대용증거금액")
    """위탁대용증거금액"""
    sOrdAbleMny: float = Field(..., title="주문가능현금", description="주문가능현금")
    """주문가능현금"""
    sOrdAbleSubstAmt: float = Field(..., title="주문가능대용금액", description="주문가능대용금액")
    """주문가능대용금액"""
    sRuseAbleAmt: float = Field(..., title="재사용가능금액", description="재사용가능금액")
    """재사용가능금액"""
    sMgntrnCode: str = Field(..., title="신용거래코드", description="신용거래코드")
    """신용거래코드"""


class AS0RealResponse(BaseModel):
    header: Optional[AS0RealResponseHeader]
    body: Optional[AS0RealResponseBody]

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
