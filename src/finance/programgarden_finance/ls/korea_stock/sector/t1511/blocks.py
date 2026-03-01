from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1511RequestHeader(BlockRequestHeader):
    """t1511 요청용 Header"""
    pass


class T1511ResponseHeader(BlockResponseHeader):
    """t1511 응답용 Header"""
    pass


class T1511InBlock(BaseModel):
    """
    t1511InBlock - 업종현재가 입력 블록

    Attributes:
        upcode (str): 업종코드 (코스피@001, 코스피200@101, KRX100@501, 코스닥@301)
    """
    upcode: str
    """ 업종코드 (코스피@001, 코스피200@101, KRX100@501, 코스닥@301) """


class T1511Request(BaseModel):
    """
    T1511 API 요청 - 업종현재가

    Attributes:
        header (T1511RequestHeader)
        body (Dict[Literal["t1511InBlock"], T1511InBlock])
    """
    header: T1511RequestHeader = T1511RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1511",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1511InBlock"], T1511InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=10,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1511"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1511OutBlock(BaseModel):
    """
    t1511OutBlock - 업종현재가 응답 블록
    """
    gubun: str = ""
    """ 업종구분 """
    hname: str = ""
    """ 업종명 """
    pricejisu: float = 0.0
    """ 현재지수 """
    jniljisu: float = 0.0
    """ 전일지수 """
    sign: str = ""
    """ 전일대비구분 """
    change: float = 0.0
    """ 전일대비 """
    diffjisu: float = 0.0
    """ 지수등락율 """
    jnilvolume: int = 0
    """ 전일거래량 """
    volume: int = 0
    """ 당일거래량 """
    volumechange: int = 0
    """ 거래량전일대비 """
    volumerate: float = 0.0
    """ 거래량비율 """
    jnilvalue: int = 0
    """ 전일거래대금 """
    value: int = 0
    """ 당일거래대금 """
    valuechange: int = 0
    """ 거래대금전일대비 """
    valuerate: float = 0.0
    """ 거래대금비율 """
    openjisu: float = 0.0
    """ 시가지수 """
    opendiff: float = 0.0
    """ 시가등락율 """
    opentime: str = ""
    """ 시가시간 """
    highjisu: float = 0.0
    """ 고가지수 """
    highdiff: float = 0.0
    """ 고가등락율 """
    hightime: str = ""
    """ 고가시간 """
    lowjisu: float = 0.0
    """ 저가지수 """
    lowdiff: float = 0.0
    """ 저가등락율 """
    lowtime: str = ""
    """ 저가시간 """
    whjisu: float = 0.0
    """ 52주최고지수 """
    whchange: float = 0.0
    """ 52주최고현재가대비 """
    whjday: str = ""
    """ 52주최고지수일자 """
    wljisu: float = 0.0
    """ 52주최저지수 """
    wlchange: float = 0.0
    """ 52주최저현재가대비 """
    wljday: str = ""
    """ 52주최저지수일자 """
    yhjisu: float = 0.0
    """ 연중최고지수 """
    yhchange: float = 0.0
    """ 연중최고현재가대비 """
    yhjday: str = ""
    """ 연중최고지수일자 """
    yljisu: float = 0.0
    """ 연중최저지수 """
    ylchange: float = 0.0
    """ 연중최저현재가대비 """
    yljday: str = ""
    """ 연중최저지수일자 """
    firstjcode: str = ""
    """ 첫번째지수코드 """
    firstjname: str = ""
    """ 첫번째지수명 """
    firstjisu: float = 0.0
    """ 첫번째지수 """
    firsign: str = ""
    """ 첫번째대비구분 """
    firchange: float = 0.0
    """ 첫번째전일대비 """
    firdiff: float = 0.0
    """ 첫번째등락율 """
    secondjcode: str = ""
    """ 두번째지수코드 """
    secondjname: str = ""
    """ 두번째지수명 """
    secondjisu: float = 0.0
    """ 두번째지수 """
    secsign: str = ""
    """ 두번째대비구분 """
    secchange: float = 0.0
    """ 두번째전일대비 """
    secdiff: float = 0.0
    """ 두번째등락율 """
    thirdjcode: str = ""
    """ 세번째지수코드 """
    thirdjname: str = ""
    """ 세번째지수명 """
    thirdjisu: float = 0.0
    """ 세번째지수 """
    thrsign: str = ""
    """ 세번째대비구분 """
    thrchange: float = 0.0
    """ 세번째전일대비 """
    thrdiff: float = 0.0
    """ 세번째등락율 """
    fourthjcode: str = ""
    """ 네번째지수코드 """
    fourthjname: str = ""
    """ 네번째지수명 """
    fourthjisu: float = 0.0
    """ 네번째지수 """
    forsign: str = ""
    """ 네번째대비구분 """
    forchange: float = 0.0
    """ 네번째전일대비 """
    fordiff: float = 0.0
    """ 네번째등락율 """
    highjo: int = 0
    """ 상승종목수 """
    upjo: int = 0
    """ 상한종목수 """
    unchgjo: int = 0
    """ 보합종목수 """
    lowjo: int = 0
    """ 하락종목수 """
    downjo: int = 0
    """ 하한종목수 """


class T1511Response(BaseModel):
    """
    T1511 API 전체 응답 - 업종현재가
    """
    header: Optional[T1511ResponseHeader] = None
    block: Optional[T1511OutBlock] = Field(
        None, title="업종현재가 데이터",
        description="업종 지수, 등락률, 거래량, 52주 고저가 등"
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
