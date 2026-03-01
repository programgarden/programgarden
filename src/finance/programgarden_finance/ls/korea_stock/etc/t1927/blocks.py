from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1927RequestHeader(BlockRequestHeader):
    """T1927 요청용 Header"""
    pass


class T1927ResponseHeader(BlockResponseHeader):
    """T1927 응답용 Header"""
    pass


class T1927InBlock(BaseModel):
    """공매도일별추이 입력 블록"""
    shcode: str = Field(default="", description="종목코드")
    date: str = Field(default="", description="일자")
    sdate: str = Field(default="", description="시작일자")
    edate: str = Field(default="", description="종료일자")


class T1927OutBlock(BaseModel):
    """공매도일별추이 출력 블록 - t1927OutBlock"""
    date: str = Field(default="", description="일자CTS")


class T1927OutBlock1(BaseModel):
    """공매도일별추이 출력 블록 - t1927OutBlock1"""
    date: str = Field(default="", description="일자")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="거래량")
    value: int = Field(default=0, description="거래대금")
    gm_vo: int = Field(default=0, description="공매도수량")
    gm_va: int = Field(default=0, description="공매도대금")
    gm_per: float = Field(default=0.0, description="공매도거래비중")
    gm_avg: int = Field(default=0, description="평균공매도단가")
    gm_vo_sum: int = Field(default=0, description="누적공매도수량")
    gm_vo1: int = Field(default=0, description="업틱룰적용공매도수량")
    gm_va1: int = Field(default=0, description="업틱룰적용공매도대금")
    gm_vo2: int = Field(default=0, description="업틱룰예외공매도수량")
    gm_va2: int = Field(default=0, description="업틱룰예외공매도대금")


class T1927Request(BaseModel):
    """공매도일별추이 요청 모델"""
    header: T1927RequestHeader = T1927RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1927",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1927Response(BaseModel):
    """공매도일별추이 응답 모델"""
    header: Optional[T1927ResponseHeader] = None
    cont_block: Optional[T1927OutBlock] = None
    block: list[T1927OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1927RequestHeader",
    "T1927ResponseHeader",
    "T1927InBlock",
    "T1927OutBlock",
    "T1927OutBlock1",
    "T1927Request",
    "T1927Response",
]
