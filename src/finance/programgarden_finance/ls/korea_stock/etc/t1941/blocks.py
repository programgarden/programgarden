from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1941RequestHeader(BlockRequestHeader):
    """T1941 요청용 Header"""
    pass


class T1941ResponseHeader(BlockResponseHeader):
    """T1941 응답용 Header"""
    pass


class T1941InBlock(BaseModel):
    """종목별대차거래일간추이 입력 블록"""
    shcode: str = Field(default="", description="종목코드")
    sdate: str = Field(default="", description="시작일자")
    edate: str = Field(default="", description="종료일자")


class T1941OutBlock1(BaseModel):
    """종목별대차거래일간추이 출력 블록 - t1941OutBlock1"""
    date: str = Field(default="", description="일자")
    price: int = Field(default=0, description="종가")
    sign: str = Field(default="", description="대비구분")
    change: int = Field(default=0, description="대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="거래량")
    upvolume: int = Field(default=0, description="당일체결")
    dnvolume: int = Field(default=0, description="당일상환")
    tovolume: int = Field(default=0, description="당일잔고")
    tovalue: int = Field(default=0, description="잔고금액")
    shcode: str = Field(default="", description="종목코드")
    tovoldif: int = Field(default=0, description="대차증감")


class T1941Request(BaseModel):
    """종목별대차거래일간추이 요청 모델"""
    header: T1941RequestHeader = T1941RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1941",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1941"
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1941Response(BaseModel):
    """종목별대차거래일간추이 응답 모델"""
    header: Optional[T1941ResponseHeader] = None
    block: list[T1941OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1941RequestHeader",
    "T1941ResponseHeader",
    "T1941InBlock",
    "T1941OutBlock1",
    "T1941Request",
    "T1941Response",
]
