from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3103RequestHeader(BlockRequestHeader):
    pass


class O3103ResponseHeader(BlockResponseHeader):
    pass


class O3103InBlock(BaseModel):
    """
    o3103InBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드 (예: ADU13)
        ncnt (int): N분주기 (예: 0=30초, 1=1분, 30=30분)
        readcnt (int): 조회건수
        cts_date (str): 연속일자 (YYYYMMDD)
        cts_time (str): 연속시간 (HHMMSS)
    """
    shcode: str
    """ 단축코드 (예: ADU13) """
    ncnt: int
    """ N분주기 (예: 0=30초, 1=1분, 30=30분) """
    readcnt: int = Field(..., description="조회건수")
    """ 조회건수 """
    cts_date: str = ""
    """ 연속일자 (YYYYMMDD) """
    cts_time: str = ""
    """ 연속시간 (HHMMSS) """


class O3103Request(BaseModel):
    """
    O3103 API 요청 전체 구조
    """
    header: O3103RequestHeader = O3103RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3103",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["o3103InBlock"], O3103InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="o3103"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3103OutBlock(BaseModel):
    """
    o3103OutBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드
        timediff (int): 시차
        readcnt (int): 조회건수
        cts_date (str): 연속일자
        cts_time (str): 연속시간
    """
    shcode: str
    """ 단축코드 """
    timediff: int
    """ 시차 """
    readcnt: int
    """ 조회건수 """
    cts_date: str
    """ 연속일자 (YYYYMMDD) """
    cts_time: str
    """ 연속시간 (HHMMSS) """


class O3103OutBlock1(BaseModel):
    """
    o3103OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        time (str): 현지시간 (HHMMSS)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str
    """ 날짜 (YYYYMMDD) """
    time: str
    """ 현지시간 (HHMMSS) """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    close: float
    """ 종가 """
    volume: int
    """ 거래량 """


class O3103Response(BaseModel):
    """
    O3103 API 응답 전체 구조

    Attributes:
        header (Optional[O3103ResponseHeader]): 응답 헤더
        block (Optional[O3103OutBlock]): 기본 응답 블록
        block1 (List[O3103OutBlock1]): 상세 리스트
        status_code (int): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[O3103ResponseHeader]
    block: Optional[O3103OutBlock]
    block1: List[O3103OutBlock1]
    rsp_cd: str
    rsp_msg: str
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="API 호출에 대한 HTTP 상태 코드"
    )
    error_msg: Optional[str] = None

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
