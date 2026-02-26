from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1405RequestHeader(BlockRequestHeader):
    """t1405 요청용 Header"""
    pass


class T1405ResponseHeader(BlockResponseHeader):
    """t1405 응답용 Header"""
    pass


class T1405InBlock(BaseModel):
    """
    t1405InBlock - 투자경고/매매정지/정리매매조회 입력 블록

    Attributes:
        gubun (str): 구분 (0:전체 1:코스피 2:코스닥)
        jongchk (str): 종목체크 (1:투자경고 2:매매정지 3:정리매매 4:투자주의 5:투자위험 6:위험예고 7:단기과열지정 8:이상급등종목 9:상장주식수부족)
        cts_shcode (str): 종목코드_CTS (연속조회키)
    """
    gubun: str
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    jongchk: str
    """ 종목체크 (1:투자경고 2:매매정지 3:정리매매 4:투자주의 5:투자위험 6:위험예고 7:단기과열지정 8:이상급등종목 9:상장주식수부족) """
    cts_shcode: str = " "
    """ 종목코드_CTS (연속조회키) """


class T1405Request(BaseModel):
    """T1405 API 요청 - 투자경고/매매정지/정리매매조회"""
    header: T1405RequestHeader = T1405RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1405",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1405InBlock"], T1405InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1405"
    )


class T1405OutBlock(BaseModel):
    """t1405OutBlock - 연속조회 블록"""
    cts_shcode: str
    """ 종목코드_CTS """


class T1405OutBlock1(BaseModel):
    """t1405OutBlock1 - 투자경고/매매정지/정리매매 종목 정보"""
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
    edate: str
    """ 해제일 """
    shcode: str
    """ 종목코드 """


class T1405Response(BaseModel):
    """T1405 API 전체 응답 - 투자경고/매매정지/정리매매조회"""
    header: Optional[T1405ResponseHeader]
    cont_block: Optional[T1405OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1405OutBlock1] = Field(default_factory=list, title="투자경고/매매정지/정리매매 종목 리스트")
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
