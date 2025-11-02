from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01800RequestHeader(BlockRequestHeader):
    pass


class CIDBQ01800ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ01800InBlock1(BaseModel):
    """
    CIDBQ01800InBlock1 데이터 블록

    해외선물 주문내역 조회 요청에 사용되는 입력 데이터 블록입니다.
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드 갯수 (예: 1건)"
    )
    """레코드 갯수 (예: 1건)"""

    IsuCodeVal: str = Field(
        ...,
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    OrdDt: str = Field(
        ...,
        title="주문일자",
        description="주문일자 (YYYYMMDD 형식)"
    )
    """주문일자 (YYYYMMDD 형식)"""

    ThdayTpCode: str = Field(
        default="",
        title="당일구분코드",
        description="당일구분코드 (공백 등)"
    )
    """당일구분코드"""

    OrdStatCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="주문상태코드",
        description="0:전체 1:체결 2:미체결"
    )
    """주문상태코드"""

    BnsTpCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="매매구분코드",
        description="0:전체 1:매도 2:매수"
    )
    """매매구분코드"""

    QryTpCode: Literal["1", "2"] = Field(
        default="1",
        title="조회구분코드",
        description="1:역순 2:정순"
    )
    """조회구분코드"""

    OrdPtnCode: Literal["00", "01", "02", "03"] = Field(
        default="00",
        title="주문유형코드",
        description="00:전체 01:일반 02:Average 03:Spread"
    )
    """주문유형코드"""

    OvrsDrvtFnoTpCode: Literal["A", "F", "O"] = Field(
        default="A",
        title="해외파생선물옵션구분코드",
        description="A:전체 F:선물 O:옵션"
    )
    """해외파생선물옵션구분코드"""


class CIDBQ01800Request(BaseModel):
    header: CIDBQ01800RequestHeader = Field(
        CIDBQ01800RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ01800",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBQ01800 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""

    body: dict[Literal["CIDBQ01800InBlock1"], CIDBQ01800InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 주문내역 조회를 위한 입력 데이터 블록"
    )
    """입력 데이터 블록"""

    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ01800"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ01800OutBlock1(BaseModel):
    """
    CIDBQ01800OutBlock1 데이터 블록

    요청에 대한 요약 정보(계좌/조회 조건 등)를 포함합니다.
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="조회 대상 계좌 번호"
    )
    """계좌번호"""

    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="계좌 비밀번호"
    )
    """비밀번호"""

    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    OrdDt: str = Field(
        default="",
        title="주문일자",
        description="주문일자 (YYYYMMDD)"
    )
    """주문일자"""

    ThdayTpCode: str = Field(
        default="",
        title="당일구분코드",
        description="당일구분코드"
    )
    """당일구분코드"""

    OrdStatCode: str = Field(
        default="",
        title="주문상태코드",
        description="주문상태코드"
    )
    """주문상태코드"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="매매구분코드"
    )
    """매매구분코드"""

    QryTpCode: str = Field(
        default="",
        title="조회구분코드",
        description="조회구분코드"
    )
    """조회구분코드"""

    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드",
        description="주문유형코드"
    )
    """주문유형코드"""

    OvrsDrvtFnoTpCode: str = Field(
        default="",
        title="해외파생선물옵션구분코드",
        description="해외파생선물옵션구분코드"
    )
    """해외파생선물옵션구분코드"""


class CIDBQ01800OutBlock2(BaseModel):
    """
    CIDBQ01800OutBlock2 데이터 블록(Occurs)

    개별 주문 레코드의 상세 정보를 포함합니다.
    """

    OvrsFutsOrdNo: str = Field(default="", title="해외선물주문번호", description="해외선물주문번호")
    """해외선물주문번호"""

    OvrsFutsOrgOrdNo: str = Field(default="", title="해외선물원주문번호", description="해외선물원주문번호")
    """해외선물원주문번호"""

    FcmOrdNo: str = Field(default="", title="FCM주문번호", description="FCM주문번호")
    """FCM주문번호"""

    IsuCodeVal: str = Field(default="", title="종목코드값", description="종목코드값")
    """종목코드값"""

    IsuNm: str = Field(default="", title="종목명", description="종목명")
    """종목명"""

    AbrdFutsXrcPrc: float = Field(default=0.0, title="해외선물행사가격", description="해외선물행사가격")
    """해외선물행사가격"""

    FcmAcntNo: str = Field(default="", title="FCM계좌번호", description="FCM계좌번호")
    """FCM계좌번호"""

    BnsTpCode: str = Field(default="", title="매매구분코드", description="매매구분코드")
    """매매구분코드"""

    BnsTpNm: str = Field(default="", title="매매구분명", description="매매구분명")
    """매매구분명"""

    FutsOrdStatCode: str = Field(default="", title="선물주문상태코드", description="선물주문상태코드")
    """선물주문상태코드"""

    TpCodeNm: str = Field(default="", title="구분코드명", description="구분코드명")
    """구분코드명"""

    FutsOrdTpCode: str = Field(default="", title="선물주문구분코드", description="선물주문구분코드")
    """선물주문구분코드"""

    TrdTpNm: str = Field(default="", title="거래구분명", description="거래구분명")
    """거래구분명"""

    AbrdFutsOrdPtnCode: str = Field(default="", title="해외선물주문유형코드", description="해외선물주문유형코드")
    """해외선물주문유형코드"""

    OrdPtnNm: str = Field(default="", title="주문유형명", description="주문유형명")
    """주문유형명"""

    OrdPtnTermTpCode: str = Field(default="", title="주문유형기간구분코드", description="주문유형기간구분코드")
    """주문유형기간구분코드"""

    CmnCodeNm: str = Field(default="", title="공통코드명", description="공통코드명")
    """공통코드명"""

    AppSrtDt: str = Field(default="", title="적용시작일자", description="적용시작일자")
    """적용시작일자"""

    AppEndDt: str = Field(default="", title="적용종료일자", description="적용종료일자")
    """적용종료일자"""

    OvrsDrvtOrdPrc: float = Field(default=0.0, title="해외파생주문가격", description="해외파생주문가격")
    """해외파생주문가격"""

    OrdQty: int = Field(default=0, title="주문수량", description="주문수량")
    """주문수량"""

    OvrsDrvtExecIsuCode: str = Field(default="", title="해외파생체결종목코드", description="해외파생체결종목코드")
    """해외파생체결종목코드"""

    ExecIsuNm: str = Field(default="", title="체결종목명", description="체결종목명")
    """체결종목명"""

    ExecBnsTpCode: str = Field(default="", title="체결매매구분코드", description="체결매매구분코드")
    """체결매매구분코드"""

    ExecBnsTpNm: str = Field(default="", title="체결매매구분명", description="체결매매구분명")
    """체결매매구분명"""

    AbrdFutsExecPrc: float = Field(default=0.0, title="해외선물체결가격", description="해외선물체결가격")
    """해외선물체결가격"""

    ExecQty: int = Field(default=0, title="체결수량", description="체결수량")
    """체결수량"""

    OrdCndiPrc: float = Field(default=0.0, title="주문조건가격", description="주문조건가격")
    """주문조건가격"""

    OvrsDrvtNowPrc: float = Field(default=0.0, title="해외파생현재가", description="해외파생현재가")
    """해외파생현재가"""

    MdfyQty: int = Field(default=0, title="정정수량", description="정정수량")
    """정정수량"""

    CancQty: int = Field(default=0, title="취소수량", description="취소수량")
    """취소수량"""

    RjtQty: int = Field(default=0, title="거부수량", description="거부수량")
    """거부수량"""

    CnfQty: int = Field(default=0, title="확인수량", description="확인수량")
    """확인수량"""

    UnercQty: int = Field(default=0, title="미체결수량", description="미체결수량")
    """미체결수량"""

    CvrgYn: str = Field(default="", title="반대매매여부", description="반대매매여부")
    """반대매매여부"""

    RegTmnlNo: str = Field(default="", title="등록단말번호", description="등록단말번호")
    """등록단말번호"""

    RegBrnNo: str = Field(default="", title="등록지점번호", description="등록지점번호")
    """등록지점번호"""

    RegUserId: str = Field(default="", title="등록사용자ID", description="등록사용자ID")
    """등록사용자ID"""

    OrdDt: str = Field(default="", title="주문일자", description="주문일자")
    """주문일자"""

    OrdTime: str = Field(default="", title="주문시각", description="주문시각")
    """주문시각"""

    OvrsOptXrcRsvTpCode: str = Field(default="", title="해외옵션행사예약구분코드", description="해외옵션행사예약구분코드")
    """해외옵션행사예약구분코드"""

    OvrsDrvtOptTpCode: str = Field(default="", title="해외파생옵션구분코드", description="해외파생옵션구분코드")
    """해외파생옵션구분코드"""

    SprdBaseIsuYn: str = Field(default="", title="스프레드기준종목여부", description="스프레드기준종목여부")
    """스프레드기준종목여부"""

    OvrsFutsOrdDt: str = Field(default="", title="해외선물주문일자", description="해외선물주문일자")
    """해외선물주문일자"""

    OvrsFutsOrdNo2: str = Field(default="", title="해외선물주문번호2", description="해외선물주문번호2")
    """해외선물주문번호2"""

    OvrsFutsOrgOrdNo2: str = Field(default="", title="해외선물원주문번호2", description="해외선물원주문번호2")
    """해외선물원주문번호2"""

    OvrsDrvtIsuCode2: str = Field(default="", title="해외파생종목코드2", description="해외파생종목코드2")
    """해외파생종목코드2"""


class CIDBQ01800Response(BaseModel):
    header: Optional[CIDBQ01800ResponseHeader] = Field(None, title="요청 헤더 데이터 블록")
    """요청 헤더 데이터 블록"""

    block1: Optional[CIDBQ01800OutBlock1] = Field(None, title="첫번째 출력 블록")
    """첫번째 출력 블록"""

    block2: List[CIDBQ01800OutBlock2] = Field(default_factory=list, title="두번째 출력 블록 리스트")
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
    """ private으로 BaseModel의 직렬화에 포함시키지 않는다 """

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
