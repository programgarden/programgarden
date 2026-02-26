from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1903RequestHeader(BlockRequestHeader):
    """T1903 요청용 Header"""
    pass


class T1903ResponseHeader(BlockResponseHeader):
    """T1903 응답용 Header"""
    pass


class T1903InBlock(BaseModel):
    """ETF일별추이 입력 블록"""
    shcode: str = Field(default="", description="단축코드")
    date: str = Field(default="", description="일자")


class T1903OutBlock(BaseModel):
    """ETF일별추이 출력 블록 - t1903OutBlock"""
    date: str = Field(default="", description="일자")
    hname: str = Field(default="", description="종목명")
    upname: str = Field(default="", description="업종지수명")


class T1903OutBlock1(BaseModel):
    """ETF일별추이 출력 블록 - t1903OutBlock1"""
    date: str = Field(default="", description="일자")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    volume: int = Field(default=0, description="누적거래량")
    navdiff: float = Field(default=0.0, description="NAV대비")
    nav: float = Field(default=0.0, description="NAV")
    navchange: float = Field(default=0.0, description="전일대비")
    crate: float = Field(default=0.0, description="추적오차")
    grate: float = Field(default=0.0, description="괴리")
    jisu: float = Field(default=0.0, description="지수")
    jichange: float = Field(default=0.0, description="전일대비")
    jirate: float = Field(default=0.0, description="전일대비율")


class T1903Request(BaseModel):
    """ETF일별추이 요청 모델"""
    header: T1903RequestHeader = T1903RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1903",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1903Response(BaseModel):
    """ETF일별추이 응답 모델"""
    header: Optional[T1903ResponseHeader] = None
    cont_block: Optional[T1903OutBlock] = None
    block: list[T1903OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1903RequestHeader",
    "T1903ResponseHeader",
    "T1903InBlock",
    "T1903OutBlock",
    "T1903OutBlock1",
    "T1903Request",
    "T1903Response",
]
