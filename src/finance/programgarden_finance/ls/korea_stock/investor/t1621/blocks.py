from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1621RequestHeader(BlockRequestHeader):
    """t1621 요청용 Header"""
    pass


class T1621ResponseHeader(BlockResponseHeader):
    """t1621 응답용 Header"""
    pass


class T1621InBlock(BaseModel):
    """
    t1621InBlock - 업종별분별투자자매매동향 입력 블록

    Attributes:
        upcode (str): 업종코드
        nmin (int): N분
        cnt (int): 조회건수
        bgubun (str): 전일분 (0:당일 1:전일)
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    upcode: str
    """ 업종코드 """
    nmin: int = 0
    """ N분 """
    cnt: int = 20
    """ 조회건수 """
    bgubun: Literal["0", "1"]
    """ 전일분 (0:당일 1:전일) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1621Request(BaseModel):
    """
    T1621 API 요청 - 업종별분별투자자매매동향
    """
    header: T1621RequestHeader = T1621RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1621",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1621InBlock"], T1621InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1621"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1621OutBlock(BaseModel):
    """
    t1621OutBlock - 업종별분별투자자매매동향 요약 블록
    """
    indcode: str = ""
    """ 개인투자자코드 """
    forcode: str = ""
    """ 외국인투자자코드 """
    syscode: str = ""
    """ 기관계투자자코드 """
    stocode: str = ""
    """ 증권투자자코드 """
    invcode: str = ""
    """ 투신투자자코드 """
    bancode: str = ""
    """ 은행투자자코드 """
    inscode: str = ""
    """ 보험투자자코드 """
    fincode: str = ""
    """ 종금투자자코드 """
    moncode: str = ""
    """ 기금투자자코드 """
    etccode: str = ""
    """ 기타투자자코드 """
    natcode: str = ""
    """ 국가투자자코드 """
    pefcode: str = ""
    """ 사모펀드투자자코드 """
    jisucd: str = ""
    """ 기준지수코드 """
    jisunm: str = ""
    """ 기준지수명 """
    ex_upcode: str = ""
    """ 거래소별업종코드 """


class T1621OutBlock1(BaseModel):
    """
    t1621OutBlock1 - 업종별분별투자자매매동향 시간별 리스트
    """
    date: str = ""
    """ 일자 """
    time: str = ""
    """ 시간 """
    datetime: str = ""
    """ 일자시간 """
    indmsvol: int = 0
    """ 개인순매수거래량 """
    indmsamt: int = 0
    """ 개인순매수거래대금 """
    formsvol: int = 0
    """ 외국인순매수거래량 """
    formsamt: int = 0
    """ 외국인순매수거래대금 """
    sysmsvol: int = 0
    """ 기관계순매수거래량 """
    sysmsamt: int = 0
    """ 기관계순매수거래대금 """
    stomsvol: int = 0
    """ 증권순매수거래량 """
    stomsamt: int = 0
    """ 증권순매수거래대금 """
    invmsvol: int = 0
    """ 투신순매수거래량 """
    invmsamt: int = 0
    """ 투신순매수거래대금 """
    banmsvol: int = 0
    """ 은행순매수거래량 """
    banmsamt: int = 0
    """ 은행순매수거래대금 """
    insmsvol: int = 0
    """ 보험순매수거래량 """
    insmsamt: int = 0
    """ 보험순매수거래대금 """
    finmsvol: int = 0
    """ 종금순매수거래량 """
    finmsamt: int = 0
    """ 종금순매수거래대금 """
    monmsvol: int = 0
    """ 기금순매수거래량 """
    monmsamt: int = 0
    """ 기금순매수거래대금 """
    etcmsvol: int = 0
    """ 기타순매수거래량 """
    etcmsamt: int = 0
    """ 기타순매수거래대금 """
    natmsvol: int = 0
    """ 국가순매수거래량 """
    natmsamt: int = 0
    """ 국가순매수거래대금 """
    pefmsvol: int = 0
    """ 사모펀드순매수거래량 """
    pefmsamt: int = 0
    """ 사모펀드순매수거래대금 """
    upclose: float = 0.0
    """ 기준지수 """
    upcvolume: int = 0
    """ 기준체결거래량 """
    upvolume: int = 0
    """ 기준누적거래량 """
    upvalue: int = 0
    """ 기준거래대금 """


class T1621Response(BaseModel):
    """
    T1621 API 전체 응답 - 업종별분별투자자매매동향
    """
    header: Optional[T1621ResponseHeader] = None
    cont_block: Optional[T1621OutBlock] = Field(
        None, title="요약 데이터",
        description="투자자 코드 및 기준지수 정보"
    )
    block: List[T1621OutBlock1] = Field(
        default_factory=list, title="시간별 리스트",
        description="분별 투자자 매매 동향 리스트"
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
