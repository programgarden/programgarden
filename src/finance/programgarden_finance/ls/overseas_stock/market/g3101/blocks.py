from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3101RequestHeader(BlockRequestHeader):
    pass


class G3101ResponseHeader(BlockResponseHeader):
    pass


class G3101InBlock(BaseModel):
    """
    g3101InBlock 입력 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (Literal["81", "82"]): 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥)
        symbol (str): 종목코드 (예: "TSLA")
    """
    delaygb: Literal["R"] = "R"
    keysymbol: str
    exchcd: Literal["81", "82"]
    symbol: str


class G3101Request(BaseModel):
    """
    G3101 API 요청

    Attributes:
        header (G3101RequestHeader)
        body (dict[Literal["g3101InBlock"], G3101InBlock])
    """
    header: G3101RequestHeader = G3101RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3101",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["g3101InBlock"], G3101InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3101"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3101OutBlock(BaseModel):
    """
    g3101OutBlock 응답 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (Literal["81", "82"]): 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥)
        exchange (str): 거래소ID
        suspend (Literal["Y", "N"]): 거래상태 (Y: 정지, N: 보통)
        sellonly (Literal[0, 1, 2]): 매매구분 (0: 매매가능, 1: 매도만가능, 2: 매매불가)
        symbol (str): 종목코드
        korname (str): 한글종목명
        induname (str): 업종한글명
        low52p (str): 52주최저가
        floatpoint (str): 소숫점자릿수
        currency (str): 외환코드
        price (str): 현재가
        sign (str): 전일대비구분
        diff (str): 전일대비
        rate (str): 등락률
        volume (int): 거래량
        amount (int): 거래대금
        high52p (str): 52주최고가
        uplimit (str): 상한가
        dnlimit (str): 하한가
        open (str): 시가
        high (str): 고가
        low (str): 저가
        perv (str): PER
        epsv (str): EPS
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    exchange: str
    """ 거래소ID """
    suspend: Literal["Y", "N"]
    """ 거래상태 (Y: 정지, N: 보통) """
    sellonly: Literal[0, 1, 2]
    """ 매매구분 (0: 매매가능, 1: 매도만가능, 2: 매매불가) """
    symbol: str
    """ 종목코드 """
    korname: str
    """ 한글종목명 """
    induname: str
    """ 업종한글명 """
    low52p: str
    """ 52주최저가 """
    floatpoint: str
    """ 소숫점자릿수 """
    currency: str
    """ 외환코드 """
    price: str
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    diff: str
    """ 전일대비 """
    rate: float
    """ 등락률 """
    volume: int
    """ 거래량 """
    amount: int
    """ 거래대금 """
    high52p: str
    """ 52주최고가 """
    uplimit: str
    """ 상한가 """
    dnlimit: str
    """ 하한가 """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    perv: str
    """ PER """
    epsv: str
    """ EPS """


class G3101Response(BaseModel):
    """
    G3101 API 전체 응답

    Attributes:
        header (Optional[G3101ResponseHeader])
        block (Optional[G3101OutBlock])
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[G3101ResponseHeader]
    block: Optional[G3101OutBlock]
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
