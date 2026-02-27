from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1463RequestHeader(BlockRequestHeader):
    """t1463 요청용 Header"""
    pass


class T1463ResponseHeader(BlockResponseHeader):
    """t1463 응답용 Header"""
    pass


class T1463InBlock(BaseModel):
    """
    t1463InBlock - 거래대금상위 입력 블록

    시장구분, 가격 범위, 최소 거래량 등 필터 조건을 설정하여
    거래대금 상위 종목을 조회합니다.

    Attributes:
        gubun (str): 시장구분 (0:전체 1:코스피 2:코스닥)
        jnilgubun (str): 전일구분 (0:당일 1:전일)
        jc_num (int): 대상제외 비트마스크 (0이면 제외 없음, 128:관리종목, 256:시장경보, 512:거래정지, 16384:우선주 등 합산)
        sprice (int): 시작가격 - 현재가 하한 필터 (0이면 필터 없음)
        eprice (int): 종료가격 - 현재가 상한 필터 (0이면 필터 없음)
        volume (int): 최소 거래량 필터 (0이면 필터 없음)
        idx (int): 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx)
        jc_num2 (int): 대상제외2 비트마스크 (0이면 제외 없음, 1:ETF, 2:선박투자, 4:스펙, 8:ETN, 16:투자주의, 32:투자위험, 64:위험예고, 128:담보불가 합산)
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합, 그외 KRX)
    """
    gubun: Literal["0", "1", "2"]
    """ 시장구분 (0:전체 1:코스피 2:코스닥) """
    jnilgubun: Literal["0", "1"]
    """ 전일구분 (0:당일 1:전일) """
    jc_num: int = 0
    """ 대상제외 비트마스크 (0이면 제외 없음, 128:관리종목, 256:시장경보, 512:거래정지, 16384:우선주 등 합산) """
    sprice: int = 0
    """ 시작가격 - 현재가 하한 필터 (0이면 필터 없음) """
    eprice: int = 0
    """ 종료가격 - 현재가 상한 필터 (0이면 필터 없음) """
    volume: int = 0
    """ 최소 거래량 필터 (0이면 필터 없음) """
    idx: int = 0
    """ 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx) """
    jc_num2: int = 0
    """ 대상제외2 비트마스크 (0이면 제외 없음, 1:ETF, 2:선박투자, 4:스펙, 8:ETN, 16:투자주의, 32:투자위험, 64:위험예고, 128:담보불가 합산) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합, 그외 KRX) """


class T1463Request(BaseModel):
    """
    T1463 API 요청 - 거래대금상위

    Attributes:
        header (T1463RequestHeader)
        body (Dict[Literal["t1463InBlock"], T1463InBlock])
    """
    header: T1463RequestHeader = T1463RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1463",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1463InBlock"], T1463InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1463"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1463OutBlock(BaseModel):
    """
    t1463OutBlock - 거래대금상위 연속조회 블록

    연속조회에 사용되는 idx를 반환합니다.
    다음 페이지 조회 시 이 값을 InBlock.idx에 설정합니다.

    Attributes:
        idx (int): 연속조회키
    """
    idx: int
    """ 연속조회키 (다음 페이지 조회 시 InBlock.idx에 설정) """


class T1463OutBlock1(BaseModel):
    """
    t1463OutBlock1 - 거래대금상위 종목 정보

    거래대금 순위별 종목의 현재가, 등락률, 누적거래량,
    거래대금, 전일거래대금, 전일비, 시가총액을 제공합니다.

    Attributes:
        hname (str): 종목명
        price (int): 현재가
        sign (str): 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락)
        change (int): 전일대비
        diff (float): 등락율(%)
        volume (int): 누적거래량
        value (int): 거래대금(백만원)
        jnilvalue (int): 전일거래대금(백만원)
        bef_diff (float): 전일비(%) - 전일거래대금 대비 당일거래대금 비율
        shcode (str): 종목코드 6자리
        filler (str): filler
        jnilvolume (int): 전일거래량
        ex_shcode (str): 거래소별단축코드
        total (int): 시가총액(백만원)
    """
    hname: str
    """ 종목명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    volume: int
    """ 누적거래량 """
    value: int
    """ 거래대금(백만원) """
    jnilvalue: int
    """ 전일거래대금(백만원) """
    bef_diff: float
    """ 전일비(%) - 전일거래대금 대비 당일거래대금 비율 """
    shcode: str
    """ 종목코드 6자리 """
    filler: str = ""
    """ filler """
    jnilvolume: int
    """ 전일거래량 """
    ex_shcode: str = ""
    """ 거래소별단축코드 """
    total: int
    """ 시가총액(백만원) """


class T1463Response(BaseModel):
    """
    T1463 API 전체 응답 - 거래대금상위

    거래대금 상위 종목 리스트를 반환합니다.
    연속조회가 필요하면 cont_block.idx를 다음 요청의 InBlock.idx에 설정합니다.

    Attributes:
        header (Optional[T1463ResponseHeader])
        cont_block (Optional[T1463OutBlock]): 연속조회 블록 (idx 포함)
        block (List[T1463OutBlock1]): 거래대금상위 종목 리스트
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T1463ResponseHeader]
    cont_block: Optional[T1463OutBlock] = Field(
        None,
        title="연속조회 블록",
        description="연속조회키(idx)를 포함하는 블록"
    )
    block: List[T1463OutBlock1] = Field(
        default_factory=list,
        title="거래대금상위 종목 리스트",
        description="거래대금 상위 종목 리스트"
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
