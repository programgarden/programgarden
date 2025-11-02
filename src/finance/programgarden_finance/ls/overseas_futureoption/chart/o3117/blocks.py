from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3117RequestHeader(BlockRequestHeader):
    pass


class O3117ResponseHeader(BlockResponseHeader):
    pass


class O3117InBlock(BaseModel):
    """
    o3117InBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드
        ncnt (int): 단위
        qrycnt (int): 건수
        cts_seq (str): 순번CTS
        cts_daygb (str): 당일구분CTS
    """
    shcode: str
    """ 단축코드 (예: ADM23) """
    ncnt: int
    """ 단위 (예: 0=NTick 등) """
    qrycnt: int = Field(..., description="조회건수")
    """ 건수 """
    cts_seq: str = ""
    """ 순번CTS (연속조회용) """
    cts_daygb: str = ""
    """ 당일구분CTS (연속조회용) """


class O3117Request(BaseModel):
    """
    O3117 API 요청 전체 구조
    """
    header: O3117RequestHeader = O3117RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3117",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["o3117InBlock"], O3117InBlock]
    """입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="o3117"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3117OutBlock(BaseModel):
    """
    o3117OutBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드
        rec_count (int): 레코드카운트
        cts_seq (str): 순번CTS
        cts_daygb (str): 당일구분CTS
    """
    shcode: str
    """단축코드"""
    rec_count: int
    """레코드카운트"""
    cts_seq: str
    """순번CTS"""
    cts_daygb: str
    """당일구분CTS"""


class O3117OutBlock1(BaseModel):
    """
    o3117OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        time (str): 시간 (HHMMSS)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str
    """날짜 (YYYYMMDD)"""
    time: str
    """시간 (HHMMSS)"""
    open: float
    """시가"""
    high: float
    """고가"""
    low: float
    """저가"""
    close: float
    """종가"""
    volume: int
    """거래량"""


class O3117Response(BaseModel):
    """
    O3117 API 응답 전체 구조

    Attributes:
        header (Optional[O3117ResponseHeader]): 응답 헤더
        block (Optional[O3117OutBlock]): 기본 응답 블록
        block1 (List[O3117OutBlock1]): 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[O3117ResponseHeader]
    block: Optional[O3117OutBlock]
    block1: List[O3117OutBlock1]
    status_code: Optional[int] = None
    """HTTP 상태 코드"""
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = None

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
