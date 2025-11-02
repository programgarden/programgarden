from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3106RequestHeader(BlockRequestHeader):
    pass


class G3106ResponseHeader(BlockResponseHeader):
    pass


class G3106InBlock(BaseModel):
    """
    g3106InBlock 입력 블록

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


class G3106Request(BaseModel):
    """
    G3106 API 요청

    Attributes:
        header (G3106RequestHeader)
        body (Dict[Literal["g3106InBlock"], G3106InBlock])
    """
    header: G3106RequestHeader = G3106RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3106",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["g3106InBlock"], G3106InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3106"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3106OutBlock(BaseModel):
    """
    g3106OutBlock 응답 블록

    Attributes:
        delaygb (Literal["R"])
        keysymbol (str)
        exchcd (Literal["81", "82"])
        symbol (str)
        korname (str)
        price (str)
        floatpoint (str)
        sign (str)
        diff (str)
        rate (str)
        volume (int)
        amount (int)
        jnilclose (str)
        open (str)
        high (str)
        low (str)
        hotime (str)
        offerho1 (str)
        bidho1 (str)
        offercnt1 (str)
        bidcnt1 (str)
        offerrem1 (int)
        bidrem1 (int)
        ... (up to 10 levels) ...
        offercnt (str)
        bidcnt (str)
        offer (int)
        bid (int)
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    symbol: str
    """ 종목코드 (예: "TSLA") """
    korname: str
    """ 한글종목명 """
    price: str
    """ 현재가 """
    floatpoint: str
    """ 소수점자리수 """
    sign: str
    """ 전일대비구분 """
    diff: str
    """ 전일대비 """
    rate: float
    """ 등락율 """
    volume: int
    """ 누적거래량 """
    amount: int
    """ 누적거래대금 """
    jnilclose: str
    """ 전일종가 """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    hotime: str
    """ 현지시간 """
    offerho1: str
    """ 매도호가1 """
    bidho1: str
    """ 매수호가1 """
    offercnt1: str
    """ 매도호가건수1 """
    bidcnt1: str
    """ 매수호가건수1 """
    offerrem1: int
    """ 매도호가수량1 """
    bidrem1: int
    """ 매수호가수량1 """
    offerho2: str
    """ 매도호가2 """
    bidho2: str
    """ 매수호가2 """
    offercnt2: str
    """ 매도호가건수2 """
    bidcnt2: str
    """ 매수호가건수2 """
    offerrem2: int
    """ 매도호가수량2 """
    bidrem2: int
    """ 매수호가수량2 """
    offerho3: str
    """ 매도호가3 """
    bidho3: str
    """ 매수호가3 """
    offercnt3: str
    """ 매도호가건수3 """
    bidcnt3: str
    """ 매수호가건수3 """
    offerrem3: int
    """ 매도호가수량3 """
    bidrem3: int
    """ 매수호가수량3 """
    offerho4: str
    """ 매도호가4 """
    bidho4: str
    """ 매수호가4 """
    offercnt4: str
    """ 매도호가건수4 """
    bidcnt4: str
    """ 매수호가건수4 """
    offerrem4: int
    """ 매도호가수량4 """
    bidrem4: int
    """ 매수호가수량4 """
    offerho5: str
    """ 매도호가5 """
    bidho5: str
    """ 매수호가5 """
    offercnt5: str
    """ 매도호가건수5 """
    bidcnt5: str
    """ 매수호가건수5 """
    offerrem5: int
    """ 매도호가수량5 """
    bidrem5: int
    """ 매수호가수량5 """
    offerho6: str
    """ 매도호가6 """
    bidho6: str
    """ 매수호가6 """
    offercnt6: str
    """ 매도호가건수6 """
    bidcnt6: str
    """ 매수호가건수6 """
    offerrem6: int
    """ 매도호가수량6 """
    bidrem6: int
    """ 매수호가수량6 """
    offerho7: str
    """ 매도호가7 """
    bidho7: str
    """ 매수호가7 """
    offercnt7: str
    """ 매도호가건수7 """
    bidcnt7: str
    """ 매수호가건수7 """
    offerrem7: int
    """ 매도호가수량7 """
    bidrem7: int
    """ 매수호가수량7 """
    offerho8: str
    """ 매도호가8 """
    bidho8: str
    """ 매수호가8 """
    offercnt8: str
    """ 매도호가건수8 """
    bidcnt8: str
    """ 매수호가건수8 """
    offerrem8: int
    """ 매도호가수량8 """
    bidrem8: int
    """ 매수호가수량8 """
    offerho9: str
    """ 매도호가9 """
    bidho9: str
    """ 매수호가9 """
    offercnt9: str
    """ 매도호가건수9 """
    bidcnt9: str
    """ 매수호가건수9 """
    offerrem9: int
    """ 매도호가수량9 """
    bidrem9: int
    """ 매수호가수량9 """
    offerho10: str
    """ 매도호가10 """
    bidho10: str
    """ 매수호가10 """
    offercnt10: str
    """ 매도호가건수10 """
    bidcnt10: str
    """ 매수호가건수10 """
    offerrem10: int
    """ 매도호가수량10 """
    bidrem10: int
    """ 매수호가수량10 """
    offercnt: str
    """ 총매도호가건수 """
    bidcnt: str
    """ 총매수호가건수 """
    offer: int
    """ 총매도호가수량 """
    bid: int
    """ 총매수호가수량 """


class G3106Response(BaseModel):
    """
    G3106 API 전체 응답

    Attributes:
        header (Optional[G3106ResponseHeader])
        block (Optional[G3106OutBlock])
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[G3106ResponseHeader]
    block: Optional[G3106OutBlock]
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
