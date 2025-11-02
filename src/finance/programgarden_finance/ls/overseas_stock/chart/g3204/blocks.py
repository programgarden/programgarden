from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3204RequestHeader(BlockRequestHeader):
    pass


class G3204ResponseHeader(BlockResponseHeader):
    pass


class G3204InBlock(BaseModel):
    """
    g3204InBlock 데이터 블록

    Attributes:
        sujung (Literal["Y", "N"]): 수정주가여부 (항상 Y로 유지)
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        comp_yn (Literal["N"]): 압축여부 (항상 N으로 유지)
        keysymbol (str): KEY종목코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        gubun (Literal["2", "3", "4", "5"]): 주기구분 (2:일, 3:주, 4:월, 5:년)
        qrycnt (int): 요청건수 (최대 500)
        sdate (str): 시작일자 (YYYYMMDD)
        edate (str): 종료일자 (YYYYMMDD)
        cts_date (str): 연속일자 (YYYYMMDD)
        cts_info (str): 연속정보
    """
    sujung: Literal["Y", "N"] = Field(default="Y", title="수정주가여부", description="수정주가여부 (Y:적용, N:비적용)")
    """ 수정주가여부 (Y:적용, N:비적용) """
    delaygb: Literal["R"] = Field(default="R", title="지연구분", description="지연구분 (항상 R으로 유지)")
    """ 지연구분 (항상 R으로 유지) """
    comp_yn: Literal["N"] = Field(default="N", title="압축여부", description="압축여부 (항상 N으로 유지)")
    """ 압축여부 (항상 N으로 유지) """
    keysymbol: str = Field(..., title="KEY종목코드", description="KEY종목코드 (예: \"82TSLA\")")
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str = Field(..., title="거래소코드", description="거래소코드 (예: \"82\")")
    """ 거래소코드 (예: "82") """
    symbol: str = Field(..., title="종목코드", description="종목코드 (예: \"TSLA\")")
    """ 종목코드 (예: "TSLA") """
    gubun: Literal["2", "3", "4", "5"] = Field(..., title="주기구분", description="주기구분 (2:일, 3:주, 4:월, 5:년)")
    """ 주기구분 (2:일, 3:주, 4:월, 5:년) """
    qrycnt: int = Field(..., le=500, title="요청건수", description="요청건수 (최대 500)")
    """ 요청건수 (최대 500) """
    sdate: str = Field(..., title="시작일자", description="시작일자 (YYYYMMDD)")
    """ 시작일자 (YYYYMMDD) """
    edate: str = Field(..., title="종료일자", description="종료일자 (YYYYMMDD)")
    """ 종료일자 (YYYYMMDD) """
    cts_date: str = Field(default="", title="연속일자", description="연속일자 (YYYYMMDD)")
    """ 연속일자 (YYYYMMDD) """
    cts_info: str = Field(default="", title="연속정보", description="연속정보")
    """ 연속정보 """


class G3204Request(BaseModel):
    """
    G3204 API 요청 전체 구조
    """
    header: G3204RequestHeader = G3204RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3204",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["g3204InBlock"], G3204InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3204"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3204OutBlock(BaseModel):
    """
    g3204OutBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        keysymbol (str): KEY종목코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        cts_date (str): 연속일자
        cts_info (str): 연속정보
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
        uplimit (str): 상한가
        dnlimit (str): 하한가
        s_time (str): 장시작시간
        e_time (str): 장종료시간
        dshmin (str): 동시호가처리시간
    """
    delaygb: Literal["R"] = Field(default="R", title="지연구분", description="지연구분 (항상 R으로 유지)")
    """ 지연구분 (항상 R으로 유지) """
    keysymbol: str = Field(..., title="KEY종목코드", description="KEY종목코드 (예: \"82TSLA\")")
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str = Field(..., title="거래소코드", description="거래소코드 (예: \"82\")")
    """ 거래소코드 (예: "82") """
    symbol: str = Field(..., title="종목코드", description="종목코드 (예: \"TSLA\")")
    """ 종목코드 (예: "TSLA") """
    cts_date: str = Field(..., title="연속일자", description="연속일자 (YYYYMMDD)")
    """ 연속일자 (YYYYMMDD) """
    cts_info: str = Field(..., title="연속정보", description="연속정보")
    """ 연속정보 """
    rec_count: int = Field(..., title="레코드카운트", description="레코드카운트")
    """ 레코드카운트 """
    preopen: float = Field(..., title="전일시가", description="전일시가")
    """ 전일시가 """
    prehigh: float = Field(..., title="전일고가", description="전일고가")
    """ 전일고가 """
    prelow: float = Field(..., title="전일저가", description="전일저가")
    """ 전일저가 """
    preclose: str = Field(..., title="전일종가", description="전일종가")
    """ 전일종가 """
    prevolume: int = Field(..., title="전일거래량", description="전일거래량")
    """ 전일거래량 """
    open: float = Field(..., title="당일시가", description="당일시가")
    """ 당일시가 """
    high: float = Field(..., title="당일고가", description="당일고가")
    """ 당일고가 """
    low: float = Field(..., title="당일저가", description="당일저가")
    """ 당일저가 """
    close: str = Field(..., title="당일종가", description="당일종가")
    """ 당일종가 """
    uplimit: str = Field(..., title="상한가", description="상한가")
    """ 상한가 """
    dnlimit: str = Field(..., title="하한가", description="하한가")
    """ 하한가 """
    s_time: str = Field(..., title="장시작시간", description="장시작시간 (HHMMSS 형식)")
    """ 장시작시간 (HHMMSS 형식) """
    e_time: str = Field(..., title="장종료시간", description="장종료시간 (HHMMSS 형식)")
    """ 장종료시간 (HHMMSS 형식) """
    dshmin: str = Field(..., title="동시호가처리시간", description="동시호가처리시간 (HHMMSS 형식)")
    """ 동시호가처리시간 (HHMMSS 형식) """


class G3204OutBlock1(BaseModel):
    """
    g3204OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜
        open (str): 시가
        high (float): 고가
        low (float): 저가
        close (float): 종가
        volume (int): 거래량
        amount (int): 거래대금
        jongchk (int): 수정구분
        prtt_rate (float): 수정비율
        pricechk (int): 수정주가반영항목
        ratevalue (int): 수정비율반영거래대금
        sign (str): 종가등락구분
    """
    date: str = Field(..., title="날짜", description="날짜 (YYYYMMDD 형식)")
    """ 날짜 (YYYYMMDD 형식) """
    open: float = Field(..., title="시가", description="시가")
    """ 시가 """
    high: float = Field(..., title="고가", description="고가")
    """ 고가 """
    low: float = Field(..., title="저가", description="저가")
    """ 저가 """
    close: float = Field(..., title="종가", description="종가")
    """ 종가 """
    volume: int = Field(..., title="거래량", description="거래량")
    """ 거래량 """
    amount: int = Field(..., title="거래대금", description="거래대금")
    """ 거래대금 """
    jongchk: int = Field(..., title="수정구분", description="수정구분 (0: 수정없음, 1: 수정있음)")
    """ 수정구분 (0: 수정없음, 1: 수정있음) """
    prtt_rate: float = Field(..., title="수정비율", description="수정비율 (예: \"1.0000\")")
    """ 수정비율 (예: "1.0000") """
    pricechk: int = Field(..., title="수정주가반영항목", description="수정주가반영항목 (0: 반영안함, 1: 반영함)")
    """ 수정주가반영항목 (0: 반영안함, 1: 반영함) """
    ratevalue: int = Field(..., title="수정비율반영거래대금", description="수정비율반영거래대금")
    """ 수정비율반영거래대금 """
    sign: str = Field(..., title="종가등락구분", description="종가등락구분 (예: \"+\" 상승, \"-\" 하락)")
    """ 종가등락구분 (예: "+" 상승, "-" 하락) """


class G3204Response(BaseModel):
    """
    G3204 API 응답 전체 구조

    Attributes:
        header (Optional[G3204ResponseHeader]): 응답 헤더
        block (Optional[G3204OutBlock]): 기본 응답 블록
        block1 (List[G3204OutBlock1]): 상세 리스트
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[G3204ResponseHeader] = Field(default=None, title="응답 헤더", description="응답 헤더")
    block: Optional[G3204OutBlock] = Field(default=None, title="기본 응답 블록", description="기본 응답 블록")
    block1: List[G3204OutBlock1] = Field(default_factory=list, title="상세 리스트", description="상세 리스트")
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답코드", description="응답코드")
    rsp_msg: str = Field(..., title="응답메시지", description="응답메시지")
    error_msg: Optional[str] = Field(default=None, title="오류메시지", description="오류메시지")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
