from typing import Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAT00400RequestHeader(BlockRequestHeader):
    pass


class COSAT00400ResponseHeader(BlockResponseHeader):
    pass


class COSAT00400InBlock1(BaseModel):
    """
    COSAT00400InBlock1 데이터 블록 (예약주문 등록/취소 입력)
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드 갯수 (예: 1)"""
    TrxTpCode: str = Field(..., title="처리구분코드", description="처리구분코드")
    """처리구분코드"""
    CntryCode: str = Field(..., title="국가코드", description="국가코드")
    """국가코드"""
    RsvOrdInptDt: str = Field(..., title="예약주문입력일자", description="예약주문입력일자 YYYYMMDD")
    """예약주문입력일자 (YYYYMMDD)"""
    RsvOrdNo: Optional[int] = Field(default=None, title="예약주문번호", description="예약주문번호")
    """예약주문번호 (등록/취소 시 사용)"""
    BnsTpCode: str = Field(..., title="매매구분코드", description="매매구분코드")
    """매매구분코드 (매수/매도 등)"""
    AcntNo: str = Field(..., title="계좌번호", description="계좌번호")
    """계좌번호"""
    Pwd: str = Field(..., title="비밀번호", description="비밀번호")
    """비밀번호"""
    FcurrMktCode: str = Field(..., title="외화시장코드", description="외화시장코드")
    """외화시장코드"""
    IsuNo: str = Field(..., title="종목번호", description="단축종목코드")
    """종목번호 (단축종목코드)"""
    OrdQty: int = Field(..., title="주문수량", description="주문수량")
    """주문수량"""
    OvrsOrdPrc: float = Field(..., title="해외주문가", description="해외주문가")
    """해외주문가"""
    OrdprcPtnCode: str = Field(..., title="호가유형코드", description="호가유형코드")
    """호가유형코드"""
    RsvOrdSrtDt: str = Field(..., title="예약주문시작일자", description="예약주문 시작일자 YYYYMMDD")
    """예약주문 시작일자 (YYYYMMDD)"""
    RsvOrdEndDt: str = Field(..., title="예약주문종료일자", description="예약주문 종료일자 YYYYMMDD")
    """예약주문 종료일자 (YYYYMMDD)"""
    RsvOrdCndiCode: str = Field(..., title="예약주문조건코드", description="예약주문 조건 코드")
    """예약주문 조건 코드"""
    MgntrnCode: str = Field(..., title="신용거래코드", description="신용거래코드")
    """신용거래 코드"""
    LoanDt: str = Field(..., title="대출일자", description="대출일자 YYYYMMDD")
    """대출일자 (YYYYMMDD)"""
    LoanDtlClssCode: str = Field(..., title="대출상세분류코드", description="대출상세분류코드")
    """대출 상세 분류 코드"""


class COSAT00400Request(BaseModel):
    """
    COSAT00400 API 요청 클래스.

    Attributes:
        header (COSAT00400RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["COSAT00400InBlock1"], COSAT00400InBlock1]): 입력 데이터 블록.
        options (SetupOptions): 설정 옵션.
    """
    header: COSAT00400RequestHeader = Field(
        COSAT00400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAT00400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="COSAT00400 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[str, COSAT00400InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="예약주문 입력 데이터 블록"
    )
    """입력 데이터 블록 (키: 'COSAT00400InBlock1')"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=10,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAT00400"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """실행 전 설정 옵션 (rate limit 등)"""


class COSAT00400OutBlock1(BaseModel):
    RecCnt: int = Field(default=0, title="레코드갯수", description="응답된 레코드 개수")
    """응답된 레코드 개수"""
    TrxTpCode: str = Field(default="", title="처리구분코드", description="처리구분코드")
    """처리구분코드"""
    CntryCode: str = Field(default="", title="국가코드", description="국가코드")
    """국가코드"""
    RsvOrdInptDt: str = Field(default="", title="예약주문입력일자", description="예약주문입력일자")
    """예약주문입력일자"""
    RsvOrdNo: Optional[int] = Field(default=None, title="예약주문번호", description="예약주문번호")
    """예약주문번호"""
    BnsTpCode: str = Field(default="", title="매매구분코드", description="매매구분코드")
    """매매구분코드"""
    AcntNo: str = Field(default="", title="계좌번호", description="계좌번호")
    """계좌번호"""
    Pwd: str = Field(default="", title="비밀번호", description="비밀번호")
    """비밀번호"""
    FcurrMktCode: str = Field(default="", title="외화시장코드", description="외화시장코드")
    """외화시장코드"""
    IsuNo: str = Field(default="", title="종목번호", description="종목번호")
    """종목번호"""
    OrdQty: int = Field(default=0, title="주문수량", description="주문수량")
    """주문수량"""
    OvrsOrdPrc: float = Field(default=0.0, title="해외주문가", description="해외주문가")
    """해외주문가"""
    RegCommdaCode: str = Field(default="", title="등록통신매체코드", description="등록통신매체코드")
    """등록통신매체코드"""
    OrdprcPtnCode: str = Field(default="", title="호가유형코드", description="호가유형코드")
    """호가유형코드"""
    RsvOrdSrtDt: str = Field(default="", title="예약주문시작일자", description="예약주문 시작일자")
    """예약주문 시작일자"""
    RsvOrdEndDt: str = Field(default="", title="예약주문종료일자", description="예약주문 종료일자")
    """예약주문 종료일자"""
    RsvOrdCndiCode: str = Field(default="", title="예약주문조건코드", description="예약주문조건코드")
    """예약주문 조건 코드"""
    MgntrnCode: str = Field(default="", title="신용거래코드", description="신용거래코드")
    """신용거래 코드"""
    LoanDt: str = Field(default="", title="대출일자", description="대출일자")
    """대출일자"""
    LoanDtlClssCode: str = Field(default="", title="대출상세분류코드", description="대출상세분류코드")
    """대출 상세 분류 코드"""


class COSAT00400OutBlock2(BaseModel):
    RecCnt: int = Field(default=0, title="레코드갯수", description="응답된 레코드 개수")
    """응답된 레코드 개수"""
    RsvOrdNo: Optional[int] = Field(default=None, title="예약주문번호", description="예약주문번호")
    """예약주문번호"""


class COSAT00400Response(BaseModel):
    """
    COSAT00400 API에 대한 응답 클래스.

    Attributes:
        header (Optional[COSAT00400ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[COSAT00400OutBlock1]): 첫번째 출력 블록
        block2 (Optional[COSAT00400OutBlock2]): 두번째 출력 블록
        rsp_cd (str): 응답 코드
        rsp_msg (str): 응답 메시지
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[COSAT00400ResponseHeader] = Field(None, title="요청 헤더 데이터 블록", description="응답 헤더 데이터 블록")
    """요청 헤더 데이터 블록 (응답)"""
    block1: Optional[COSAT00400OutBlock1] = Field(None, title="첫번째 출력 블록", description="COSAT00400OutBlock1")
    """첫번째 출력 블록 (COSAT00400OutBlock1)"""
    block2: Optional[COSAT00400OutBlock2] = Field(None, title="두번째 출력 블록", description="COSAT00400OutBlock2")
    """두번째 출력 블록 (COSAT00400OutBlock2)"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(..., title="응답 코드", description="응답 코드")
    """응답 코드set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )"""
    rsp_msg: str = Field(..., title="응답 메시지", description="응답 메시지")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지", description="오류 메시지")
    """오류 메시지 (있으면)"""

    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
