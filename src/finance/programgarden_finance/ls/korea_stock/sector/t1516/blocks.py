from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1516RequestHeader(BlockRequestHeader):
    """t1516 요청용 Header"""
    pass


class T1516ResponseHeader(BlockResponseHeader):
    """t1516 응답용 Header"""
    pass


class T1516InBlock(BaseModel):
    """
    t1516InBlock - 업종별종목시세 입력 블록

    Attributes:
        upcode (str): 업종코드
        gubun (str): 구분 (1:코스피업종 2:코스닥업종 3:섹터지수)
        shcode (str): 종목코드 (처음 조회시 Space, 연속 조회시 이전 OutBlock의 shcode)
    """
    upcode: str
    """ 업종코드 """
    gubun: Literal["1", "2", "3"]
    """ 구분 (1:코스피업종 2:코스닥업종 3:섹터지수) """
    shcode: str = ""
    """ 종목코드 (처음 조회시 Space, 연속 조회시 이전 OutBlock의 shcode) """


class T1516Request(BaseModel):
    """
    T1516 API 요청 - 업종별종목시세

    Attributes:
        header (T1516RequestHeader)
        body (Dict[Literal["t1516InBlock"], T1516InBlock])
    """
    header: T1516RequestHeader = T1516RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1516",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1516InBlock"], T1516InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1516"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1516OutBlock(BaseModel):
    """
    t1516OutBlock - 업종별종목시세 연속 블록
    """
    shcode: str = ""
    """ 종목코드 """
    pricejisu: float = 0.0
    """ 지수 """
    sign: str = ""
    """ 전일대비구분 """
    change: float = 0.0
    """ 전일대비 """
    jdiff: float = 0.0
    """ 등락율 """


class T1516OutBlock1(BaseModel):
    """
    t1516OutBlock1 - 업종별종목시세 종목 리스트
    """
    hname: str = ""
    """ 종목명 """
    price: int = 0
    """ 현재가 """
    sign: str = ""
    """ 전일대비구분 """
    change: int = 0
    """ 전일대비 """
    diff: float = 0.0
    """ 등락율 """
    volume: int = 0
    """ 누적거래량 """
    open: int = 0
    """ 시가 """
    high: int = 0
    """ 고가 """
    low: int = 0
    """ 저가 """
    sojinrate: float = 0.0
    """ 소진율 """
    beta: float = 0.0
    """ 베타계수 """
    perx: float = 0.0
    """ PER """
    frgsvolume: int = 0
    """ 외인순매수 """
    orgsvolume: int = 0
    """ 기관순매수 """
    diff_vol: float = 0.0
    """ 거래증가율 """
    shcode: str = ""
    """ 종목코드 """
    total: int = 0
    """ 시가총액 """
    value: int = 0
    """ 거래대금 """


class T1516Response(BaseModel):
    """
    T1516 API 전체 응답 - 업종별종목시세
    """
    header: Optional[T1516ResponseHeader] = None
    cont_block: Optional[T1516OutBlock] = Field(
        None, title="연속 데이터",
        description="업종 지수 및 연속조회 키"
    )
    block: List[T1516OutBlock1] = Field(
        default_factory=list, title="종목 리스트",
        description="업종별 종목 시세 리스트"
    )
    status_code: Optional[int] = Field(None, title="HTTP 상태 코드")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(None, title="오류메시지")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
