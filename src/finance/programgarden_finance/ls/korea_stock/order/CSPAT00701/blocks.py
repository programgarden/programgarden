from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CSPAT00701RequestHeader(BlockRequestHeader):
    """CSPAT00701 요청용 Header"""
    pass


class CSPAT00701ResponseHeader(BlockResponseHeader):
    """CSPAT00701 응답용 Header"""
    pass


class CSPAT00701InBlock1(BaseModel):
    """
    CSPAT00701InBlock1 - 현물정정주문 입력 블록

    기존 주문의 가격/수량/호가유형을 정정합니다.
    원주문번호(OrgOrdNo)는 CSPAT00601 주문 시 받은 OrdNo를 사용합니다.

    Attributes:
        OrgOrdNo (int): 원주문번호 (정정 대상 주문번호)
        IsuNo (str): 종목번호 (주식/ETF: 종목코드 or A+종목코드, ELW: J+종목코드, ETN: Q+종목코드)
        OrdQty (int): 주문수량
        OrdprcPtnCode (str): 호가유형코드
        OrdCndiTpCode (str): 주문조건구분 (0:없음, 1:IOC, 2:FOK)
        OrdPrc (float): 주문가
    """
    OrgOrdNo: int = Field(
        ...,
        title="원주문번호",
        description="정정 대상 주문번호 (CSPAT00601 주문 시 받은 OrdNo)"
    )
    """ 원주문번호 (정정 대상 주문번호) """
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
    OrdprcPtnCode: str = Field(
        default="00",
        title="호가유형코드",
        description="00:지정가 03:시장가 05:조건부지정가 06:최유리지정가 07:최우선지정가 61:장개시전시간외종가 81:시간외종가 82:시간외단일가"
    )
    """ 호가유형코드 (00:지정가 03:시장가 등) """
    OrdCndiTpCode: str = Field(
        default="0",
        title="주문조건구분",
        description="0:없음 1:IOC 2:FOK"
    )
    """ 주문조건구분 (0:없음 1:IOC 2:FOK) """
    OrdPrc: float = Field(
        default=0,
        title="주문가",
        description="주문가"
    )
    """ 주문가 """


class CSPAT00701Request(BaseModel):
    """
    CSPAT00701 API 요청 - 현물정정주문

    Attributes:
        header (CSPAT00701RequestHeader)
        body (dict[Literal["CSPAT00701InBlock1"], CSPAT00701InBlock1])
    """
    header: CSPAT00701RequestHeader = CSPAT00701RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="CSPAT00701",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["CSPAT00701InBlock1"], CSPAT00701InBlock1]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="CSPAT00701"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CSPAT00701OutBlock1(BaseModel):
    """
    CSPAT00701OutBlock1 - 현물정정주문 입력 echo-back 블록
    """
    RecCnt: int = Field(default=0, title="레코드갯수")
    """ 레코드갯수 """
    OrgOrdNo: int = Field(default=0, title="원주문번호")
    """ 원주문번호 """
    AcntNo: str = Field(default="", title="계좌번호")
    """ 계좌번호 """
    InptPwd: str = Field(default="", title="입력비밀번호")
    """ 입력비밀번호 """
    IsuNo: str = Field(default="", title="종목번호")
    """ 종목번호 """
    OrdQty: int = Field(default=0, title="주문수량")
    """ 주문수량 """
    OrdprcPtnCode: str = Field(default="", title="호가유형코드")
    """ 호가유형코드 """
    OrdCndiTpCode: str = Field(default="", title="주문조건구분")
    """ 주문조건구분 """
    OrdPrc: float = Field(default=0, title="주문가")
    """ 주문가 """
    CommdaCode: str = Field(default="", title="통신매체코드")
    """ 통신매체코드 """
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


class CSPAT00701OutBlock2(BaseModel):
    """
    CSPAT00701OutBlock2 - 현물정정주문 결과 블록

    정정 주문 접수 결과를 제공합니다. OrdNo(주문번호)가 핵심 필드입니다.
    """
    RecCnt: int = Field(default=0, title="레코드갯수")
    """ 레코드갯수 """
    OrdNo: int = Field(default=0, title="주문번호")
    """ 주문번호 """
    PrntOrdNo: int = Field(default=0, title="모주문번호")
    """ 모주문번호 """
    OrdTime: str = Field(default="", title="주문시각")
    """ 주문시각 """
    OrdMktCode: str = Field(default="", title="주문시장코드")
    """ 주문시장코드 """
    OrdPtnCode: str = Field(default="", title="주문유형코드")
    """ 주문유형코드 """
    ShtnIsuNo: str = Field(default="", title="단축종목번호")
    """ 단축종목번호 """
    PrgmOrdprcPtnCode: str = Field(default="", title="프로그램호가유형코드")
    """ 프로그램호가유형코드 """
    StslOrdprcTpCode: str = Field(default="", title="공매도호가구분")
    """ 공매도호가구분 """
    StslAbleYn: str = Field(default="", title="공매도가능여부")
    """ 공매도가능여부 """
    MgntrnCode: str = Field(default="", title="신용거래코드")
    """ 신용거래코드 """
    LoanDt: str = Field(default="", title="대출일")
    """ 대출일 """
    CvrgOrdTp: str = Field(default="", title="반대매매주문구분")
    """ 반대매매주문구분 """
    LpYn: str = Field(default="", title="유동성공급자여부")
    """ 유동성공급자여부 """
    MgempNo: str = Field(default="", title="관리사원번호")
    """ 관리사원번호 """
    OrdAmt: int = Field(default=0, title="주문금액")
    """ 주문금액 """
    BnsTpCode: str = Field(default="", title="매매구분")
    """ 매매구분 """
    SpareOrdNo: int = Field(default=0, title="예비주문번호")
    """ 예비주문번호 """
    CvrgSeqno: int = Field(default=0, title="반대매매일련번호")
    """ 반대매매일련번호 """
    RsvOrdNo: int = Field(default=0, title="예약주문번호")
    """ 예약주문번호 """
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


class CSPAT00701Response(BaseModel):
    """
    CSPAT00701 API 전체 응답 - 현물정정주문

    Attributes:
        header (Optional[CSPAT00701ResponseHeader])
        block1 (Optional[CSPAT00701OutBlock1]): 입력 echo-back
        block2 (Optional[CSPAT00701OutBlock2]): 정정 결과 (주문번호, 모주문번호 등)
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[CSPAT00701ResponseHeader] = None
    block1: Optional[CSPAT00701OutBlock1] = Field(
        None,
        title="입력 echo-back",
        description="정정주문 입력 파라미터 echo-back 블록"
    )
    block2: Optional[CSPAT00701OutBlock2] = Field(
        None,
        title="정정 결과",
        description="주문번호, 모주문번호, 주문시각, 주문금액 등 정정 접수 결과"
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
