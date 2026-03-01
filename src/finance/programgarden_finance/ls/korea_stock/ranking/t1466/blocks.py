from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1466RequestHeader(BlockRequestHeader):
    """t1466 요청용 Header"""
    pass


class T1466ResponseHeader(BlockResponseHeader):
    """t1466 응답용 Header"""
    pass


class T1466InBlock(BaseModel):
    """
    t1466InBlock - 전일동시간대비거래급증 입력 블록

    Attributes:
        gubun (str): 구분 (0:전체 1:코스피 2:코스닥)
        type1 (str): 전일거래량 (0:1주이상 1:1만주이상 2:5만주이상 3:10만주이상 4:20만주이상 5:50만주이상 6:100만주이상)
        type2 (str): 거래급등율 (0:전체 1:2000%이하 2:1500%이하 3:1000%이하 4:500%이하 5:100%이하 6:50%이하)
        jc_num (int): 대상제외 비트마스크
        sprice (int): 시작가격
        eprice (int): 종료가격
        volume (int): 거래량
        idx (int): 연속조회키
        jc_num2 (int): 대상제외2 비트마스크
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    gubun: Literal["0", "1", "2"]
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    type1: Literal["0", "1", "2", "3", "4", "5", "6"]
    """ 전일거래량 (0:1주이상 ~ 6:100만주이상) """
    type2: Literal["0", "1", "2", "3", "4", "5", "6"]
    """ 거래급등율 (0:전체 ~ 6:50%이하) """
    jc_num: int = 0
    """ 대상제외 비트마스크 """
    sprice: int = 0
    """ 시작가격 """
    eprice: int = 0
    """ 종료가격 """
    volume: int = 0
    """ 거래량 """
    idx: int = 0
    """ 연속조회키 (최초 0) """
    jc_num2: int = 0
    """ 대상제외2 비트마스크 """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1466Request(BaseModel):
    """T1466 API 요청 - 전일동시간대비거래급증"""
    header: T1466RequestHeader = T1466RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1466",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1466InBlock"], T1466InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1466"
    )


class T1466OutBlock(BaseModel):
    """t1466OutBlock - 연속조회 블록"""
    hhmm: str
    """ 현재시분 """
    idx: int
    """ 연속조회키 """


class T1466OutBlock1(BaseModel):
    """t1466OutBlock1 - 전일동시간대비거래급증 종목 정보"""
    shcode: str
    """ 종목코드 """
    hname: str
    """ 종목명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    stdvolume: int
    """ 전일거래량 """
    volume: int
    """ 당일거래량 """
    voldiff: float
    """ 거래급등율(%) """
    open: int
    """ 시가 """
    high: int
    """ 고가 """
    low: int
    """ 저가 """
    ex_shcode: str = ""
    """ 거래소별단축코드 """


class T1466Response(BaseModel):
    """T1466 API 전체 응답 - 전일동시간대비거래급증"""
    header: Optional[T1466ResponseHeader]
    cont_block: Optional[T1466OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1466OutBlock1] = Field(default_factory=list, title="거래급증 종목 리스트")
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
