from typing import Literal, Optional
from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBT01000RequestHeader(BlockRequestHeader):
    pass


class CIDBT01000ResponseHeader(BlockResponseHeader):
    pass


class CIDBT01000InBlock1(BaseModel):
    """
    CIDBT01000InBlock1 데이터 블록 (해외선물 취소주문)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdDt (str): 주문일자 (YYYYMMDD)
        IsuCodeVal (str): 종목코드값
        OvrsFutsOrgOrdNo (str): 해외선물원주문번호
        FutsOrdTpCode (Literal["3"]): 선물주문구분코드 (3:취소)
        PrdtTpCode (str): 상품구분코드
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
    IsuCodeVal: str = Field(
        ...,
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""
    OvrsFutsOrgOrdNo: str = Field(
        ...,
        title="해외선물원주문번호",
        description="해외선물원주문번호"
    )
    """해외선물원주문번호"""
    FutsOrdTpCode: Literal["3"] = Field(
        ...,
        title="선물주문구분코드",
        description="3:취소"
    )
    """선물주문구분코드 (3:취소)"""
    PrdtTpCode: str = Field(
        " ",
        title="상품구분코드",
        description="상품구분코드 (SPACE 허용)"
    )
    """상품구분코드"""
    ExchCode: str = Field(
        " ",
        title="거래소코드",
        description="거래소코드 (SPACE 허용)"
    )
    """거래소코드"""


class CIDBT01000Request(BaseModel):
    """
    CIDBT01000 API 요청 클래스.

    Attributes:
        header (CIDBT01000RequestHeader): 요청 헤더 데이터 블록.
        body (dict[Literal["CIDBT01000InBlock1"], CIDBT01000InBlock1]): 입력 데이터 블록.
        options (SetupOptions): 설정 옵션.
    """
    header: CIDBT01000RequestHeader = Field(
        CIDBT01000RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBT01000",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBT01000 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[str, CIDBT01000InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="해외선물 취소주문 입력 데이터 블록"
    )
    """입력 데이터 블록 (키: 'CIDBT01000InBlock1')"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=5,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBT01000"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """실행 전 설정 옵션 (rate limit 등)"""


class CIDBT01000OutBlock1(BaseModel):
    """
    CIDBT01000OutBlock1 데이터 블록 (응답)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdDt (str): 주문일자
        BrnNo (str): 지점번호
        AcntNo (str): 계좌번호
        Pwd (str): 비밀번호
        IsuCodeVal (str): 종목코드값
        OvrsFutsOrgOrdNo (str): 해외선물원주문번호
        FutsOrdTpCode (str): 선물주문구분코드
        PrdtTpCode (str): 상품구분코드
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
    BrnNo: str = Field(
        default="",
        title="지점번호",
        description="지점번호"
    )
    """지점번호"""
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
    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""
    OvrsFutsOrgOrdNo: str = Field(
        default="",
        title="해외선물원주문번호",
        description="해외선물원주문번호"
    )
    """해외선물원주문번호"""
    FutsOrdTpCode: str = Field(
        default="",
        title="선물주문구분코드",
        description="선물주문구분코드"
    )
    """선물주문구분코드"""
    PrdtTpCode: str = Field(
        default="",
        title="상품구분코드",
        description="상품구분코드"
    )
    """상품구분코드"""
    ExchCode: str = Field(
        default="",
        title="거래소코드",
        description="거래소코드"
    )
    """거래소코드"""


class CIDBT01000OutBlock2(BaseModel):
    """
    CIDBT01000OutBlock2 데이터 블록 (응답)

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


class CIDBT01000Response(BaseModel):
    """
    CIDBT01000 API에 대한 응답 클래스.

    Attributes:
        header (Optional[CIDBT01000ResponseHeader]): 요청 헤더 데이터 블록
        block1 (Optional[CIDBT01000OutBlock1]): 첫번째 출력 블록
        block2 (Optional[CIDBT01000OutBlock2]): 두번째 출력 블록
        rsp_cd (str): 응답 코드
        rsp_msg (str): 응답 메시지
        error_msg (Optional[str]): 오류 메시지
    """
    header: Optional[CIDBT01000ResponseHeader] = Field(
        None,
        title="요청 헤더 데이터 블록",
        description="CIDBT01000 API 응답을 위한 요청 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록 (응답)"""
    block1: Optional[CIDBT01000OutBlock1] = Field(
        None,
        title="첫번째 출력 블록",
        description="CIDBT01000 API 응답의 첫번째 출력 블록"
    )
    """첫번째 출력 블록 (CIDBT01000OutBlock1)"""
    block2: Optional[CIDBT01000OutBlock2] = Field(
        None,
        title="두번째 출력 블록",
        description="CIDBT01000 API 응답의 두번째 출력 블록"
    )
    """두번째 출력 블록 (CIDBT01000OutBlock2)"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    """HTTP 상태 코드"""
    rsp_cd: str = Field(
        ...,
        title="응답 코드",
        description="CIDBT01000 API 응답의 상태 코드"
    )
    """응답 코드"""
    rsp_msg: str = Field(
        ...,
        title="응답 메시지",
        description="CIDBT01000 API 응답의 상태 메시지"
    )
    """응답 메시지"""
    error_msg: Optional[str] = Field(
        None,
        title="오류 메시지",
        description="CIDBT01000 API 응답의 오류 메시지"
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
