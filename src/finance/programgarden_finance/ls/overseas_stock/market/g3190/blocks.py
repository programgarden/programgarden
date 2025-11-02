from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3190RequestHeader(BlockRequestHeader):
    """g3190 요청용 Header"""
    pass


class G3190ResponseHeader(BlockResponseHeader):
    """g3190 응답용 Header"""
    pass


class G3190InBlock(BaseModel):
    """
    g3190InBlock 입력 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R)
        natcode (str): 국가구분 (예: "US")
        exgubun (str): 거래소구분 (예: "2")
        readcnt (int): 조회갯수
        cts_value (str): 연속구분
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    natcode: str
    """ 국가구분 (예: "US") """
    exgubun: str
    """ 거래소구분 (예: "2") """
    readcnt: int
    """ 조회갯수 """
    cts_value: str
    """ 연속구분 (예: "0") """


class G3190Request(BaseModel):
    """
    G3190 API 요청

    Attributes:
        header (G3190RequestHeader)
        body (Dict[Literal["g3190InBlock"], G3190InBlock])
    """
    header: G3190RequestHeader = G3190RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3190",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["g3190InBlock"], G3190InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3190"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3190OutBlock(BaseModel):
    """
    g3190OutBlock 응답 블록 (요약)

    Attributes:
        delaygb (Literal["R"]): 지연구분
        natcode (str): 국가구분
        exgubun (str): 거래소구분
        cts_value (str): 연속구분
        rec_count (int): 조회된 종목 수
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    natcode: str
    """ 국가구분 (예: "US") """
    exgubun: str
    """ 거래소구분 (예: "2") """
    cts_value: str
    """ 연속구분 (예: "0") """
    rec_count: int
    """ 조회된 종목 수 """


class G3190OutBlock1(BaseModel):
    """
    g3190OutBlock1 개별 종목 정보

    Attributes:
        keysymbol (str): KEY종목코드
        natcode (str): 국가코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        seccode (str): 거래소종목코드
        korname (str): 한글종목명
        engname (str): 영문종목명
        currency (str): 외환코드
        isin (str): ISIN
        floatpoint (str): FLOATPOINT
        indusury (str): 업종코드
        share (int): 상장주식수
        marketcap (int): 자본금
        par (int): 액면가
        parcurr (str): 액면가외환코드
        bidlotsize2 (int): 매수주문단위2
        asklotsize2 (int): 매도주문단위2
        clos (float): 기준가
        listed_date (str): 상장일자
        expire_date (str): 만기일자
        suspend (str): 거래정지여부
        bymd (str): 영업일자
        sellonly (str): SELLONLY구분
        stamp (str): 인지세여부
        ticktype (str): TICKSIZETYPE
        pcls (str): 전일종가
        vcmf (str): VCM대상종목
        casf (str): CAS대상종목
        posf (str): POS대상종목
        point (str): 소수점매매가능종목
    """
    keysymbol: str
    """ KEY종목코드 """
    natcode: str
    """ 국가코드 """
    exchcd: str
    """ 거래소코드 """
    symbol: str
    """ 종목코드 """
    seccode: str
    """ 거래소종목코드 """
    korname: str
    """ 한글종목명 """
    engname: str
    """ 영문종목명 """
    currency: str
    """ 외환코드 """
    isin: str
    """ ISIN """
    floatpoint: str
    """ FLOATPOINT """
    indusury: str
    """ 업종코드 """
    share: int
    """ 상장주식수 """
    marketcap: int
    """ 자본금 """
    par: float
    """ 액면가 """
    parcurr: str
    """ 액면가외환코드 """
    bidlotsize2: int
    """ 매수주문단위2 """
    asklotsize2: int
    """ 매도주문단위2 """
    clos: float
    """ 기준가 """
    listed_date: str
    """ 상장일자 """
    expire_date: str
    """ 만기일자 """
    suspend: str
    """ 거래정지여부 """
    bymd: str
    """ 영업일자 """
    sellonly: str
    """ SELLONLY구분 """
    stamp: str
    """ 인지세여부 """
    ticktype: str
    """ TICKSIZETYPE """
    pcls: str
    """ 전일종가 """
    vcmf: str
    """ VCM대상종목 """
    casf: str
    """ CAS대상종목 """
    posf: str
    """ POS대상종목 """
    point: str
    """ 소수점매매가능종목 """


class G3190Response(BaseModel):
    """
    G3190 API 전체 응답

    Attributes:
        header (Optional[G3190ResponseHeader])
        block (Optional[G3190OutBlock])
        block1 (Optional[List[G3190OutBlock1]])
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[G3190ResponseHeader]
    block: Optional[G3190OutBlock]
    block1: List[G3190OutBlock1] = Field(
        default_factory=list,
        title="상세 리스트",
        description="상세 리스트 (여러 레코드)"
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
