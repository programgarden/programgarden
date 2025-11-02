from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3203RequestHeader(BlockRequestHeader):
    pass


class G3203ResponseHeader(BlockResponseHeader):
    pass


class G3203InBlock(BaseModel):
    """
    g3203InBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        comp_yn (Literal["N"]): 압축여부 (항상 N으로 유지)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (str): 거래소코드 (예: "82")
        symbol (str): 종목코드 (예: "TSLA")
        ncnt (int): 단위(n분)
        qrycnt (int): 요청건수 (최대 500)
        sdate (str): 시작일자 (YYYYMMDD)
        edate (str): 종료일자 (YYYYMMDD)
        cts_date (str): 연속일자 (YYYYMMDD)
        cts_time (str): 연속시간 (HHMMSS)
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R으로 유지) """
    comp_yn: Literal["N"] = "N"
    """ 압축여부 (항상 N으로 유지) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str
    """ 거래소코드 (예: "82") """
    symbol: str
    """ 종목코드 (예: "TSLA") """
    ncnt: int
    """ 단위(n분) """
    qrycnt: int = Field(..., le=500, description="요청건수 (최대 500)")
    """ 요청건수 (최대 500) """
    sdate: str
    """ 시작일자 (YYYYMMDD) """
    edate: str
    """ 종료일자 (YYYYMMDD) """
    cts_date: str = ""
    """ 연속일자 (YYYYMMDD) """
    cts_time: str = ""
    """ 연속시간 (HHMMSS) """


class G3203Request(BaseModel):
    """
    G3203 API 요청 전체 구조
    """
    header: G3203RequestHeader = G3203RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3203",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["g3203InBlock"], G3203InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3203"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3203OutBlock(BaseModel):
    """
    g3203OutBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        keysymbol (str): KEY종목코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        cts_date (str): 연속일자
        cts_time (str): 연속시간
        rec_count (int): 레코드카운트
        preopen (str): 전일시가
        prehigh (str): 전일고가
        prelow (str): 전일저가
        preclose (str): 전일종가
        prevolume (int): 전일거래량
        open (str): 당일시가
        high (str): 당일고가
        low (str): 당일저가
        close (str): 당일종가
        s_time (str): 장시작시간 (HHMMSS)
        e_time (str): 장종료시간 (HHMMSS)
        timediff (str): 시차
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R으로 유지) """
    keysymbol: str
    """ KEY종목코드 """
    exchcd: str
    """ 거래소코드 """
    symbol: str
    """ 종목코드 """
    cts_date: str
    """ 연속일자 (YYYYMMDD) """
    cts_time: str
    """ 연속시간 (HHMMSS) """
    rec_count: int
    """ 레코드카운트 (조회된 데이터의 개수) """
    preopen: float
    """ 전일시가 """
    prehigh: float
    """ 전일고가 """
    prelow: float
    """ 전일저가 """
    preclose: str
    """ 전일종가 """
    prevolume: int
    """ 전일거래량 """
    open: float
    """ 당일시가 """
    high: float
    """ 당일고가 """
    low: float
    """ 당일저가 """
    close: str
    """ 당일종가 """
    s_time: str
    """ 장시작시간 (HHMMSS 형식) """
    e_time: str
    """ 장종료시간 (HHMMSS 형식) """
    timediff: str
    """ 시차 (HHMMSS 형식) """


class G3203OutBlock1(BaseModel):
    """
    g3203OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        loctime (str): 현지시간 (HHMMSS)
        open (str): 시가
        high (str): 고가
        low (str): 저가
        close (str): 종가
        exevol (int): 체결량
        amount (int): 거래대금
    """
    date: str
    """ 날짜 (YYYYMMDD) """
    loctime: str
    """ 현지시간 (HHMMSS) """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    close: str
    """ 종가 """
    exevol: int
    """ 체결량 """
    amount: int
    """ 거래대금 """


class G3203Response(BaseModel):
    """
    G3203 API 응답 전체 구조

    Attributes:
        header (Optional[G3203ResponseHeader]): 응답 헤더
        block (Optional[G3203OutBlock]): 기본 응답 블록
        block1 (List[G3203OutBlock1]): 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[G3203ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[G3203OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 데이터 블록"
    )
    block1: List[G3203OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지",
        description="오류메시지 (있으면)"
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
