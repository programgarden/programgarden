from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ02400RequestHeader(BlockRequestHeader):
    pass


class CIDBQ02400ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ02400InBlock1(BaseModel):
    """
    CIDBQ02400InBlock1 데이터 블록

    요청 필드 설명:
        IsuCodeVal: 종목코드값
        QrySrtDt: 조회시작일자 (YYYYMMDD, 과거조회시 사용, 당일조회는 공백)
        QryEndDt: 조회종료일자 (YYYYMMDD, 과거조회시 사용, 당일조회는 공백)
        ThdayTpCode: 당일구분코드 (0:과거조회 1:당일조회)
        OrdStatCode: 주문상태코드 (0:전체 1:체결 2:미체결)
        BnsTpCode: 매매구분코드 (0:전체 1:매도 2:매수)
        QryTpCode: 조회구분코드 (1:역순 2:정순)
        OrdPtnCode: 주문유형코드 (00:전체 01:일반 02:Average 03:Spread)
        OvrsDrvtFnoTpCode: 해외파생선물옵션구분코드 (A:전체 F:선물 O:옵션)
    """

    IsuCodeVal: str = Field(
        ...,
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    QrySrtDt: str = Field(
        ...,
        title="조회시작일자",
        description="조회 시작일자(YYYYMMDD). 과거조회시는 사용, 당일조회시는 공백"
    )
    """조회시작일자 (YYYYMMDD)"""

    QryEndDt: str = Field(
        ...,
        title="조회종료일자",
        description="조회 종료일자(YYYYMMDD). 과거조회시는 사용, 당일조회시는 공백"
    )
    """조회종료일자 (YYYYMMDD)"""

    ThdayTpCode: Literal["0", "1"] = Field(
        ...,
        title="당일구분코드",
        description="0:과거조회 1:당일조회"
    )
    """당일구분코드 0:과거조회 1:당일조회"""

    OrdStatCode: Literal["0", "1", "2"] = Field(
        ...,
        title="주문상태코드",
        description="0:전체 1:체결 2:미체결"
    )
    """주문상태코드 0:전체 1:체결 2:미체결"""

    BnsTpCode: Literal["0", "1", "2"] = Field(
        ...,
        title="매매구분코드",
        description="0:전체 1:매도 2:매수"
    )
    """매매구분코드 0:전체 1:매도 2:매수"""

    QryTpCode: Literal["1", "2"] = Field(
        ...,
        title="조회구분코드",
        description="1:역순 2:정순"
    )
    """조회구분코드 1:역순 2:정순"""

    OrdPtnCode: Literal["00", "01", "02", "03"] = Field(
        ...,
        title="주문유형코드",
        description="00:전체 01:일반 02:Average 03:Spread"
    )
    """주문유형코드 00:전체 01:일반 02:Average 03:Spread"""

    OvrsDrvtFnoTpCode: Literal["A", "F", "O"] = Field(
        ...,
        title="해외파생선물옵션구분코드",
        description="A:전체 F:선물 O:옵션"
    )
    """해외파생선물옵션구분코드 A:전체 F:선물 O:옵션"""


class CIDBQ02400Request(BaseModel):
    header: CIDBQ02400RequestHeader = Field(
        CIDBQ02400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ02400",
            tr_cont="N",
            tr_cont_key="",
            mac_address="",
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBQ02400 API 요청을 위한 헤더 데이터 블록",
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDBQ02400InBlock1"], CIDBQ02400InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 주문체결내역 상세 조회를 위한 입력 데이터 블록",
    )
    """입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ02400"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션",
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ02400OutBlock1(BaseModel):
    """
    CIDBQ02400OutBlock1 데이터 블록

    응답 필드 요약:
        RecCnt, AcntNo, Pwd, IsuCodeVal, QrySrtDt, QryEndDt, ThdayTpCode,
        OrdStatCode, BnsTpCode, QryTpCode, OrdPtnCode, OvrsDrvtFnoTpCode
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수",
    )
    """레코드갯수"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="조회 대상 계좌 번호",
    )
    """계좌번호"""

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="계좌 비밀번호",
    )
    """비밀번호"""

    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값",
    )
    """종목코드값"""

    QrySrtDt: str = Field(
        default="",
        title="조회시작일자",
        description="조회 시작일자(YYYYMMDD)",
    )
    """조회시작일자 (YYYYMMDD)"""

    QryEndDt: str = Field(
        default="",
        title="조회종료일자",
        description="조회 종료일자(YYYYMMDD)",
    )
    """조회종료일자 (YYYYMMDD)"""

    ThdayTpCode: str = Field(
        default="",
        title="당일구분코드",
        description="0:과거조회 1:당일조회",
    )
    """당일구분코드"""

    OrdStatCode: str = Field(
        default="",
        title="주문상태코드",
        description="0:전체 1:체결 2:미체결",
    )
    """주문상태코드"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="0:전체 1:매도 2:매수",
    )
    """매매구분코드"""

    QryTpCode: str = Field(
        default="",
        title="조회구분코드",
        description="1:역순 2:정순",
    )
    """조회구분코드"""

    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드",
        description="00:전체 01:일반 02:Average 03:Spread",
    )
    """주문유형코드"""

    OvrsDrvtFnoTpCode: str = Field(
        default="",
        title="해외파생선물옵션구분코드",
        description="A:전체 F:선물 O:옵션",
    )
    """해외파생선물옵션구분코드"""


class CIDBQ02400OutBlock2(BaseModel):
    """
    CIDBQ02400OutBlock2 데이터 블록 (Occurs)

    많은 수의 주문/체결 레코드를 포함하는 항목입니다. 주요 필드는 아래와 같습니다.
    """

    OrdDt: str = Field(default="", title="주문일자", description="주문일자(YYYYMMDD)")
    """주문일자"""

    OvrsFutsOrdNo: str = Field(default="", title="해외선물주문번호", description="해외선물 주문번호")
    """해외선물주문번호"""

    OvrsFutsOrgOrdNo: str = Field(default="", title="해외선물원주문번호", description="해외선물 원주문번호")
    """해외선물원주문번호"""

    FcmOrdNo: str = Field(default="", title="FCM주문번호", description="FCM 주문번호")
    """FCM주문번호"""

    ExecDt: str = Field(default="", title="체결일자", description="체결일자(YYYYMMDD)")
    """체결일자"""

    OvrsFutsExecNo: str = Field(default="", title="해외선물체결번호", description="해외선물 체결번호")
    """해외선물체결번호"""

    FcmAcntNo: str = Field(default="", title="FCM계좌번호", description="FCM 계좌번호")
    """FCM계좌번호"""

    IsuCodeVal: str = Field(default="", title="종목코드값", description="종목코드값")
    """종목코드값"""

    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """종목명"""

    AbrdFutsXrcPrc: float = Field(default=0.0, title="해외선물행사가격", description="해외선물 행사가격")
    """해외선물행사가격"""

    BnsTpCode: str = Field(default="", title="매매구분코드", description="0:전체 1:매도 2:매수")
    """매매구분코드"""

    BnsTpNm: str = Field(default="", title="매매구분명", description="매매구분명")
    """매매구분명"""

    FutsOrdStatCode: str = Field(default="", title="선물주문상태코드", description="0:전체 1:체결 2:미체결")
    """선물주문상태코드"""

    TpCodeNm: str = Field(default="", title="구분코드명", description="신규, 정정, 취소 등")
    """구분코드명"""

    FutsOrdTpCode: str = Field(default="", title="선물주문구분코드", description="")
    """선물주문구분코드"""

    TrdTpNm: str = Field(default="", title="거래구분명", description="주문, 접수, 확인, 체결, 소멸, 거부")
    """거래구분명"""

    AbrdFutsOrdPtnCode: str = Field(default="", title="해외선물주문유형코드", description="")
    """해외선물주문유형코드"""

    OrdPtnNm: str = Field(default="", title="주문유형명", description="시장가, 지정가, Stop Market, Stop Limit")
    """주문유형명"""

    OrdPtnTermTpCode: str = Field(default="", title="주문유형기간구분코드", description="")
    """주문유형기간구분코드"""

    CmnCodeNm: str = Field(default="", title="공통코드명", description="일반, Spread 등")
    """공통코드명"""

    AppSrtDt: str = Field(default="", title="적용시작일자", description="적용 시작일자(YYYYMMDD)")
    """적용시작일자"""

    AppEndDt: str = Field(default="", title="적용종료일자", description="적용 종료일자(YYYYMMDD)")
    """적용종료일자"""

    OrdQty: int = Field(default=0, title="주문수량", description="주문 수량")
    """주문수량"""

    OvrsDrvtOrdPrc: float = Field(default=0.0, title="해외파생주문가격", description="해외파생 주문가격")
    """해외파생주문가격"""

    OvrsDrvtExecIsuCode: str = Field(default="", title="해외파생체결종목코드", description="해외파생 체결 종목코드")
    """해외파생체결종목코드"""

    ExecIsuNm: str = Field(default="", title="체결종목명", description="체결 종목명")
    """체결종목명"""

    ExecBnsTpCode: str = Field(default="", title="체결매매구분코드", description="체결 매매구분코드")
    """체결매매구분코드"""

    ExecBnsTpNm: str = Field(default="", title="체결매매구분명", description="체결 매매구분명")
    """체결매매구분명"""

    ExecQty: int = Field(default=0, title="체결수량", description="체결 수량")
    """체결수량"""

    AbrdFutsExecPrc: float = Field(default=0.0, title="해외선물체결가격", description="해외선물 체결가격")
    """해외선물체결가격"""

    OrdCndiPrc: float = Field(default=0.0, title="주문조건가격", description="주문 조건 가격")
    """주문조건가격"""

    OvrsDrvtNowPrc: float = Field(default=0.0, title="해외파생현재가", description="해외파생 현재가")
    """해외파생현재가"""

    UnercQty: int = Field(default=0, title="미체결수량", description="미체결 수량")
    """미체결수량"""

    TrxStatCode: str = Field(default="", title="처리상태코드", description="")
    """처리상태코드"""

    TrxStatCodeNm: str = Field(default="", title="처리상태코드명", description="")
    """처리상태코드명"""

    CsgnCmsn: float = Field(default=0.0, title="위탁수수료", description="위탁수수료")
    """위탁수수료"""

    FcmCmsn: float = Field(default=0.0, title="FCM수수료", description="FCM 수수료")
    """FCM수수료"""

    ThcoCmsn: float = Field(default=0.0, title="당사수수료", description="당사 수수료")
    """당사수수료"""

    MdaCode: str = Field(default="", title="매체코드", description="매체코드(00 창구 등)")
    """매체코드"""

    MdaCodeNm: str = Field(default="", title="매체코드명", description="매체코드명")
    """매체코드명"""

    RegTmnlNo: str = Field(default="", title="등록단말번호", description="등록 단말 번호")
    """등록단말번호"""

    RegUserId: str = Field(default="", title="등록사용자ID", description="등록 사용자 ID")
    """등록사용자ID"""

    OrdSndDttm: str = Field(default="", title="주문발송일시", description="주문 발송 일시(YYYYMMDDHHMMSSsss)")
    """주문발송일시"""

    ExecDttm: str = Field(default="", title="체결일시", description="체결 일시(YYYYMMDDHHMMSSsss)")
    """체결일시"""

    EufOneCmsnAmt: float = Field(default=0.0, title="거래소비용1수수료금액", description="거래소 비용 1 수수료")
    """거래소비용1수수료금액"""

    EufTwoCmsnAmt: float = Field(default=0.0, title="거래소비용2수수료금액", description="거래소 비용 2 수수료")
    """거래소비용2수수료금액"""

    LchOneCmsnAmt: float = Field(default=0.0, title="런던청산소1수수료금액", description="런던청산소 1 수수료")
    """런던청산소1수수료금액"""

    LchTwoCmsnAmt: float = Field(default=0.0, title="런던청산소2수수료금액", description="런던청산소 2 수수료")
    """런던청산소2수수료금액"""

    TrdOneCmsnAmt: float = Field(default=0.0, title="거래1수수료금액", description="거래 1 수수료")
    """거래1수수료금액"""

    TrdTwoCmsnAmt: float = Field(default=0.0, title="거래2수수료금액", description="거래 2 수수료")
    """거래2수수료금액"""

    TrdThreeCmsnAmt: float = Field(default=0.0, title="거래3수수료금액", description="거래 3 수수료")
    """거래3수수료금액"""

    StrmOneCmsnAmt: float = Field(default=0.0, title="단기1수수료금액", description="단기 1 수수료")
    """단기1수수료금액"""

    StrmTwoCmsnAmt: float = Field(default=0.0, title="단기2수수료금액", description="단기 2 수수료")
    """단기2수수료금액"""

    StrmThreeCmsnAmt: float = Field(default=0.0, title="단기3수수료금액", description="단기 3 수수료")
    """단기3수수료금액"""

    TransOneCmsnAmt: float = Field(default=0.0, title="전달1수수료금액", description="전달 1 수수료")
    """전달1수수료금액"""

    TransTwoCmsnAmt: float = Field(default=0.0, title="전달2수수료금액", description="전달 2 수수료")
    """전달2수수료금액"""

    TransThreeCmsnAmt: float = Field(default=0.0, title="전달3수수료금액", description="전달 3 수수료")
    """전달3수수료금액"""

    TransFourCmsnAmt: float = Field(default=0.0, title="전달4수수료금액", description="전달 4 수수료")
    """전달4수수료금액"""

    OvrsOptXrcRsvTpCode: str = Field(default="", title="해외옵션행사예약구분코드", description="1:만기행사 등")
    """해외옵션행사예약구분코드"""

    OvrsDrvtOptTpCode: str = Field(default="", title="해외파생옵션구분코드", description="해외파생 옵션 구분 코드")
    """해외파생옵션구분코드"""

    SprdBaseIsuYn: str = Field(default="", title="스프레드기준종목여부", description="스프레드 기준 종목 여부")
    """스프레드기준종목여부"""

    OvrsDrvtIsuCode2: str = Field(default="", title="해외파생종목코드2", description="해외파생 종목 코드2")
    """해외파생종목코드2"""


class CIDBQ02400Response(BaseModel):
    header: Optional[CIDBQ02400ResponseHeader] = Field(None, title="요청 헤더 데이터 블록")
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDBQ02400OutBlock1] = Field(None, title="첫번째 출력 블록")
    """첫번째 출력 블록"""

    block2: List[CIDBQ02400OutBlock2] = Field(default_factory=list, title="두번째 출력 블록 리스트")
    """두번째 출력 블록 리스트"""

    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    """HTTP 상태 코드"""

    rsp_cd: str = Field(..., title="응답 코드")
    """응답 코드"""

    rsp_msg: str = Field(..., title="응답 메시지")
    """응답 메시지"""

    error_msg: Optional[str] = Field(None, title="오류 메시지")
    """오류 메시지 (오류 발생 시)"""

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
