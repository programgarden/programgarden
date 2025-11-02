from typing import Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class CIDBQ01400RequestHeader(BlockRequestHeader):
    pass


class CIDBQ01400ResponseHeader(BlockResponseHeader):
    pass


class CIDBQ01400InBlock1(BaseModel):
    """
    CIDBQ01400InBlock1 입력 블록

    Attributes:
        RecCnt (int): 레코드갯수
        QryTpCode (Literal["1", "2", "3"]): 조회구분코드 (1:신규 2:청산 3:총가능)
        IsuCodeVal (str): 종목코드값
        BnsTpCode (Literal["1", "2"]): 매매구분코드 (1:매도 2:매수)
        OvrsDrvtOrdPrc (float): 해외파생주문가격 (지정가; 시장가인 경우 0)
        AbrdFutsOrdPtnCode (Literal["1", "2"]): 해외선물주문유형코드 (1:시장가 2:지정가)
    """

    RecCnt: int = Field(
        default=1,
        title="레코드갯수",
        description="레코드 갯수"
    )
    """레코드갯수"""

    QryTpCode: Literal["1", "2", "3"] = Field(
        default="1",
        title="조회구분코드",
        description="1:신규 2:청산 3:총가능"
    )
    """조회구분코드 (1:신규 2:청산 3:총가능)"""

    IsuCodeVal: str = Field(
        ...,
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    BnsTpCode: Literal["1", "2"] = Field(
        ...,
        title="매매구분코드",
        description="1:매도 2:매수"
    )
    """매매구분코드 (1:매도 2:매수)"""

    OvrsDrvtOrdPrc: float = Field(
        ...,
        title="해외파생주문가격",
        description="지정가 (시장가인경우 0)"
    )
    """해외파생주문가격 (지정가; 시장가인 경우 0)"""

    AbrdFutsOrdPtnCode: Literal["1", "2"] = Field(
        ...,
        title="해외선물주문유형코드",
        description="1: 시장가 2: 지정가"
    )
    """해외선물주문유형코드 (1: 시장가 2: 지정가)"""


class CIDBQ01400Request(BaseModel):
    header: CIDBQ01400RequestHeader = Field(
        CIDBQ01400RequestHeader(
            content_type="application/json; charset=utf-8",
            authorization="",
            tr_cd="CIDBQ01400",
            tr_cont="N",
            tr_cont_key="",
            mac_address=""
        ),
        title="요청 헤더 데이터 블록",
        description="CIDBQ01400 API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["CIDBQ01400InBlock1"], CIDBQ01400InBlock1] = Field(
        ...,
        title="입력 데이터 블록",
        description="주문가능수량 조회를 위한 입력 데이터 블록"
    )
    """입력 데이터 블록"""
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="CIDBQ01400"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class CIDBQ01400OutBlock1(BaseModel):
    """
    CIDBQ01400OutBlock1 응답 기본 블록

    Attributes:
        RecCnt (int): 레코드갯수
        QryTpCode (str): 조회구분코드
        AcntNo (str): 계좌번호
        IsuCodeVal (str): 종목코드값
        BnsTpCode (str): 매매구분코드
        OvrsDrvtOrdPrc (str): 해외파생주문가격 (응답 예제는 문자열 포맷)
        AbrdFutsOrdPtnCode (str): 해외선물주문유형코드
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    QryTpCode: str = Field(
        default="",
        title="조회구분코드",
        description="조회구분코드"
    )
    """조회구분코드"""

    AcntNo: str = Field(
        default="",
        title="계좌번호",
        description="조회 대상 계좌 번호"
    )
    """계좌번호"""

    IsuCodeVal: str = Field(
        default="",
        title="종목코드값",
        description="종목코드값"
    )
    """종목코드값"""

    BnsTpCode: str = Field(
        default="",
        title="매매구분코드",
        description="매매구분코드"
    )
    """매매구분코드"""

    OvrsDrvtOrdPrc: str = Field(
        default="",
        title="해외파생주문가격",
        description="해외파생주문가격 (문자열 포맷으로 전달될 수 있음)"
    )
    """해외파생주문가격 (문자열 포맷)"""

    AbrdFutsOrdPtnCode: str = Field(
        default="",
        title="해외선물주문유형코드",
        description="해외선물주문유형코드"
    )
    """해외선물주문유형코드"""


class CIDBQ01400OutBlock2(BaseModel):
    """
    CIDBQ01400OutBlock2 응답 블록 (주문가능수량)

    Attributes:
        RecCnt (int): 레코드갯수
        OrdAbleQty (int): 주문가능수량
    """

    RecCnt: int = Field(
        default=0,
        title="레코드갯수",
        description="응답된 레코드 개수"
    )
    """레코드갯수"""

    OrdAbleQty: int = Field(
        default=0,
        title="주문가능수량",
        description="주문가능수량"
    )
    """주문가능수량"""


class CIDBQ01400Response(BaseModel):
    header: Optional[CIDBQ01400ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    """응답 헤더 데이터 블록"""
    block1: Optional[CIDBQ01400OutBlock1] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    """기본 응답 블록"""
    block2: Optional[CIDBQ01400OutBlock2] = Field(
        None,
        title="주문가능수량 블록",
        description="주문가능수량 블록"
    )
    """주문가능수량 블록"""
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    """응답코드"""
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    """응답메시지"""
    error_msg: Optional[str] = Field(None, title="오류메시지", description="오류메시지 (있으면)")
    """오류메시지 (있으면)"""

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
