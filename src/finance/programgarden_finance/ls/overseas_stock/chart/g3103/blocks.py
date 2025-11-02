from typing import List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class G3103RequestHeader(BlockRequestHeader):
    pass


class G3103ResponseHeader(BlockResponseHeader):
    pass


class G3103InBlock(BaseModel):
    """
    g3103InBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        keysymbol (str): KEY종목코드 (예: "82TSLA")
        exchcd (str): 거래소코드 (예: "82" - 나스닥)
        symbol (str): 종목코드 (예: "TSLA")
        gubun (Literal["2", "3", "4"]): 주기구분 (2: 일봉, 3: 주봉, 4: 월봉)
        date (str): 조회일자 (YYYYMMDD 형식, 예: "20231001")
    """
    delaygb: Literal["R"] = Field(
        default="R",
        title="지연구분",
        description="지연구분 (항상 R으로 유지)"
    )
    """ 지연구분 (항상 R으로 유지) """
    keysymbol: str = Field(
        ...,
        title="KEY종목코드",
        description="KEY종목코드 (예: \"82TSLA\")"
    )
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str = Field(
        ...,
        title="거래소코드",
        description="거래소코드 (예: \"82\" - 나스닥)"
    )
    """ 거래소코드 (예: "82" - 나스닥) """
    symbol: str = Field(
        ...,
        title="종목코드",
        description="종목코드 (예: \"TSLA\")"
    )
    """ 종목코드 (예: "TSLA") """
    gubun: Literal["2", "3", "4"] = Field(
        ...,
        title="주기구분",
        description="주기구분 (2: 일봉, 3: 주봉, 4: 월봉)"
    )
    """ 주기구분 (2: 일봉, 3: 주봉, 4: 월봉) """
    date: str = Field(
        ...,
        title="조회일자",
        description="조회일자 (YYYYMMDD 형식, 예: \"20231001\")"
    )
    """ 조회일자 (YYYYMMDD 형식, 예: "20231001") """


class G3103Request(BaseModel):
    """
    G3103 API 요청 클래스.

    Attributes:
        header (G3103RequestHeader): 요청 헤더
        body (dict[Literal["g3103InBlock"], G3103InBlock]): 입력 블록
    """
    header: G3103RequestHeader = G3103RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="g3103",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    """요청 헤더 데이터 블록"""
    body: dict[Literal["g3103InBlock"], G3103InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="주문 내역 조회를 위한 입력 데이터 블록"
    )
    """ 입력 데이터 블록"""
    options: SetupOptions = SetupOptions(
        rate_limit_count=3,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="g3103"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class G3103OutBlock(BaseModel):
    """
    g3103OutBlock 데이터 블록

    Attributes:
        delaygb (Literal["R"]): 지연구분 (항상 R으로 유지)
        keysymbol (str): KEY종목코드
        exchcd (str): 거래소코드
        symbol (str): 종목코드
        gubun (Literal["2", "3", "4"]): 주기구분 (2: 일봉, 3: 주봉, 4: 월봉)
        date (str): 조회일자
    """
    delaygb: Literal["R"] = "R"
    """ 지연구분 (항상 R으로 유지) """
    keysymbol: str
    """ KEY종목코드 (예: "82TSLA") """
    exchcd: str
    """ 거래소코드 (예: "82" - 나스닥) """
    symbol: str
    """ 종목코드 (예: "TSLA") """
    gubun: Literal["2", "3", "4"]
    """ 주기구분 (2: 일봉, 3: 주봉, 4: 월봉) """
    date: str
    """ 조회일자 (YYYYMMDD 형식, 예: "20231001") """


class G3103OutBlock1(BaseModel):
    """
    g3103OutBlock1 데이터 블록 리스트 항목

    Attributes:
        chedate (str): 영업일자 (YYYYMMDD 형식)
        price (str): 현재가 (예: "1500.00")
        sign (str): 전일대비구분 (예: "+" 상승, "-" 하락)
        diff (str): 전일대비 차이 (예: "10.00")
        rate (str): 등락률 (예: "0.67")
        volume (int): 누적거래량 (예: 1000000)
        open (str): 시가 (예: "1480.00")
        high (str): 고가 (예: "1520.00")
        low (str): 저가 (예: "1470.00")
        floatpoint (str): 소숫점자릿수 (예: "4")
    """
    chedate: str
    """ 영업일자 (YYYYMMDD 형식) """
    price: str
    """ 현재가 """
    sign: str
    """ 전일대비구분 (예: "+" 상승, "-" 하락) """
    diff: str
    """ 전일대비 차이 """
    rate: float
    """ 등락률 """
    volume: int
    """ 누적거래량 """
    open: float
    """ 시가 """
    high: float
    """ 고가 """
    low: float
    """ 저가 """
    floatpoint: str
    """ 소숫점자릿수 (예: "4") """


class G3103Response(BaseModel):
    """
    G3103 API 응답 전체 구조

    Attributes:
        header (Optional[G3103ResponseHeader]): 응답 헤더
        block (Optional[G3103OutBlock]): 기본 응답 블록
        block1 (List[G3103OutBlock1]): 상세 리스트
        status_code (Optional[int]): HTTP 상태 코드
        rsp_cd (str): 응답코드
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 오류메시지
    """
    header: Optional[G3103ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[G3103OutBlock] = Field(
        None,
        title="기본 응답 블록",
        description="기본 응답 데이터 블록"
    )
    block1: List[G3103OutBlock1] = Field(
        default_factory=list,
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
