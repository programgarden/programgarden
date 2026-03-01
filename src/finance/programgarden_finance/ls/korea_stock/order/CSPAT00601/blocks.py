from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAT00601RequestHeader(BlockRequestHeader):
    """CSPAT00601 요청용 Header"""
    pass


class CSPAT00601ResponseHeader(BlockResponseHeader):
    """CSPAT00601 응답용 Header"""
    pass


class CSPAT00601InBlock1(BaseModel):
    """
    CSPAT00601InBlock1 - 현물주문 입력 블록

    국내주식 현물 매수/매도 주문을 요청합니다.

    Attributes:
        IsuNo (str): 종목번호 (주식/ETF: 종목코드 or A+종목코드, ELW: J+종목코드, ETN: Q+종목코드)
        OrdQty (int): 주문수량
        OrdPrc (float): 주문가 (시장가 주문 시 0)
        BnsTpCode (str): 매매구분 (1:매도, 2:매수)
        OrdprcPtnCode (str): 호가유형코드
        MgntrnCode (str): 신용거래코드 (000:보통)
        LoanDt (str): 대출일
        OrdCndiTpCode (str): 주문조건구분 (0:없음, 1:IOC, 2:FOK)
        MbrNo (str): 회원사번호 (KRX/NXT/공백=KRX)
    """
    IsuNo: str = Field(
        ...,
        title="종목번호",
        description="주식/ETF: 종목코드 or A+종목코드(모의투자는 A+종목코드), ELW: J+종목코드, ETN: Q+종목코드"
    )
    """ 종목번호 """
    OrdQty: int = Field(
        ...,
        title="주문수량",
        description="주문수량"
    )
    """ 주문수량 """
    OrdPrc: float = Field(
        default=0,
        title="주문가",
        description="주문가 (시장가 주문 시 0)"
    )
    """ 주문가 (시장가 주문 시 0) """
    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="매매구분",
        description="1:매도, 2:매수"
    )
    """ 매매구분 (1:매도, 2:매수) """
    OrdprcPtnCode: Literal["00", "03", "05", "06", "07", "12", "61", "81", "82"] = Field(
        default="00",
        title="호가유형코드",
        description="00:지정가 03:시장가 05:조건부지정가 06:최유리지정가 07:최우선지정가 12:중간가 61:장개시전시간외종가 81:시간외종가 82:시간외단일가"
    )
    """ 호가유형코드 (00:지정가 03:시장가 05:조건부지정가 06:최유리지정가 07:최우선지정가 12:중간가 61:장개시전시간외종가 81:시간외종가 82:시간외단일가) """
    MgntrnCode: Literal["000", "003", "005", "007", "101", "103", "105", "107", "180"] = Field(
        default="000",
        title="신용거래코드",
        description="000:보통 003:유통/자기융자신규 005:유통대주신규 007:자기대주신규 101:유통융자상환 103:자기융자상환 105:유통대주상환 107:자기대주상환 180:예탁담보대출상환(신용)"
    )
    """ 신용거래코드 (000:보통) """
    LoanDt: str = Field(
        default="",
        title="대출일",
        description="대출일"
    )
    """ 대출일 """
    OrdCndiTpCode: Literal["0", "1", "2"] = Field(
        default="0",
        title="주문조건구분",
        description="0:없음 1:IOC 2:FOK"
    )
    """ 주문조건구분 (0:없음 1:IOC 2:FOK) """
    MbrNo: str = Field(
        default="",
        title="회원사번호",
        description="KRX: KRX, NXT: NXT, 공백을 포함한 그 외 입력값은 KRX로 처리"
    )
    """ 회원사번호 (KRX/NXT/공백=KRX) """


class CSPAT00601Request(BaseModel):
    """
    CSPAT00601 API 요청 - 현물주문

    Attributes:
        header (CSPAT00601RequestHeader)
        body (dict[Literal["CSPAT00601InBlock1"], CSPAT00601InBlock1])
    """
    header: CSPAT00601RequestHeader = CSPAT00601RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAT00601",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAT00601InBlock1"], CSPAT00601InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAT00601"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAT00601OutBlock1(BaseModel):
    """
    CSPAT00601OutBlock1 - 현물주문 입력 echo-back 블록
    """
    RecCnt: int = Field(default=0, title="레코드갯수")
    """ 레코드갯수 """
    AcntNo: str = Field(default="", title="계좌번호")
    """ 계좌번호 """
    InptPwd: str = Field(default="", title="입력비밀번호")
    """ 입력비밀번호 """
    IsuNo: str = Field(default="", title="종목번호")
    """ 종목번호 """
    OrdQty: int = Field(default=0, title="주문수량")
    """ 주문수량 """
    OrdPrc: float = Field(default=0, title="주문가")
    """ 주문가 """
    BnsTpCode: str = Field(default="", title="매매구분")
    """ 매매구분 (1:매도, 2:매수) """
    OrdprcPtnCode: str = Field(default="", title="호가유형코드")
    """ 호가유형코드 """
    PrgmOrdprcPtnCode: str = Field(default="", title="프로그램호가유형코드")
    """ 프로그램호가유형코드 """
    StslAbleYn: str = Field(default="", title="공매도가능여부")
    """ 공매도가능여부 """
    StslOrdprcTpCode: str = Field(default="", title="공매도호가구분")
    """ 공매도호가구분 """
    CommdaCode: str = Field(default="", title="통신매체코드")
    """ 통신매체코드 """
    MgntrnCode: str = Field(default="", title="신용거래코드")
    """ 신용거래코드 """
    LoanDt: str = Field(default="", title="대출일")
    """ 대출일 """
    MbrNo: str = Field(default="", title="회원번호")
    """ 회원번호 """
    OrdCndiTpCode: str = Field(default="", title="주문조건구분")
    """ 주문조건구분 """
    StrtgCode: str = Field(default="", title="전략코드")
    """ 전략코드 """
    GrpId: str = Field(default="", title="그룹ID")
    """ 그룹ID """
    OrdSeqNo: int = Field(default=0, title="주문회차")
    """ 주문회차 """
    PtflNo: int = Field(default=0, title="포트폴리오번호")
    """ 포트폴리오번호 """
    BskNo: int = Field(default=0, title="바스켓번호")
    """ 바스켓번호 """
    TrchNo: int = Field(default=0, title="트렌치번호")
    """ 트렌치번호 """
    ItemNo: int = Field(default=0, title="아이템번호")
    """ 아이템번호 """
    OpDrtnNo: str = Field(default="", title="운용지시번호")
    """ 운용지시번호 """
    LpYn: str = Field(default="", title="유동성공급자여부")
    """ 유동성공급자여부 """
    CvrgTpCode: str = Field(default="", title="반대매매구분")
    """ 반대매매구분 """


class CSPAT00601OutBlock2(BaseModel):
    """
    CSPAT00601OutBlock2 - 현물주문 결과 블록

    주문 접수 결과를 제공합니다. OrdNo(주문번호)가 핵심 필드입니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수")
    """ 레코드갯수 """
    OrdNo: int = Field(default=0, title="주문번호")
    """ 주문번호 """
    OrdTime: str = Field(default="", title="주문시각")
    """ 주문시각 """
    OrdMktCode: str = Field(default="", title="주문시장코드")
    """ 주문시장코드 """
    OrdPtnCode: str = Field(default="", title="주문유형코드")
    """ 주문유형코드 """
    ShtnIsuNo: str = Field(default="", title="단축종목번호")
    """ 단축종목번호 """
    MgempNo: str = Field(default="", title="관리사원번호")
    """ 관리사원번호 """
    OrdAmt: int = Field(default=0, title="주문금액")
    """ 주문금액 """
    SpareOrdNo: int = Field(default=0, title="예비주문번호")
    """ 예비주문번호 """
    CvrgSeqno: int = Field(default=0, title="반대매매일련번호")
    """ 반대매매일련번호 """
    RsvOrdNo: int = Field(default=0, title="예약주문번호")
    """ 예약주문번호 """
    SpotOrdQty: int = Field(default=0, title="실물주문수량")
    """ 실물주문수량 """
    RuseOrdQty: int = Field(default=0, title="재사용주문수량")
    """ 재사용주문수량 """
    MnyOrdAmt: int = Field(default=0, title="현금주문금액")
    """ 현금주문금액 """
    SubstOrdAmt: int = Field(default=0, title="대용주문금액")
    """ 대용주문금액 """
    RuseOrdAmt: int = Field(default=0, title="재사용주문금액")
    """ 재사용주문금액 """
    AcntNm: str = Field(default="", title="계좌명")
    """ 계좌명 """
    IsuNm: str = Field(default="", title="종목명")
    """ 종목명 """


class CSPAT00601Response(BaseModel):
    """
    CSPAT00601 API 전체 응답 - 현물주문

    Attributes:
        header (Optional[CSPAT00601ResponseHeader])
        block1 (Optional[CSPAT00601OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAT00601OutBlock2]): 주문 결과 (주문번호 등)
        rsp_cd (str): 응답코드 ("00040" = 매수주문완료, "00039" = 매도주문완료)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAT00601ResponseHeader] = None
    block1: Optional[CSPAT00601OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="주문 입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAT00601OutBlock2] = Field(
        None,
        title="주문 결과",
        description="주문번호, 주문시각, 주문금액 등 주문 접수 결과"
    )
    status_code: Optional[int] = Field(None, title="HTTP 상태 코드")
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(None, title="오류메시지")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
