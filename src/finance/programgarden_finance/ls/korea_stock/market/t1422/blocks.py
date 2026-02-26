from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1422RequestHeader(BlockRequestHeader):
    """t1422 요청용 Header"""
    pass


class T1422ResponseHeader(BlockResponseHeader):
    """t1422 응답용 Header"""
    pass


class T1422InBlock(BaseModel):
    """
    t1422InBlock - 상/하한 입력 블록

    Attributes:
        qrygb (str): 조회구분 (1:20종목씩 조회 2:전체조회)
        gubun (str): 구분 (0:전체 1:코스피 2:코스닥)
        jnilgubun (str): 전일구분 (0:당일 1:전일)
        sign (str): 상하한구분 (1:상한 4:하한)
        jc_num (int): 대상제외 비트마스크
        sprice (int): 시작가격
        eprice (int): 종료가격
        volume (int): 거래량
        idx (int): 연속조회키
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    qrygb: str
    """ 조회구분 (1:20종목씩 조회 2:전체조회) """
    gubun: str
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    jnilgubun: str
    """ 전일구분 (0:당일 1:전일) """
    sign: str
    """ 상하한구분 (1:상한 4:하한) """
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
    exchgubun: str = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1422Request(BaseModel):
    """T1422 API 요청 - 상/하한"""
    header: T1422RequestHeader = T1422RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1422",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1422InBlock"], T1422InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1422"
    )


class T1422OutBlock(BaseModel):
    """t1422OutBlock - 연속조회 블록"""
    cnt: int
    """ CNT """
    idx: int
    """ 연속조회키 """


class T1422OutBlock1(BaseModel):
    """t1422OutBlock1 - 상/하한 종목 정보"""
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
    diff_vol: float
    """ 거래증가율(%) """
    offerrem1: int
    """ 매도잔량 """
    bidrem1: int
    """ 매수잔량 """
    last: str
    """ 최종진입 """
    lmtdaycnt: int
    """ 연속 """
    jnilvolume: int
    """ 전일거래량 """
    shcode: str
    """ 종목코드 """
    ex_shcode: str = ""
    """ 거래소별단축코드 """


class T1422Response(BaseModel):
    """T1422 API 전체 응답 - 상/하한"""
    header: Optional[T1422ResponseHeader]
    cont_block: Optional[T1422OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1422OutBlock1] = Field(default_factory=list, title="상/하한 종목 리스트")
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
