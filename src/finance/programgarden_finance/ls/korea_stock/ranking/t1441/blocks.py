from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1441RequestHeader(BlockRequestHeader):
    """t1441 요청용 Header"""
    pass


class T1441ResponseHeader(BlockResponseHeader):
    """t1441 응답용 Header"""
    pass


class T1441InBlock(BaseModel):
    """
    t1441InBlock - 등락율상위 입력 블록

    Attributes:
        gubun1 (str): 구분 (0:전체 1:코스피 2:코스닥)
        gubun2 (str): 상승하락 (0:상승률 1:하락률 2:보합)
        gubun3 (str): 당일전일 (0:당일 1:전일)
        jc_num (int): 대상제외 비트마스크
        sprice (int): 시작가격
        eprice (int): 종료가격
        volume (int): 거래량
        idx (int): 연속조회키
        jc_num2 (int): 대상제외2 비트마스크
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    gubun1: Literal["0", "1", "2"]
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    gubun2: Literal["0", "1", "2"]
    """ 상승하락 (0:상승률 1:하락률 2:보합) """
    gubun3: Literal["0", "1"]
    """ 당일전일 (0:당일 1:전일) """
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


class T1441Request(BaseModel):
    """T1441 API 요청 - 등락율상위"""
    header: T1441RequestHeader = T1441RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1441",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1441InBlock"], T1441InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1441"
    )


class T1441OutBlock(BaseModel):
    """t1441OutBlock - 연속조회 블록"""
    idx: int
    """ 연속조회키 """


class T1441OutBlock1(BaseModel):
    """t1441OutBlock1 - 등락율상위 종목 정보"""
    hname: str
    """ 한글명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    volume: int
    """ 누적거래량 """
    offerrem1: int
    """ 매도잔량 """
    offerho1: int
    """ 매도호가 """
    bidho1: int
    """ 매수호가 """
    bidrem1: int
    """ 매수잔량 """
    updaycnt: int
    """ 연속일수 """
    jnildiff: float
    """ 전일등락율 """
    shcode: str
    """ 종목코드 """
    open: int
    """ 시가 """
    high: int
    """ 고가 """
    low: int
    """ 저가 """
    voldiff: float
    """ 거래량대비율 """
    value: int
    """ 거래대금 """
    total: int
    """ 시가총액 """
    ex_shcode: str = ""
    """ 거래소별단축코드 """


class T1441Response(BaseModel):
    """T1441 API 전체 응답 - 등락율상위"""
    header: Optional[T1441ResponseHeader]
    cont_block: Optional[T1441OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1441OutBlock1] = Field(default_factory=list, title="등락율상위 종목 리스트")
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
