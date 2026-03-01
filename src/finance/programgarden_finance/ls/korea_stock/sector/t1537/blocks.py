from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1537RequestHeader(BlockRequestHeader):
    """t1537 요청용 Header"""
    pass


class T1537ResponseHeader(BlockResponseHeader):
    """t1537 응답용 Header"""
    pass


class T1537InBlock(BaseModel):
    """
    t1537InBlock - 테마종목별시세조회 입력 블록

    Attributes:
        tmcode (str): 테마코드 (t8425 조회하여 확인 후 입력)
    """
    tmcode: str
    """ 테마코드 (t8425 조회하여 확인 후 입력) """


class T1537Request(BaseModel):
    """
    T1537 API 요청 - 테마종목별시세조회

    Attributes:
        header (T1537RequestHeader)
        body (Dict[Literal["t1537InBlock"], T1537InBlock])
    """
    header: T1537RequestHeader = T1537RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1537",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1537InBlock"], T1537InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1537"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1537OutBlock(BaseModel):
    """
    t1537OutBlock - 테마종목별시세 요약 블록
    """
    upcnt: int = 0
    """ 상승종목수 """
    tmcnt: int = 0
    """ 테마종목수 """
    uprate: int = 0
    """ 상승종목비율 """
    tmname: str = ""
    """ 테마명 """


class T1537OutBlock1(BaseModel):
    """
    t1537OutBlock1 - 테마종목별시세 종목 리스트
    """
    hname: str = ""
    """ 종목명 """
    price: int = 0
    """ 현재가 """
    sign: str = ""
    """ 전일대비구분 """
    change: int = 0
    """ 전일대비 """
    diff: float = 0.0
    """ 등락율 """
    volume: int = 0
    """ 누적거래량 """
    jniltime: float = 0.0
    """ 전일동시간 """
    shcode: str = ""
    """ 종목코드 """
    yeprice: int = 0
    """ 예상체결가 """
    open: int = 0
    """ 시가 """
    high: int = 0
    """ 고가 """
    low: int = 0
    """ 저가 """
    value: int = 0
    """ 누적거래대금(단위:백만) """
    marketcap: int = 0
    """ 시가총액(단위:백만) """


class T1537Response(BaseModel):
    """
    T1537 API 전체 응답 - 테마종목별시세조회
    """
    header: Optional[T1537ResponseHeader] = None
    cont_block: Optional[T1537OutBlock] = Field(
        None, title="테마 요약",
        description="테마 상승종목수, 종목수, 상승비율 등"
    )
    block: List[T1537OutBlock1] = Field(
        default_factory=list, title="종목 리스트",
        description="테마에 속한 종목 시세 리스트"
    )
    status_code: Optional[int] = Field(None, title="HTTP 상태 코드")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(None, title="오류메시지")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
