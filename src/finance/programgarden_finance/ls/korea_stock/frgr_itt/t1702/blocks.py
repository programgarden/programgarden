from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1702RequestHeader(BlockRequestHeader):
    """T1702 요청용 Header"""
    pass


class T1702ResponseHeader(BlockResponseHeader):
    """T1702 응답용 Header"""
    pass


class T1702InBlock(BaseModel):
    """TR명 입력 블록"""
    shcode: str = Field(default="", description="종목코드")
    fromdt: str = Field(default="", description="시작일자")
    todt: str = Field(default="", description="종료일자")
    volvalgb: str = Field(default="", description="금액수량구분(0:금액1:수량2:단가)")
    msmdgb: str = Field(default="", description="매수매도구분(0:순매수1:매수2:매도)")
    gubun: str = Field(default="", description="누적구분(0:일간1:누적)")
    exchgubun: str = Field(default="", description="거래소구분코드")


class T1702OutBlock1(BaseModel):
    """TR명 출력 블록 - t1702OutBlock1"""
    date: str = Field(default="", description="일자")
    close: int = Field(default=0, description="종가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="누적거래량")
    tjj0000: int = Field(default=0, description="사모펀드")
    tjj0001: int = Field(default=0, description="증권")
    tjj0002: int = Field(default=0, description="보험")
    tjj0003: int = Field(default=0, description="투신")
    tjj0004: int = Field(default=0, description="은행")
    tjj0005: int = Field(default=0, description="종금")
    tjj0006: int = Field(default=0, description="기금")
    tjj0007: int = Field(default=0, description="기타법인")
    tjj0008: int = Field(default=0, description="개인")
    tjj0009: int = Field(default=0, description="등록외국인")
    tjj0010: int = Field(default=0, description="미등록외국인")
    tjj0011: int = Field(default=0, description="국가외")
    tjj0018: int = Field(default=0, description="기관")
    tjj0016: int = Field(default=0, description="외인계(등록+미등록)")
    amt0017: int = Field(default=0, description="기타계(기타+국가)")
    value: int = Field(default=0, description="거래대금")


class T1702Request(BaseModel):
    """TR명 요청 모델"""
    header: T1702RequestHeader = T1702RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1702",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1702Response(BaseModel):
    """TR명 응답 모델"""
    header: Optional[T1702ResponseHeader] = None
    block: list[T1702OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1702RequestHeader",
    "T1702ResponseHeader",
    "T1702InBlock",
    "T1702OutBlock1",
    "T1702Request",
    "T1702Response",
]
