from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3202RequestHeader(BlockRequestHeader):
    pass


class G3202ResponseHeader(BlockResponseHeader):
    pass


class G3202InBlock(BaseModel):
    """
    g3202InBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        comp_yn (Literal["N"]): 압축여부 (항상 N으로 유지)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (str): 거래소코드 (예: "82")
        symbol (str): 종목코드 (예: "TSLA")
        ncnt (int): 단위(n틱)
        qrycnt (int): 요청건수, 최대 500건
        sdate (str): 시작일자 (YYYYMMDD)
        edate (str): 종료일자 (YYYYMMDD)
        cts_seq (int): 연속시퀀스
    """
    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분",
        description="지연구분 (항상 R으로 유지)"
    )
    """ 지연구분 (항상 R으로 유지) """
    comp_yn: Literal["N"] = Field(
        default="N",
        title="압축여부",
        description="압축여부 (항상 N으로 유지)"
    )
    """ 압축여부 (항상 N으로 유지) """
    keysymbol: str = Field(
        ...,
        title="KEY종목코드",
        description='KEY종목코드 (예: "82TSLA")'
    )
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str = Field(
        ...,
        title="거래소코드",
        description='거래소코드 (예: "82")'
    )
    """ 거래소코드 (예: "82") """
    symbol: str = Field(
        ...,
        title="종목코드",
        description='종목코드 (예: "TSLA")'
    )
    """ 종목코드 (예: "TSLA") """
    ncnt: int = Field(
        ...,
        title="단위",
        description="단위(n틱)"
    )
    """ 단위(n틱) """
    qrycnt: int = Field(
        ...,
        le=500,
        title="요청건수",
        description="요청건수 (최대 500)"
    )
    """ 요청건수, 최대 500건 """
    sdate: str = Field(
        ...,
        title="시작일자",
        description="시작일자 (YYYYMMDD)"
    )
    """ 시작일자 (YYYYMMDD) """
    edate: str = Field(
        ...,
        title="종료일자",
        description="종료일자 (YYYYMMDD)"
    )
    """ 종료일자 (YYYYMMDD) """
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스",
        description="연속시퀀스"
    )
    """ 연속시퀀스 """


class G3202Request(BaseModel):
    """
    G3202 API 요청 전체 구조
    """
    header: G3202RequestHeader = G3202RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3202",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """ 요청 헤더 """
    body: dict[Literal["g3202InBlock"], G3202InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'g3202InBlock')"
    )
    """ 입력 블록, g3202InBlock 데이터 블록을 포함하는 딕셔너리 형태 """
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=3,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="g3202"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3202OutBlock(BaseModel):
    """
    g3202OutBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 "R"으로 유지)
        keysymbol (str): KEY종목코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        cts_seq (int): 연속시퀀스
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
        last_count (str): 마지막Tick건수
        timediff (str): 시차
        prtt_rate (str): 수정비율
    """
    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분",
        description="지연구분 (항상 R으로 유지)"
    )
    """ 지연구분 (항상 R으로 유지) """
    keysymbol: str = Field(
        default="",
        title="KEY종목코드",
        description='KEY종목코드 (예: "82TSLA")'
    )
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str = Field(
        default="",
        title="거래소코드",
        description='거래소코드 (예: "82" - 나스닥)'
    )
    """ 거래소코드 (예: "82" - 나스닥) """
    symbol: str = Field(
        default="",
        title="종목코드",
        description='종목코드 (예: "TSLA")'
    )
    """ 종목코드 (예: "TSLA") """
    cts_seq: int = Field(
        default=0,
        title="연속시퀀스",
        description="연속시퀀스"
    )
    """ 연속시퀀스 """
    rec_count: int = Field(
        default=0,
        title="레코드카운트",
        description="레코드카운트 (조회된 데이터의 개수)"
    )
    """ 레코드카운트 (조회된 데이터의 개수) """
    preopen: float = Field(default=0.0, title="전일시가", description="전일시가")
    """ 전일시가 """
    prehigh: float = Field(default=0.0, title="전일고가", description="전일고가")
    """ 전일고가 """
    prelow: float = Field(default=0.0, title="전일저가", description="전일저가")
    """ 전일저가 """
    preclose: str = Field(default="", title="전일종가", description="전일종가")
    """ 전일종가 """
    prevolume: int = Field(default=0, title="전일거래량", description="전일거래량")
    """ 전일거래량 """
    open: float = Field(default=0.0, title="당일시가", description="당일시가")
    """ 당일시가 """
    high: float = Field(default=0.0, title="당일고가", description="당일고가")
    """ 당일고가 """
    low: float = Field(default=0.0, title="당일저가", description="당일저가")
    """ 당일저가 """
    close: str = Field(default="", title="당일종가", description="당일종가")
    """ 당일종가 """
    s_time: str = Field(default="", title="장시작시간", description="장시작시간 (HHMMSS 형식)")
    """ 장시작시간 (HHMMSS 형식) """
    e_time: str = Field(default="", title="장종료시간", description="장종료시간 (HHMMSS 형식)")
    """ 장종료시간 (HHMMSS 형식) """
    last_count: str = Field(default="", title="마지막Tick건수", description="마지막Tick건수")
    """ 마지막Tick건수 """
    timediff: str = Field(default="", title="시차", description='시차 (예: "0" - 동일시간대)')
    """ 시차 (예: "0" - 동일시간대) """


class G3202OutBlock1(BaseModel):
    """
    g3202OutBlock1 데이터 블록 리스트 항목

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        loctime (str): 현지시간 (HHMMSS)
        open (str): 시가
        high (str): 고가
        low (str): 저가
        close (str): 종가
        exevol (int): 체결량
        jongchk (int): 수정구분
        prtt_rate (str): 수정비율
        pricechk (int): 수정주가반영항목
        sign (str): 종가등락구분
    """
    date: str = Field(default="", title="날짜", description="날짜 (YYYYMMDD 형식)")
    """ 날짜 (YYYYMMDD 형식) """
    loctime: str = Field(default="", title="현지시간", description="현지시간 (HHMMSS 형식)")
    """ 현지시간 (HHMMSS 형식) """
    open: float = Field(default=0.0, title="시가", description="시가")
    """ 시가 """
    high: float = Field(default=0.0, title="고가", description="고가")
    """ 고가 """
    low: float = Field(default=0.0, title="저가", description="저가")
    """ 저가 """
    close: str = Field(default="", title="종가", description="종가")
    """ 종가 """
    exevol: int = Field(default=0, title="체결량", description="체결량")
    """ 체결량 """
    jongchk: int = Field(default=0, title="수정구분", description="수정구분 (0: 수정없음, 1: 수정있음 등)")
    """ 수정구분 (0: 수정없음, 1: 수정있음 등) """
    prtt_rate: float = Field(default=0.0, title="수정비율", description="수정비율")
    """ 수정비율 """
    pricechk: int = Field(default=0, title="수정주가반영항목", description="수정주가반영항목 (0: 반영안함, 1: 반영함 등)")
    """ 수정주가반영항목 (0: 반영안함, 1: 반영함 등) """
    sign: str = Field(default="", title="종가등락구분", description='종가등락구분 (예: "+" 상승, "-" 하락 등)')
    """ 종가등락구분 (예: "+" 상승, "-" 하락 등) """


class G3202Response(BaseModel):
    """
    G3202 API 응답 전체 구조

    Attributes:
        header (Optional[G3202ResponseHeader]): 응답 헤더
        block (Optional[G3202OutBlock]): 기본 응답 블록
        block1 (List[G3202OutBlock1]): 상세 리스트
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[G3202ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[G3202OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 블록"
    )
    block1: List[G3202OutBlock1] = Field(
        ...,
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
    error_msg: Optional[str] = Field(None, title="오류메시지", description="오류메시지 (있으면)")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
