from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T8454RequestHeader(BlockRequestHeader):
    """T8454 요청용 Header"""
    pass


class T8454ResponseHeader(BlockResponseHeader):
    """T8454 응답용 Header"""
    pass


class T8454InBlock(BaseModel):
    """(통합)주식시간대별체결2 API용 입력 블록"""
    shcode: str = Field(default="", description="단축코드")
    cvolume: int = Field(default=0, description="특이거래량")
    starttime: str = Field(default="", description="시작시간")
    endtime: str = Field(default="", description="종료시간")
    cts_time: str = Field(default="", description="시간CTS")
    exchgubun: str = Field(default="", description="거래소구분코드")


class T8454OutBlock(BaseModel):
    """(통합)주식시간대별체결2 API용 출력 블록 - t8454OutBlock"""
    cts_time: str = Field(default="", description="시간CTS")
    ex_shcode: str = Field(default="", description="거래소별단축코드")


class T8454OutBlock1(BaseModel):
    """(통합)주식시간대별체결2 API용 출력 블록 - t8454OutBlock1"""
    chetime: str = Field(default="", description="시간")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    cvolume: int = Field(default=0, description="체결수량")
    chdegree: float = Field(default=0.0, description="체결강도")
    volume: int = Field(default=0, description="거래량")
    mdvolume: int = Field(default=0, description="매도체결수량")
    mdchecnt: int = Field(default=0, description="매도체결건수")
    msvolume: int = Field(default=0, description="매수체결수량")
    mschecnt: int = Field(default=0, description="매수체결건수")
    revolume: int = Field(default=0, description="순체결량")
    rechecnt: int = Field(default=0, description="순체결건수")
    exchname: str = Field(default="", description="거래소명")


class T8454Request(BaseModel):
    """(통합)주식시간대별체결2 API용 요청 모델"""
    header: T8454RequestHeader = T8454RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t8454",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T8454Response(BaseModel):
    """(통합)주식시간대별체결2 API용 응답 모델"""
    header: Optional[T8454ResponseHeader] = None
    cont_block: Optional[T8454OutBlock] = None
    block: list[T8454OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T8454RequestHeader",
    "T8454ResponseHeader",
    "T8454InBlock",
    "T8454OutBlock",
    "T8454OutBlock1",
    "T8454Request",
    "T8454Response",
]
