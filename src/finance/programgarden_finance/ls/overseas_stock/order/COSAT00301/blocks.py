
from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class COSAT00301RequestHeader(BlockRequestHeader):
    pass


class COSAT00301ResponseHeader(BlockResponseHeader):
    pass


class COSAT00301InBlock1(BaseModel):
    """
    COSAT00301InBlock1 데이터 블록

    Attributes:
        RecCnt (int): 레코드갯수
        OrdPtnCode (Literal["01", "02", "08"]): 주문유형코드 (01: 매도, 02: 매수, 08: 취소)
        OrgOrdNo (Optional[int]): 원주문번호 (취소주문만 필수)
        OrdMktCode (Literal["81", "82"]): 주문시장코드 (81: 뉴욕, 82: NASDAQ)
        IsuNo (str): 종목번호 (단축종목코드)
        OrdQty (int): 주문수량
        OvrsOrdPrc (float): 해외주문가
        OrdprcPtnCode (Literal["00", "03", "M1", "M2", "M3", "M4"]): 호가유형코드 (00: 지정가, 03: 시장가, M1: LOO, M2: LOC, M3: MOO, M4: MOC)
        BrkTpCode (str): 중개인구분코드
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드 갯수 (예: 1)"""
    OrdPtnCode: Literal["01", "02", "08"] = Field(
        ...,
        title="주문유형코드",
        description="01: 매도, 02: 매수, 08: 취소"
    )
    """주문유형코드 01: 매도, 02: 매수, 08: 취소"""
    OrgOrdNo: Optional[int] = Field(
        default=None,
        title="원주문번호",
        description="취소주문인 경우만 필수 입력"
    )
    """원주문번호 (취소주문인 경우 필수)"""
    OrdMktCode: Literal["81", "82"] = Field(
        ...,
        title="주문시장코드",
        description="81: 뉴욕, 82: NASDAQ"
    )
    """주문시장코드 81: 뉴욕, 82: NASDAQ"""
    IsuNo: str = Field(
        ...,
        title="종목번호",
        description="단축종목코드 (예: TSLA)"
    )
    """종목번호 (단축종목코드, 예: TSLA)"""
    OrdQty: int = Field(
        ...,
        title="주문수량",
        description="주문수량"
    )
    """주문수량"""
    OvrsOrdPrc: float = Field(
        ...,
        title="해외주문가",
        description="해외주문가"
    )
    """해외주문가"""
    OrdprcPtnCode: Literal["00", "03", "M1", "M2", "M3", "M4"] = Field(
        ...,
        title="호가유형코드",
        description="00: 지정가, 03: 시장가, M1: LOO, M2: LOC, M3: MOO, M4: MOC"
    )
    """호가유형코드 (예: 00=지정가, 03=시장가, M1=LOO, M2=LOC, M3=MOO, M4=MOC)"""
    BrkTpCode: str = Field(
        "",
        title="중개인구분코드",
        description="중개인구분코드"
    )
    """중개인구분코드"""


class COSAT00301Request(BaseModel):
    """
    COSAT00301 API 요청 클래스.

    Attributes:
        header (COSAT00301RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["COSAT00301InBlock1"], COSAT00301InBlock1]): 입력 데이터 블록.
        options (SetupOptions): 설정 옵션.
    """
    header: COSAT00301RequestHeader = Field(
        COSAT00301RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="COSAT00301",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="COSAT00301 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[str, COSAT00301InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="미국시장주문 입력 데이터 블록"
    )
    """입력 데이터 블록 (키: 'COSAT00301InBlock1')"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=10,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="COSAT00301"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """실행 전 설정 옵션 (rate limit 등)"""


class COSAT00301OutBlock1(BaseModel):
    """
    COSAT00301OutBlock1 데이터 블록 (응답)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdPtnCode (str): 주문유형코드
        OrgOrdNo (Optional[int]): 원주문번호
        AcntNo (str): 계좌번호
        InptPwd (str): 입력비밀번호
        OrdMktCode (str): 주문시장코드
        IsuNo (str): 종목번호
        OrdQty (int): 주문수량
        OvrsOrdPrc (float): 해외주문가
        OrdprcPtnCode (str): 호가유형코드
        RegCommdaCode (str): 등록통신매체코드
        BrkTpCode (str): 중개인구분코드
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """응답된 레코드 개수"""
    OrdPtnCode: str = Field(
        default="",
        title="주문유형코드",
        description="주문유형코드"
    )
    """주문유형코드"""
    OrgOrdNo: Optional[int] = Field(
        default=None,
        title="원주문번호",
        description="원주문번호"
    )
    """원주문번호"""
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""
    InptPwd: str = Field(
        default="",
        title="입력비밀번호",
        description="입력비밀번호"
    )
    """입력비밀번호"""
    OrdMktCode: str = Field(
        default="",
        title="주문시장코드",
        description="주문시장코드"
    )
    """주문시장코드"""
    IsuNo: str = Field(
        default="",
        title="종목번호",
        description="종목번호"
    )
    """종목번호"""
    OrdQty: int = Field(
        default=0,
        title="주문수량",
        description="주문수량"
    )
    """주문수량"""
    OvrsOrdPrc: float = Field(
        default=0.0,
        title="해외주문가",
        description="해외주문가"
    )
    """해외주문가"""
    OrdprcPtnCode: str = Field(
        default="",
        title="호가유형코드",
        description="호가유형코드"
    )
    """호가유형코드"""
    RegCommdaCode: str = Field(
        default="",
        title="등록통신매체코드",
        description="등록통신매체코드"
    )
    """등록통신매체코드"""
    BrkTpCode: str = Field(
        default="",
        title="중개인구분코드",
        description="중개인구분코드"
    )
    """중개인구분코드"""


class COSAT00301OutBlock2(BaseModel):
    """
    COSAT00301OutBlock2 데이터 블록 (응답)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdNo (int): 주문번호
        AcntNm (str): 계좌명
        IsuNm (str): 종목명
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """응답된 레코드 개수"""
    OrdNo: int = Field(
        default=0,
        title="주문번호",
        description="주문번호"
    )
    """주문번호"""
    AcntNm: str = Field(
        default="",
        title="계좌명",
        description="계좌명"
    )
    """계좌명"""
    IsuNm: str = Field(
        default="",
        title="종목명",
        description="종목명"
    )
    """종목명"""


class COSAT00301Response(BaseModel):
    """
    COSAT00301 API에 대한 응답 클래스.

    Attributes:
        header (Optional[COSAT00301ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[COSAT00301OutBlock1]): 첫번째 출력 블록
        block2 (Optional[COSAT00301OutBlock2]): 두번째 출력 블록
        rsp_cd (str): 응답 코드
        rsp_msg (str): 응답 메시지
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[COSAT00301ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="COSAT00301 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록 (응답)"""
    block1: Optional[COSAT00301OutBlock1] = Field(
        None,
        title="첫번째 출력 블록",
        description="COSAT00301 API 응답의 첫번째 출력 블록"
    )
    """첫번째 출력 블록 (COSAT00301OutBlock1)"""
    block2: Optional[COSAT00301OutBlock2] = Field(
        None,
        title="두번째 출력 블록",
        description="COSAT00301 API 응답의 두번째 출력 블록"
    )
    """두번째 출력 블록 (COSAT00301OutBlock2)"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답 코드",
        description="COSAT00301 API 응답의 상태 코드"
    )
    """응답 코드set_tr_header_options(
            token_manager=self.token_manager,
            header=header,
            options=options,
            request_data=request_data
        )"""
    rsp_msg: str = Field(
        ...,
        title="응답 메시지",
        description="COSAT00301 API 응답의 상태 메시지"
    )
    """응답 메시지"""
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="COSAT00301 API 응답의 오류 메시지"
    )
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
