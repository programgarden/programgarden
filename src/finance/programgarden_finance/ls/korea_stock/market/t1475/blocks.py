from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1475RequestHeader(BlockRequestHeader):
    """t1475 요청용 Header"""
    pass


class T1475ResponseHeader(BlockResponseHeader):
    """t1475 응답용 Header"""
    pass


class T1475InBlock(BaseModel):
    """
    t1475InBlock - 체결강도추이 입력 블록

    Attributes:
        shcode (str): 종목코드
        vptype (str): 상승하락 (0:시간별 1:일별)
        datacnt (int): 데이터개수 (스페이스시 최대 20개)
        date (int): 기준일자 (연속조회시 OutBlock.date 값)
        time (int): 기준시간 (연속조회시 OutBlock.time 값)
        rankcnt (int): 랭크카운터 (미사용)
        gubun (str): 조회구분 (0:일반조회 1:차트조회)
    """
    shcode: str
    """ 종목코드 """
    vptype: Literal["0", "1"] = "0"
    """ 상승하락 (0:시간별 1:일별) """
    datacnt: int = 0
    """ 데이터개수 """
    date: int = 0
    """ 기준일자 """
    time: int = 0
    """ 기준시간 """
    rankcnt: int = 0
    """ 랭크카운터 (미사용) """
    gubun: Literal["0", "1"] = "0"
    """ 조회구분 (0:일반조회 1:차트조회) """


class T1475Request(BaseModel):
    """T1475 API 요청 - 체결강도추이"""
    header: T1475RequestHeader = T1475RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1475",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1475InBlock"], T1475InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1475"
    )


class T1475OutBlock(BaseModel):
    """t1475OutBlock - 연속조회 블록"""
    date: int
    """ 기준일자 """
    time: int
    """ 기준시간 """
    rankcnt: int
    """ 랭크카운터 """


class T1475OutBlock1(BaseModel):
    """t1475OutBlock1 - 체결강도 정보"""
    datetime: str
    """ 일자 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    volume: int
    """ 거래량 """
    todayvp: float
    """ 당일VP """
    ma5vp: float
    """ 5일MAVP """
    ma20vp: float
    """ 20일MAVP """
    ma60vp: float
    """ 60일MAVP """


class T1475Response(BaseModel):
    """T1475 API 전체 응답 - 체결강도추이"""
    header: Optional[T1475ResponseHeader]
    cont_block: Optional[T1475OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1475OutBlock1] = Field(default_factory=list, title="체결강도 리스트")
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
