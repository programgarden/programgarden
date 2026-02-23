from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8451RequestHeader(BlockRequestHeader):
    """t8451 요청용 Header"""
    pass


class T8451ResponseHeader(BlockResponseHeader):
    """t8451 응답용 Header"""
    pass


class T8451InBlock(BaseModel):
    """
    t8451InBlock 입력 블록

    Attributes:
        shcode (str): 단축코드 (6자리)
        gubun (str): 주기구분 (2:일, 3:주, 4:월, 5:년)
        qrycnt (int): 요청건수 (최대 500)
        sdate (str): 시작일자 (YYYYMMDD, 기본값 공백)
        edate (str): 종료일자 (YYYYMMDD, 처음조회시 "99999999" 또는 당일)
        cts_date (str): 연속일자 (연속조회시 이전 응답의 cts_date 값)
        comp_yn (str): 압축여부 (N:비압축, OPEN API 압축 미제공)
        sujung (str): 수정주가여부 (Y:적용, N:비적용)
        exchgubun (str): 거래소구분코드 (K:KRX, N:NXT, U:통합)
    """
    shcode: str
    """ 단축코드 """
    gubun: str = "2"
    """ 주기구분 (2:일, 3:주, 4:월, 5:년) """
    qrycnt: int = 500
    """ 요청건수 (최대 500) """
    sdate: str = ""
    """ 시작일자 (YYYYMMDD, 기본값 공백이면 edate 기준으로 qrycnt만큼 조회) """
    edate: str = "99999999"
    """ 종료일자 (YYYYMMDD, 처음조회시 "99999999" 또는 당일) """
    cts_date: str = ""
    """ 연속일자 (연속조회시 이전 응답의 cts_date 값) """
    comp_yn: str = "N"
    """ 압축여부 (N:비압축, OPEN API 압축 미제공) """
    sujung: str = "N"
    """ 수정주가여부 (Y:적용, N:비적용) """
    exchgubun: str = "K"
    """ 거래소구분코드 (K:KRX, N:NXT, U:통합, 그외 KRX로 처리) """


class T8451Request(BaseModel):
    """
    T8451 API 요청

    Attributes:
        header (T8451RequestHeader)
        body (Dict[Literal["t8451InBlock"], T8451InBlock])
    """
    header: T8451RequestHeader = T8451RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8451",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t8451InBlock"], T8451InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t8451"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T8451OutBlock(BaseModel):
    """
    t8451OutBlock 응답 블록 (차트 기본 정보)

    Attributes:
        shcode (str): 단축코드
        jisiga (int): 전일시가
        jihigh (int): 전일고가
        jilow (int): 전일저가
        jiclose (int): 전일종가
        jivolume (int): 전일거래량
        disiga (int): 당일시가
        dihigh (int): 당일고가
        dilow (int): 당일저가
        diclose (int): 당일종가
        highend (int): 상한가
        lowend (int): 하한가
        cts_date (str): 연속일자
        s_time (str): 장시작시간(HHMMSS)
        e_time (str): 장종료시간(HHMMSS)
        dshmin (str): 동시호가처리시간(MM:분)
        rec_count (int): 레코드카운트
        svi_uplmtprice (int): 정적VI상한가
        svi_dnlmtprice (int): 정적VI하한가
        nxt_fm_s_time (str): NXT프리마켓장시작시간(HHMMSS)
        nxt_fm_e_time (str): NXT프리마켓장종료시간(HHMMSS)
        nxt_fm_dshmin (str): NXT프리마켓동시호가처리시간(MM:분)
        nxt_am_s_time (str): NXT에프터마켓장시작시간(HHMMSS)
        nxt_am_e_time (str): NXT에프터마켓장종료시간(HHMMSS)
        nxt_am_dshmin (str): NXT에프터마켓동시호가처리시간(MM:분)
    """
    shcode: str
    """ 단축코드 """
    jisiga: int
    """ 전일시가 """
    jihigh: int
    """ 전일고가 """
    jilow: int
    """ 전일저가 """
    jiclose: int
    """ 전일종가 """
    jivolume: int
    """ 전일거래량 """
    disiga: int
    """ 당일시가 """
    dihigh: int
    """ 당일고가 """
    dilow: int
    """ 당일저가 """
    diclose: int
    """ 당일종가 """
    highend: int
    """ 상한가 """
    lowend: int
    """ 하한가 """
    cts_date: str
    """ 연속일자 """
    s_time: str
    """ 장시작시간(HHMMSS) """
    e_time: str
    """ 장종료시간(HHMMSS) """
    dshmin: str
    """ 동시호가처리시간(MM:분) """
    rec_count: int
    """ 레코드카운트 """
    svi_uplmtprice: int
    """ 정적VI상한가 """
    svi_dnlmtprice: int
    """ 정적VI하한가 """
    nxt_fm_s_time: str = ""
    """ NXT프리마켓장시작시간(HHMMSS) """
    nxt_fm_e_time: str = ""
    """ NXT프리마켓장종료시간(HHMMSS) """
    nxt_fm_dshmin: str = ""
    """ NXT프리마켓동시호가처리시간(MM:분) """
    nxt_am_s_time: str = ""
    """ NXT에프터마켓장시작시간(HHMMSS) """
    nxt_am_e_time: str = ""
    """ NXT에프터마켓장종료시간(HHMMSS) """
    nxt_am_dshmin: str = ""
    """ NXT에프터마켓동시호가처리시간(MM:분) """


class T8451OutBlock1(BaseModel):
    """
    t8451OutBlock1 응답 블록 (차트 OHLCV 데이터, occurs)

    Attributes:
        date (str): 날짜 (YYYYMMDD)
        open (int): 시가
        high (int): 고가
        low (int): 저가
        close (int): 종가
        jdiff_vol (int): 거래량
        value (int): 거래대금
        jongchk (int): 수정구분
        rate (float): 수정비율
        pricechk (int): 수정주가반영항목
        ratevalue (int): 수정비율반영거래대금
        sign (str): 종가등락구분 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락, 주식일만사용)
    """
    date: str
    """ 날짜 (YYYYMMDD) """
    open: int
    """ 시가 """
    high: int
    """ 고가 """
    low: int
    """ 저가 """
    close: int
    """ 종가 """
    jdiff_vol: int
    """ 거래량 """
    value: int
    """ 거래대금 """
    jongchk: int
    """ 수정구분 """
    rate: float
    """ 수정비율 """
    pricechk: int
    """ 수정주가반영항목 """
    ratevalue: int
    """ 수정비율반영거래대금 """
    sign: str
    """ 종가등락구분 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락) """


class T8451Response(BaseModel):
    """
    T8451 API 전체 응답

    Attributes:
        header (Optional[T8451ResponseHeader])
        block (Optional[T8451OutBlock]): 차트 기본 정보
        block1 (List[T8451OutBlock1]): 차트 OHLCV 데이터 리스트
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[T8451ResponseHeader]
    block: Optional[T8451OutBlock] = Field(
        None,
        title="차트 기본 정보",
        description="주식차트(일주월년) 기본 응답 블록"
    )
    block1: List[T8451OutBlock1] = Field(
        default_factory=list,
        title="차트 OHLCV 데이터",
        description="주식차트(일주월년) OHLCV 데이터 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str
    rsp_msg: str
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
