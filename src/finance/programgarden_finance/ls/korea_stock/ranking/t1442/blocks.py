from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1442RequestHeader(BlockRequestHeader):
    """t1442 요청용 Header"""
    pass


class T1442ResponseHeader(BlockResponseHeader):
    """t1442 응답용 Header"""
    pass


class T1442InBlock(BaseModel):
    """
    t1442InBlock - 신고/신저가 입력 블록

    Attributes:
        gubun (str): 구분 (0:전체 1:코스피 2:코스닥)
        type1 (str): 신고신저 (0:신고 1:신저)
        type2 (str): 기간 (0:전일 1:5일 2:10일 3:20일 4:60일 5:90일 6:52주 7:년중)
        type3 (str): 유지여부 (0:일시돌파 1:돌파유지)
        jc_num (int): 대상제외 비트마스크
        sprice (int): 시작가격
        eprice (int): 종료가격
        volume (int): 거래량
        idx (int): 연속조회키
        jc_num2 (int): 대상제외2 비트마스크
    """
    gubun: str
    """ 구분 (0:전체 1:코스피 2:코스닥) """
    type1: str
    """ 신고신저 (0:신고 1:신저) """
    type2: str
    """ 기간 (0:전일 1:5일 2:10일 3:20일 4:60일 5:90일 6:52주 7:년중) """
    type3: str
    """ 유지여부 (0:일시돌파 1:돌파유지) """
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


class T1442Request(BaseModel):
    """T1442 API 요청 - 신고/신저가"""
    header: T1442RequestHeader = T1442RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1442",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1442InBlock"], T1442InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1442"
    )


class T1442OutBlock(BaseModel):
    """t1442OutBlock - 연속조회 블록"""
    idx: int
    """ 연속조회키 """


class T1442OutBlock1(BaseModel):
    """t1442OutBlock1 - 신고/신저가 종목 정보"""
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
    volume: int
    """ 거래량 """
    pastprice: int
    """ 이전가 """
    pastsign: str
    """ 이전가대비구분 """
    pastchange: int
    """ 이전가대비 """
    pastdiff: float
    """ 이전가대비율(%) """


class T1442Response(BaseModel):
    """T1442 API 전체 응답 - 신고/신저가"""
    header: Optional[T1442ResponseHeader]
    cont_block: Optional[T1442OutBlock] = Field(None, title="연속조회 블록")
    block: List[T1442OutBlock1] = Field(default_factory=list, title="신고/신저가 종목 리스트")
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
