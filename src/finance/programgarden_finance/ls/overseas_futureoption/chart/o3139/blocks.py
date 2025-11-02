from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3139RequestHeader(BlockRequestHeader):
    pass


class O3139ResponseHeader(BlockResponseHeader):
    pass


class O3139InBlock(BaseModel):
    """
    o3139InBlock 데이터 블록

    Attributes:
        mktgb (str): 시장구분
        shcode (str): 단축코드
        ncnt (int): 단위
        qrycnt (int): 건수
        cts_seq (str): 순번CTS
        cts_daygb (str): 당일구분CTS
    """
    mktgb: str
    """ 시장구분 (예: F=선물, O=옵션) """
    shcode: str
    """ 단축코드 (예: 2ESF16_1915) """
    ncnt: int
    """ 단위 (Number) """
    qrycnt: int = Field(..., description="조회건수")
    """ 조회건수 """
    cts_seq: str = ""
    """ 순번CTS (연속조회용) """
    cts_daygb: str = ""
    """ 당일구분CTS (연속조회용) """


class O3139Request(BaseModel):
    """
    O3139 API 요청 전체 구조
    """
    header: O3139RequestHeader = O3139RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3139",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["o3139InBlock"], O3139InBlock]
    """입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="o3139"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3139OutBlock(BaseModel):
    """
    o3139OutBlock 데이터 블록

    Attributes:
        shcode (str): 단축코드
        rec_count (int): 레코드카운트
        cts_seq (str): 연속시간
        cts_daygb (str): 연속당일구분
        last_count (Optional[int]): 마지막Tick건수
    """
    shcode: Optional[str]
    """단축코드"""
    rec_count: Optional[int]
    """레코드카운트"""
    cts_seq: Optional[str]
    """연속시간(순번CTS)"""
    cts_daygb: Optional[str]
    """연속당일구분"""
    last_count: Optional[int]
    """마지막Tick건수 (없을 수 있음) """


class O3139OutBlock1(BaseModel):
    """
    o3139OutBlock1 데이터 블록 리스트 항목

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


class O3139Response(BaseModel):
    """
    O3139 API 응답 전체 구조

    Attributes:
        header (Optional[O3139ResponseHeader]): 응답 헤더
        block (Optional[O3139OutBlock]): 기본 응답 블록
        block1 (List[O3139OutBlock1]): 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[O3139ResponseHeader]
    block: Optional[O3139OutBlock]
    block1: List[O3139OutBlock1]
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


__all__ = [
    "O3139InBlock",
    "O3139OutBlock",
    "O3139OutBlock1",
    "O3139Request",
    "O3139Response",
    "O3139RequestHeader",
    "O3139ResponseHeader",
]
