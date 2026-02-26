from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1904RequestHeader(BlockRequestHeader):
    """T1904 요청용 Header"""
    pass


class T1904ResponseHeader(BlockResponseHeader):
    """T1904 응답용 Header"""
    pass


class T1904InBlock(BaseModel):
    """ETF구성종목조회 입력 블록"""
    shcode: str = Field(default="", description="ETF단축코드")
    date: str = Field(default="", description="PDF적용일자")
    sgb: str = Field(default="", description="정렬기준(1:평가금액2:증권수)")


class T1904OutBlock(BaseModel):
    """ETF구성종목조회 출력 블록 - t1904OutBlock"""
    chk_tday: str = Field(default="", description="당일구분")
    date: str = Field(default="", description="PDF적용일자")
    price: int = Field(default=0, description="ETF현재가")
    sign: str = Field(default="", description="ETF전일대비구분")
    change: int = Field(default=0, description="ETF전일대비")
    diff: float = Field(default=0.0, description="ETF등락율")
    volume: int = Field(default=0, description="ETF누적거래량")
    nav: float = Field(default=0.0, description="NAV")
    navsign: str = Field(default="", description="NAV전일대비구분")
    navchange: float = Field(default=0.0, description="NAV전일대비")
    navdiff: float = Field(default=0.0, description="NAV등락율")
    jnilnav: float = Field(default=0.0, description="전일NAV")
    jnilnavsign: str = Field(default="", description="전일NAV전일대비구분")
    jnilnavchange: float = Field(default=0.0, description="전일NAV전일대비")
    jnilnavdiff: float = Field(default=0.0, description="전일NAV등락율")
    upname: str = Field(default="", description="업종명")
    upcode: str = Field(default="", description="업종코드")
    upprice: float = Field(default=0.0, description="업종현재가")
    upsign: str = Field(default="", description="업종전일비구분")
    upchange: float = Field(default=0.0, description="업종전일대비")
    updiff: float = Field(default=0.0, description="업종등락율")
    futname: str = Field(default="", description="선물최근월물명")
    futcode: str = Field(default="", description="선물최근월물코드")
    futprice: float = Field(default=0.0, description="선물현재가")
    futsign: str = Field(default="", description="선물전일비구분")
    futchange: float = Field(default=0.0, description="선물전일대비")
    futdiff: float = Field(default=0.0, description="선물등락율")
    upname2: str = Field(default="", description="참고지수명")
    upcode2: str = Field(default="", description="참고지수코드")
    upprice2: float = Field(default=0.0, description="참고지수현재가")
    etftotcap: int = Field(default=0, description="순자산총액(단위:억)")
    etfnum: int = Field(default=0, description="구성종목수")
    etfcunum: int = Field(default=0, description="CU주식수")
    cash: int = Field(default=0, description="현금")
    opcom_nmk: str = Field(default="", description="운용사명")
    tot_pval: int = Field(default=0, description="전종목평가금액합")
    tot_sigatval: int = Field(default=0, description="전종목구성시가총액합")


class T1904OutBlock1(BaseModel):
    """ETF구성종목조회 출력 블록 - t1904OutBlock1"""
    shcode: str = Field(default="", description="단축코드")
    hname: str = Field(default="", description="한글명")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="누적거래량")
    value: int = Field(default=0, description="거래대금(백만)")
    icux: int = Field(default=0, description="단위증권수(계약수/원화현금/USD현금/창고증권)")
    parprice: int = Field(default=0, description="액면금액/설정현금액")
    pvalue: int = Field(default=0, description="평가금액")
    sigatvalue: int = Field(default=0, description="구성시가총액")
    profitdate: str = Field(default="", description="PDF적용일자")
    weight: float = Field(default=0.0, description="비중(평가금액)")
    diff2: float = Field(default=0.0, description="ETF종목과등락차")


class T1904Request(BaseModel):
    """ETF구성종목조회 요청 모델"""
    header: T1904RequestHeader = T1904RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1904",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1904Response(BaseModel):
    """ETF구성종목조회 응답 모델"""
    header: Optional[T1904ResponseHeader] = None
    cont_block: Optional[T1904OutBlock] = None
    block: list[T1904OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1904RequestHeader",
    "T1904ResponseHeader",
    "T1904InBlock",
    "T1904OutBlock",
    "T1904OutBlock1",
    "T1904Request",
    "T1904Response",
]
