from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8407RequestHeader(BlockRequestHeader):
    """T8407 요청용 Header"""
    pass


class T8407ResponseHeader(BlockResponseHeader):
    """T8407 응답용 Header"""
    pass


class T8407InBlock(BaseModel):
    """API용주식멀티현재가조회 입력 블록"""
    nrec: int = Field(default=0, description="건수")
    shcode: str = Field(default="", description="종목코드")


class T8407OutBlock1(BaseModel):
    """API용주식멀티현재가조회 출력 블록 - t8407OutBlock1"""
    shcode: str = Field(default="", description="종목코드")
    hname: str = Field(default="", description="종목명")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="누적거래량")
    offerho: int = Field(default=0, description="매도호가")
    bidho: int = Field(default=0, description="매수호가")
    cvolume: int = Field(default=0, description="체결수량")
    chdegree: float = Field(default=0.0, description="체결강도")
    open: int = Field(default=0, description="시가")
    high: int = Field(default=0, description="고가")
    low: int = Field(default=0, description="저가")
    value: int = Field(default=0, description="거래대금(백만)")
    offerrem: int = Field(default=0, description="우선매도잔량")
    bidrem: int = Field(default=0, description="우선매수잔량")
    totofferrem: int = Field(default=0, description="총매도잔량")
    totbidrem: int = Field(default=0, description="총매수잔량")
    jnilclose: int = Field(default=0, description="전일종가")
    uplmtprice: int = Field(default=0, description="상한가")
    dnlmtprice: int = Field(default=0, description="하한가")


class T8407Request(BaseModel):
    """API용주식멀티현재가조회 요청 모델"""
    header: T8407RequestHeader = T8407RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8407",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8407Response(BaseModel):
    """API용주식멀티현재가조회 응답 모델"""
    header: Optional[T8407ResponseHeader] = None
    block: list[T8407OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8407RequestHeader",
    "T8407ResponseHeader",
    "T8407InBlock",
    "T8407OutBlock1",
    "T8407Request",
    "T8407Response",
]
