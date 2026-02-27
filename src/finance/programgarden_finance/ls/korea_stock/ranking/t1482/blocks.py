from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1482RequestHeader(BlockRequestHeader):
    """T1482 요청용 Header"""
    pass


class T1482ResponseHeader(BlockResponseHeader):
    """T1482 응답용 Header"""
    pass


class T1482InBlock(BaseModel):
    """시간외거래량상위 입력 블록"""
    sort_gbn: Literal[0, 1] = Field(default=0, description="정렬구분(0:거래량, 1:거래대금)")
    gubun: Literal["0", "1", "2"] = Field(default="0", description="구분(0:전체, 1:코스피, 2:코스닥)")
    jongchk: Literal["0", "1", "2", "3"] = Field(default="0", description="거래량(0:전체, 1:우선제외, 2:관리제외, 3:우선관리제외)")
    idx: int = Field(default=0, description="IDX(연속조회시 OutBlock의 idx 입력)")


class T1482OutBlock(BaseModel):
    """시간외거래량상위 출력 블록 - t1482OutBlock"""
    idx: int = Field(default=0, description="IDX")


class T1482OutBlock1(BaseModel):
    """시간외거래량상위 출력 블록 - t1482OutBlock1"""
    hname: str = Field(default="", description="종목명")
    price: int = Field(default=0, description="현재가")
    sign: str = Field(default="", description="전일대비구분")
    change: int = Field(default=0, description="전일대비")
    diff: float = Field(default=0.0, description="등락율")
    volume: int = Field(default=0, description="누적거래량")
    vol: float = Field(default=0.0, description="회전율")
    shcode: str = Field(default="", description="종목코드")
    value: int = Field(default=0, description="누적거래대금")


class T1482Request(BaseModel):
    """시간외거래량상위 요청 모델"""
    header: T1482RequestHeader = T1482RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1482",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1482"
    )
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1482Response(BaseModel):
    """시간외거래량상위 응답 모델"""
    header: Optional[T1482ResponseHeader] = None
    cont_block: Optional[T1482OutBlock] = None
    block: list[T1482OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1482RequestHeader",
    "T1482ResponseHeader",
    "T1482InBlock",
    "T1482OutBlock",
    "T1482OutBlock1",
    "T1482Request",
    "T1482Response",
]
