from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1404RequestHeader(BlockRequestHeader):
    """t1404 요청용 Header"""
    pass


class T1404ResponseHeader(BlockResponseHeader):
    """t1404 응답용 Header"""
    pass


class T1404InBlock(BaseModel):
    """
    t1404InBlock - 관리/불성실/투자유의조회 입력 블록

    Attributes:
        gubun (str): 구분 (0:전체 1:코스피 2:코스닥)
        jongchk (str): 종목체크 (1:관리 2:불성실공시 3:투자유의 4:투자환기)
        cts_shcode (str): 종목코드_CTS (연속조회키)
    """
    gubun: str
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    jongchk: str
    """ 종목체크 (1:관리 2:불성실공시 3:투자유의 4:투자환기) """
    cts_shcode: str = " "
    """ 종목코드_CTS (연속조회키) """


class T1404Request(BaseModel):
    """T1404 API 요청 - 관리/불성실/투자유의조회"""
    header: T1404RequestHeader = T1404RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1404",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1404InBlock"], T1404InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1404"
    )


class T1404OutBlock(BaseModel):
    """t1404OutBlock - 연속조회 블록"""
    cts_shcode: str
    """ 종목코드_CTS """


class T1404OutBlock1(BaseModel):
    """t1404OutBlock1 - 관리/불성실/투자유의 종목 정보"""
    hname: str
    """ 한글명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    volume: int
    """ 누적거래량 """
    date: str
    """ 지정일 """
    tprice: int
    """ 지정일주가 """
    tchange: int
    """ 지정일대비 """
    tdiff: float
    """ 대비율(%) """
    reason: str
    """ 사유 """
    shcode: str
    """ 종목코드 """
    edate: str
    """ 해제일 """


class T1404Response(BaseModel):
    """T1404 API 전체 응답 - 관리/불성실/투자유의조회"""
    header: Optional[T1404ResponseHeader]
    cont_block: Optional[T1404OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1404OutBlock1] = Field(default_factory=list, title="관리/불성실/투자유의 종목 리스트")
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
