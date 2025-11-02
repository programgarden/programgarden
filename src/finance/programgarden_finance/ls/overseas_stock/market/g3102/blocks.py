from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3102RequestHeader(BlockRequestHeader):
    pass


class G3102ResponseHeader(BlockResponseHeader):
    pass


class G3102InBlock(BaseModel):
    """
    g3102InBlock 입력 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        symbol (str): 종목코드 (예: "TSLA")
        exchcd (Literal["81", "82"]): 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥)
        readcnt (int): 조회갯수
        cts_seq (int): 연속시퀀스
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    symbol: str
    """ 종목코드 (예: "TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    readcnt: int
    """ 조회갯수 """
    cts_seq: int = 0
    """ 연속시퀀스 """


class G3102Request(BaseModel):
    """
    G3102 API 요청

    Attributes:
        header (G3102RequestHeader)
        body (dict[Literal["g3102InBlock"], G3102InBlock])
    """
    header: G3102RequestHeader = G3102RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3102",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["g3102InBlock"], G3102InBlock]
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3102"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3102OutBlock(BaseModel):
    """
    g3102OutBlock 응답 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분
        keysymbol (str): KEY종목코드
        exchcd (Literal["81", "82"]): 거래소코드
        symbol (str): 종목코드
        cts_seq (int): 연속시퀀스
        rec_count (int): 레코드카운트
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: Literal["81", "82"]
    """ 거래소코드 (81: 뉴욕/아멕스, 82: 나스닥) """
    symbol: str
    """ 종목코드 """
    cts_seq: int
    """ 연속시퀀스 """
    rec_count: int
    """ 레코드카운트 """


class G3102OutBlock1(BaseModel):
    """
    g3102OutBlock1 응답 배열 블록

    Attributes:
        locdate (str): 현지일자
        loctime (str): 현지시간
        kordate (str): 한국일자
        kortime (str): 한국시간
        price (str): 현재가
        sign (str): 전일대비구분
        diff (str): 전일대비
        rate (str): 등락률
        open (str): 시가
        high (str): 고가
        low (str): 저가
        exevol (int): 체결량
        cgubun (str): 체결구분
        floatpoint (str): 소숫점자릿수
    """
    locdate: str
    """ 현지일자 """
    loctime: str
    """ 현지시간 """
    kordate: str
    """ 한국일자 """
    kortime: str
    """ 한국시간 """
    price: str
    """ 현재가 """
    sign: str
    """ 전일대비구분 """
    diff: str
    """ 전일대비 """
    rate: float
    """ 등락률 """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    exevol: int
    """ 체결량 """
    cgubun: str
    """ 체결구분 """
    floatpoint: str
    """ 소숫점자릿수 """


class G3102Response(BaseModel):
    """
    G3102 API 전체 응답

    Attributes:
        header (Optional[G3102ResponseHeader])
        block (Optional[G3102OutBlock])
        g3102OutBlock1 (Optional[List[G3102OutBlock1]])
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[G3102ResponseHeader]
    block: Optional[G3102OutBlock]
    block1: List[G3102OutBlock1] = Field(
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
