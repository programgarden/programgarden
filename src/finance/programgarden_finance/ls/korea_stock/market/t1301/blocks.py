from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1301RequestHeader(BlockRequestHeader):
    """t1301 요청용 Header"""
    pass


class T1301ResponseHeader(BlockResponseHeader):
    """t1301 응답용 Header"""
    pass


class T1301InBlock(BaseModel):
    """
    t1301InBlock - 주식시간대별체결조회 입력 블록

    Attributes:
        shcode (str): 단축코드
        cvolume (int): 특이거래량 (거래량 > 특이거래량)
        starttime (str): 시작시간 (장시작시간 이후)
        endtime (str): 종료시간 (장종료시간 이전)
        cts_time (str): 시간CTS (연속조회시 OutBlock의 동일필드 입력)
    """
    shcode: str
    """ 단축코드 """
    cvolume: int = 0
    """ 특이거래량 """
    starttime: str = ""
    """ 시작시간 """
    endtime: str = ""
    """ 종료시간 """
    cts_time: str = ""
    """ 시간CTS (연속조회키) """


class T1301Request(BaseModel):
    """T1301 API 요청 - 주식시간대별체결조회"""
    header: T1301RequestHeader = T1301RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1301",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1301InBlock"], T1301InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1301"
    )


class T1301OutBlock(BaseModel):
    """t1301OutBlock - 연속조회 블록"""
    cts_time: str
    """ 시간CTS """


class T1301OutBlock1(BaseModel):
    """t1301OutBlock1 - 시간대별 체결 정보"""
    chetime: str
    """ 시간 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    cvolume: int
    """ 체결수량 """
    chdegree: float
    """ 체결강도 """
    volume: int
    """ 거래량 """
    mdvolume: int
    """ 매도체결수량 """
    mdchecnt: int
    """ 매도체결건수 """
    msvolume: int
    """ 매수체결수량 """
    mschecnt: int
    """ 매수체결건수 """
    revolume: int
    """ 순체결량 """
    rechecnt: int
    """ 순체결건수 """


class T1301Response(BaseModel):
    """T1301 API 전체 응답 - 주식시간대별체결조회"""
    header: Optional[T1301ResponseHeader]
    cont_block: Optional[T1301OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1301OutBlock1] = Field(default_factory=list, title="시간대별 체결 리스트")
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
