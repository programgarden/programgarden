from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3108RequestHeader(BlockRequestHeader):
    pass


class O3108ResponseHeader(BlockResponseHeader):
    pass


class O3108InBlock(BaseModel):
    """
    o3108InBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드 (예: ADU13)
        gubun (Literal["0", "1", "2"]): 주기구분 (예: 0=일,1=주,2=월)
        qrycnt (int): 요청건수
        sdate (str): 시작일자 (YYYYMMDD)
        edate (str): 종료일자 (YYYYMMDD)
        cts_date (str): 연속일자 (YYYYMMDD)
    """
    shcode: str
    """ 단축코드 (예: ADU13) """
    gubun: Literal["0", "1", "2"]
    """ 주기구분 (예: 0=일,1=주,2=월) """
    qrycnt: int = Field(..., description="요청건수")
    """ 요청건수 """
    sdate: str
    """ 시작일자 (YYYYMMDD) """
    edate: str
    """ 종료일자 (YYYYMMDD) """
    cts_date: str = ""
    """ 연속일자 (YYYYMMDD) """


class O3108Request(BaseModel):
    """
    O3108 API 요청 전체 구조
    """
    header: O3108RequestHeader = O3108RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3108",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["o3108InBlock"], O3108InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="o3108"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3108OutBlock(BaseModel):
    """
    o3108OutBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드
        jisiga (float): 전일시가
        jihigh (float): 전일고가
        jilow (float): 전일저가
        jiclose (float): 전일종가
        jivolume (int): 전일거래량
        disiga (float): 당일시가
        dihigh (float): 당일고가
        dilow (float): 당일저가
        diclose (float): 당일종가
        mk_stime (str): 장시작시간
        mk_etime (str): 장마감시간
        cts_date (str): 연속일자
        rec_count (int): 레코드카운트
    """
    shcode: str
    """ 단축코드 """
    jisiga: float
    """ 전일시가 """
    jihigh: float
    """ 전일고가 """
    jilow: float
    """ 전일저가 """
    jiclose: float
    """ 전일종가 """
    jivolume: Optional[int]
    """ 전일거래량 """
    disiga: Optional[float]
    """ 당일시가 """
    dihigh: Optional[float]
    """ 당일고가 """
    dilow: Optional[float]
    """ 당일저가 """
    diclose: Optional[float]
    """ 당일종가 """
    mk_stime: Optional[str]
    """ 장시작시간 """
    mk_etime: Optional[str]
    """ 장마감시간 """
    cts_date: Optional[str]
    """ 연속일자 (YYYYMMDD) """
    rec_count: Optional[int]
    """ 레코드카운트 """


class O3108OutBlock1(BaseModel):
    """
    o3108OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        open (float): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
    """
    date: str
    """ 날짜 (YYYYMMDD) """
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


class O3108Response(BaseModel):
    """
    O3108 API 응답 전체 구조

    Attributes:
        header (Optional[O3108ResponseHeader]): 응답 헤더
        block (Optional[O3108OutBlock]): 기본 응답 블록
        block1 (List[O3108OutBlock1]): 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[O3108ResponseHeader]
    block: Optional[O3108OutBlock]
    block1: List[O3108OutBlock1]
    status_code: Optional[int] = None
    """ HTTP 상태 코드 """
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
