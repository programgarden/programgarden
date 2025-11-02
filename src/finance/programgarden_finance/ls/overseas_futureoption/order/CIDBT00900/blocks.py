from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBT00900RequestHeader(BlockRequestHeader):
    pass


class CIDBT00900ResponseHeader(BlockResponseHeader):
    pass


class CIDBT00900InBlock1(BaseModel):
    """
    CIDBT00900InBlock1 데이터 블록

    Attributes:
        RecCnt (int): 레코드갯수
        OrdDt (str): 주문일자 (YYYYMMDD)
        OvrsFutsOrgOrdNo (str): 해외선물원주문번호
        IsuCodeVal (str): 종목코드값
        FutsOrdTpCode (Literal["2"]): 선물주문구분코드 (2:정정)
        BnsTpCode (Literal["1","2"]): 매매구분코드 (1:매도, 2:매수)
        FutsOrdPtnCode (Literal["2"]): 선물주문유형코드 (2:지정가)
        CrcyCodeVal (str): 통화코드값
        OvrsDrvtOrdPrc (float): 해외파생주문가격
        CndiOrdPrc (float): 조건주문가격
        OrdQty (int): 주문수량
        OvrsDrvtPrdtCode (str): 해외파생상품코드
        DueYymm (str): 만기년월
        ExchCode (str): 거래소코드
    """
    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드갯수 (예: 1)"
    )
    """레코드 갯수 (예: 1)"""
    OrdDt: str = Field(
        ...,
        title="주문일자",
        description="YYYYMMDD 형식"
    )
    """주문일자 (YYYYMMDD)"""
    OvrsFutsOrgOrdNo: str = Field(
        ...,
        title="해외선물원주문번호",
        description="해외선물원주문번호"
    )
    """해외선물원주문번호"""
    IsuCodeVal: str = Field(
        ...,
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""
    FutsOrdTpCode: Literal["2"] = Field(
        ...,
        title="선물주문구분코드",
        description="2:정정"
    )
    """선물주문구분코드 (2:정정)"""
    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="매매구분코드",
        description="1:매도, 2:매수"
    )
    """매매구분코드 1:매도, 2:매수"""
    FutsOrdPtnCode: Literal["2"] = Field(
        ...,
        title="선물주문유형코드",
        description="2:지정가"
    )
    """선물주문유형코드 2:지정가"""
    CrcyCodeVal: str = Field(
        "",
        title="통화코드값",
        description="통화코드값 (공백 허용)"
    )
    """통화코드값 (공백 허용)"""
    OvrsDrvtOrdPrc: float = Field(
        ...,
        title="해외파생주문가격",
        description="해외파생주문가격"
    )
    """해외파생주문가격"""
    CndiOrdPrc: float = Field(
        ...,
        title="조건주문가격",
        description="조건주문가격"
    )
    """조건주문가격"""
    OrdQty: int = Field(
        ...,
        title="주문수량",
        description="주문수량"
    )
    """주문수량"""
    OvrsDrvtPrdtCode: str = Field(
        "",
        title="해외파생상품코드",
        description="해외파생상품코드 (공백 허용)"
    )
    """해외파생상품코드"""
    DueYymm: str = Field(
        "",
        title="만기년월",
        description="만기년월 (YYMM)"
    )
    """만기년월"""
    ExchCode: str = Field(
        "",
        title="거래소코드",
        description="거래소코드 (공백 허용)"
    )
    """거래소코드"""


class CIDBT00900Request(BaseModel):
    """
    CIDBT00900 API 요청 클래스.

    Attributes:
        header (CIDBT00900RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["CIDBT00900InBlock1"], CIDBT00900InBlock1]): 입력 데이터 블록.
        options (SetupOptions): 설정 옵션.
    """
    header: CIDBT00900RequestHeader = Field(
        CIDBT00900RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBT00900",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBT00900 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[str, CIDBT00900InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 정정주문 입력 데이터 블록"
    )
    """입력 데이터 블록 (키: 'CIDBT00900InBlock1')"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=5,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBT00900"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """실행 전 설정 옵션 (rate limit 등)"""


class CIDBT00900OutBlock1(BaseModel):
    """
    CIDBT00900OutBlock1 데이터 블록 (응답)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdDt (str): 주문일자
        RegBrnNo (str): 등록지점번호
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        OvrsFutsOrgOrdNo (str): 해외선물원주문번호
        IsuCodeVal (str): 종목코드값
        FutsOrdTpCode (str): 선물주문구분코드
        BnsTpCode (str): 매매구분코드
        FutsOrdPtnCode (str): 선물주문유형코드
        CrcyCodeVal (str): 통화코드값
        OvrsDrvtOrdPrc (float): 해외파생주문가격
        CndiOrdPrc (float): 조건주문가격
        OrdQty (int): 주문수량
        OvrsDrvtPrdtCode (str): 해외파생상품코드
        DueYymm (str): 만기년월
        ExchCode (str): 거래소코드
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """응답된 레코드 개수"""
    OrdDt: str = Field(
        default="",
        title="주문일자",
        description="주문일자"
    )
    """주문일자"""
    RegBrnNo: str = Field(
        default="",
        title="등록지점번호",
        description="등록지점번호"
    )
    """등록지점번호"""
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""
    Pwd: str = Field(
        default="",
        title="비밀번호",
        description="비밀번호"
    )
    """비밀번호"""
    OvrsFutsOrgOrdNo: str = Field(
        default="",
        title="해외선물원주문번호",
        description="해외선물원주문번호"
    )
    """해외선물원주문번호"""
    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""
    FutsOrdTpCode: str = Field(
        default="",
        title="선물주문구분코드",
        description="선물주문구분코드"
    )
    """선물주문구분코드"""
    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="매매구분코드"
    )
    """매매구분코드"""
    FutsOrdPtnCode: str = Field(
        default="",
        title="선물주문유형코드",
        description="선물주문유형코드"
    )
    """선물주문유형코드"""
    CrcyCodeVal: str = Field(
        default="",
        title="통화코드값",
        description="통화코드값"
    )
    """통화코드값"""
    OvrsDrvtOrdPrc: float = Field(
        default=0.0,
        title="해외파생주문가격",
        description="해외파생주문가격"
    )
    """해외파생주문가격"""
    CndiOrdPrc: float = Field(
        default=0.0,
        title="조건주문가격",
        description="조건주문가격"
    )
    """조건주문가격"""
    OrdQty: int = Field(
        default=0,
        title="주문수량",
        description="주문수량"
    )
    """주문수량"""
    OvrsDrvtPrdtCode: str = Field(
        default="",
        title="해외파생상품코드",
        description="해외파생상품코드"
    )
    """해외파생상품코드"""
    DueYymm: str = Field(
        default="",
        title="만기년월",
        description="만기년월"
    )
    """만기년월"""
    ExchCode: str = Field(
        default="",
        title="거래소코드",
        description="거래소코드"
    )
    """거래소코드"""


class CIDBT00900OutBlock2(BaseModel):
    """
    CIDBT00900OutBlock2 데이터 블록 (응답)

    Attributes:
        RecCnt (int): 레코드갯수
        AcntNo (str): 계좌번호
        OvrsFutsOrdNo (str): 해외선물주문번호
        InnerMsgCnts (str): 내부메시지내용
    """
    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """응답된 레코드 개수"""
    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="계좌번호"
    )
    """계좌번호"""
    OvrsFutsOrdNo: str = Field(
        default="",
        title="해외선물주문번호",
        description="해외선물주문번호"
    )
    """해외선물주문번호"""
    InnerMsgCnts: str = Field(
        default="",
        title="내부메시지내용",
        description="내부메시지내용"
    )
    """내부메시지내용"""


class CIDBT00900Response(BaseModel):
    """
    CIDBT00900 API에 대한 응답 클래스.

    Attributes:
        header (Optional[CIDBT00900ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDBT00900OutBlock1]): 첫번째 출력 블록
        block2 (Optional[CIDBT00900OutBlock2]): 두번째 출력 블록
        rsp_cd (str): 응답 코드
        rsp_msg (str): 응답 메시지
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[CIDBT00900ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDBT00900 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록 (응답)"""
    block1: Optional[CIDBT00900OutBlock1] = Field(
        None,
        title="첫번째 출력 블록",
        description="CIDBT00900 API 응답의 첫번째 출력 블록"
    )
    """첫번째 출력 블록 (CIDBT00900OutBlock1)"""
    block2: Optional[CIDBT00900OutBlock2] = Field(
        None,
        title="두번째 출력 블록",
        description="CIDBT00900 API 응답의 두번째 출력 블록"
    )
    """두번째 출력 블록 (CIDBT00900OutBlock2)"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답 코드",
        description="CIDBT00900 API 응답의 상태 코드"
    )
    """응답 코드"""
    rsp_msg: str = Field(
        ...,
        title="응답 메시지",
        description="CIDBT00900 API 응답의 상태 메시지"
    )
    """응답 메시지"""
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="CIDBT00900 API 응답의 오류 메시지"
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
