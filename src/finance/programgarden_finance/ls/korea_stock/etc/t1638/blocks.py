from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1638RequestHeader(BlockRequestHeader):
    """T1638 요청용 Header"""
    pass


class T1638ResponseHeader(BlockResponseHeader):
    """T1638 응답용 Header"""
    pass


class T1638InBlock(BaseModel):
    """종목별잔량/사전공시 입력 블록"""
    gubun1: str = Field(default="", description="구분")


class T1638OutBlock(BaseModel):
    """종목별잔량/사전공시 출력 블록 - t1638OutBlock"""
    rank: int = Field(default=0, description="순위")
    hname: str = Field(default="", description="한글명")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    sigatotrt: float = Field(default=0.0, description="시총비중")
    obuyvol: int = Field(default=0, description="순매수잔량")
    buyrem: int = Field(default=0, description="매수잔량")
    psgvolume: int = Field(default=0, description="매수공시수량")
    sellrem: int = Field(default=0, description="매도잔량")
    pdgvolume: int = Field(default=0, description="매도공시수량")
    sigatot: int = Field(default=0, description="시가총액")
    shcode: str = Field(default="", description="종목코드")


class T1638Request(BaseModel):
    """종목별잔량/사전공시 요청 모델"""
    header: T1638RequestHeader = T1638RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1638",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1638Response(BaseModel):
    """종목별잔량/사전공시 응답 모델"""
    header: Optional[T1638ResponseHeader] = None
    block: list[T1638OutBlock] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1638RequestHeader",
    "T1638ResponseHeader",
    "T1638InBlock",
    "T1638OutBlock",
    "T1638Request",
    "T1638Response",
]
