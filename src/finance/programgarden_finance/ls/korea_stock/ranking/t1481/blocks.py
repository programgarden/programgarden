from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1481RequestHeader(BlockRequestHeader):
    """t1481 요청용 Header"""
    pass


class T1481ResponseHeader(BlockResponseHeader):
    """t1481 응답용 Header"""
    pass


class T1481InBlock(BaseModel):
    """
    t1481InBlock - 시간외등락율상위 입력 블록

    Attributes:
        gubun1 (str): 구분 (0:전체 1:코스피 2:코스닥)
        gubun2 (str): 상승하락 (0:상승률 1:하락률)
        jongchk (str): 종목체크 (0:전체 1:우선제외 2:관리제외 3:우선관리제외)
        volume (str): 거래량 (0:전체 1:1천주이상 ~ 7:100만주이상)
        idx (int): 연속조회키
    """
    gubun1: Literal["0", "1", "2"]
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    gubun2: Literal["0", "1"]
    """ 상승하락 (0:상승률 1:하락률) """
    jongchk: Literal["0", "1", "2", "3"]
    """ 종목체크 (0:전체 1:우선제외 2:관리제외 3:우선관리제외) """
    volume: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    """ 거래량 (0:전체 1:1천주이상 2:5천주이상 3:1만주이상 4:5만주이상 5:10만주이상 6:50만주이상 7:100만주이상) """
    idx: int = 0
    """ 연속조회키 (최초 0) """


class T1481Request(BaseModel):
    """T1481 API 요청 - 시간외등락율상위"""
    header: T1481RequestHeader = T1481RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1481",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1481InBlock"], T1481InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1481"
    )


class T1481OutBlock(BaseModel):
    """t1481OutBlock - 연속조회 블록"""
    idx: int
    """ 연속조회키 """


class T1481OutBlock1(BaseModel):
    """t1481OutBlock1 - 시간외등락율상위 종목 정보"""
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
    offerrem1: int
    """ 매도잔량 """
    bidrem1: int
    """ 매수잔량 """
    offerho1: int
    """ 매도호가 """
    bidho1: int
    """ 매수호가 """
    shcode: str
    """ 종목코드 """
    value: int
    """ 누적거래대금 """
    total: int
    """ 시가총액(억) """


class T1481Response(BaseModel):
    """T1481 API 전체 응답 - 시간외등락율상위"""
    header: Optional[T1481ResponseHeader]
    cont_block: Optional[T1481OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1481OutBlock1] = Field(default_factory=list, title="시간외등락율상위 종목 리스트")
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
