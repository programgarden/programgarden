from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1471RequestHeader(BlockRequestHeader):
    """t1471 요청용 Header"""
    pass


class T1471ResponseHeader(BlockResponseHeader):
    """t1471 응답용 Header"""
    pass


class T1471InBlock(BaseModel):
    """
    t1471InBlock - 시간대별호가잔량추이 입력 블록

    Attributes:
        shcode (str): 종목코드
        gubun (str): 분구분 (00:30초 01:1분 02:2분 03:3분 ...)
        time (str): 시간 (연속조회시 OutBlock의 time 값)
        cnt (str): 자료개수 (1~500, ex: "010")
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    shcode: str
    """ 종목코드 """
    gubun: str = "01"
    """ 분구분 (00:30초 01:1분 02:2분 03:3분 ...) """
    time: str = " "
    """ 시간 (연속조회키) """
    cnt: str = "010"
    """ 자료개수 (1~500) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1471Request(BaseModel):
    """T1471 API 요청 - 시간대별호가잔량추이"""
    header: T1471RequestHeader = T1471RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1471",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1471InBlock"], T1471InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1471"
    )


class T1471OutBlock(BaseModel):
    """t1471OutBlock - 연속조회 블록 (현재가 정보 포함)"""
    time: str
    """ 시간CTS """
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


class T1471OutBlock1(BaseModel):
    """t1471OutBlock1 - 시간대별 호가잔량 정보"""
    time: str
    """ 체결시간 """
    preoffercha1: int
    """ 매도증감 """
    offerrem1: int
    """ 매도우선잔량 """
    offerho1: int
    """ 매도우선호가 """
    bidho1: int
    """ 매수우선호가 """
    bidrem1: int
    """ 매수우선잔량 """
    prebidcha1: int
    """ 매수증감 """
    totofferrem: int
    """ 총매도 """
    totbidrem: int
    """ 총매수 """
    totsun: int
    """ 순매수 """
    msrate: float
    """ 매수비율 """
    close: int
    """ 종가 """


class T1471Response(BaseModel):
    """T1471 API 전체 응답 - 시간대별호가잔량추이"""
    header: Optional[T1471ResponseHeader]
    cont_block: Optional[T1471OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1471OutBlock1] = Field(default_factory=list, title="호가잔량 리스트")
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
