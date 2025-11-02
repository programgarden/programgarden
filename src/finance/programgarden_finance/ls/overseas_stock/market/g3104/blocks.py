from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3104RequestHeader(BlockRequestHeader):
    pass


class G3104ResponseHeader(BlockResponseHeader):
    pass


class G3104InBlock(BaseModel):
    """
    g3104InBlock 입력 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (Literal["81", "82"]): 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥)
        symbol (str): 종목코드 (예: "TSLA")
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    symbol: str
    """ 종목코드 (예: "TSLA") """


class G3104Request(BaseModel):
    """
    G3104 API 요청

    Attributes:
        header (G3104RequestHeader)
        body (Dict[Literal["g3104InBlock"], G3104InBlock])
    """
    header: G3104RequestHeader = G3104RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3104",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["g3104InBlock"], G3104InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3104"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3104OutBlock(BaseModel):
    """
    g3104OutBlock 응답 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분
        keysymbol (str): KEY종목코드
        exchcd (Literal["81", "82"]): 거래소코드
        exchange (str): 거래소ID
        symbol (str): 종목코드
        korname (str): 한글종목명
        engname (str): 영문종목명
        exchange_name (str): 거래소명
        nation_name (str): 국가명
        induname (str): 업종명
        instname (str): 증권종류
        floatpoint (str): 소숫점자릿수
        currency (str): 거래통화
        suspend (str): 거래상태
        sellonly (str): 매매구분
        share (int): 발행주식수
        untprc (float): 호가단위
        bidlotsize (int): 매수주문단위
        asklotsize (int): 매도주문단위
        volume (int): 거래량
        amount (int): 거래대금
        pcls (float): 전일종가
        clos (float): 기준가
        open (float): 시가
        high (float): 고가
        low (float): 저가
        high52p (float): 52주고가
        low52p (float): 52주저가
        shareprc (int): 시가총액
        perv (float): PER
        epsv (float): EPS
        exrate (float): 환율
        bidlotsize2 (int): 매수주문단위2
        asklotsize2 (int): 매도주문단위2
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    exchange: str
    """ 거래소ID """
    symbol: str
    """ 종목코드 (예: "TSLA") """
    korname: str
    """ 한글종목명 """
    engname: str
    """ 영문종목명 """
    exchange_name: str
    """ 거래소명 """
    nation_name: str
    """ 국가명 """
    induname: str
    """ 업종명 """
    instname: str
    """ 증권종류 """
    floatpoint: str
    """ 소숫점자릿수 """
    currency: str
    """ 거래통화 """
    suspend: str
    """ 거래상태 """
    sellonly: str
    """ 매매구분 """
    share: int
    """ 발행주식수 """
    untprc: float
    """ 호가단위 """
    bidlotsize: int
    """ 매수주문단위 """
    asklotsize: int
    """ 매도주문단위 """
    volume: int
    """ 거래량 """
    amount: int
    """ 거래대금 """
    pcls: float
    """ 전일종가 """
    clos: float
    """ 기준가 """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    high52p: str
    """ 52주고가 """
    low52p: str
    """ 52주저가 """
    shareprc: int
    """ 시가총액 """
    perv: float
    """ PER """
    epsv: float
    """ EPS """
    exrate: float
    """ 환율 """
    bidlotsize2: int
    """ 매수주문단위2 """
    asklotsize2: int
    """ 매도주문단위2 """


class G3104Response(BaseModel):
    """
    G3104 API 전체 응답

    Attributes:
        header (Optional[G3104ResponseHeader])
        block (Optional[G3104OutBlock])
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[G3104ResponseHeader]
    block: Optional[G3104OutBlock]
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
