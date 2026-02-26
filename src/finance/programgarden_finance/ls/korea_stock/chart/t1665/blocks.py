from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1665RequestHeader(BlockRequestHeader):
    """T1665 요청용 Header"""
    pass


class T1665ResponseHeader(BlockResponseHeader):
    """T1665 응답용 Header"""
    pass


class T1665InBlock(BaseModel):
    """TR명 입력 블록"""
    market: str = Field(default="", description="시장구분")


class T1665OutBlock(BaseModel):
    """TR명 출력 블록 - t1665OutBlock"""
    mcode: str = Field(default="", description="시장코드")
    mname: str = Field(default="", description="시장명")
    ex_upcode: str = Field(default="", description="거래소별업종코드")


class T1665OutBlock1(BaseModel):
    """TR명 출력 블록 - t1665OutBlock1"""
    date: str = Field(default="", description="일자")
    sv_08: int = Field(default=0, description="개인수량")
    sv_17: int = Field(default=0, description="외인계수량(등록+미등록)")
    sv_18: int = Field(default=0, description="기관계수량")
    sv_01: int = Field(default=0, description="증권수량")
    sv_03: int = Field(default=0, description="투신수량")
    sv_04: int = Field(default=0, description="은행수량")
    sv_02: int = Field(default=0, description="보험수량")
    sv_05: int = Field(default=0, description="종금수량")
    sv_06: int = Field(default=0, description="기금수량")
    sv_07: int = Field(default=0, description="기타수량")
    sv_00: int = Field(default=0, description="사모펀드수량")
    sv_09: int = Field(default=0, description="등록외국인수량")
    sv_10: int = Field(default=0, description="미등록외국인수량")
    sv_11: int = Field(default=0, description="국가수량")
    sv_99: int = Field(default=0, description="기타계수량(기타+국가)")
    sa_08: int = Field(default=0, description="개인금액")
    sa_17: int = Field(default=0, description="외인계금액(등록+미등록)")
    sa_18: int = Field(default=0, description="기관계금액")
    sa_01: int = Field(default=0, description="증권금액")
    sa_03: int = Field(default=0, description="투신금액")
    sa_04: int = Field(default=0, description="은행금액")
    sa_02: int = Field(default=0, description="보험금액")
    sa_05: int = Field(default=0, description="종금금액")
    sa_06: int = Field(default=0, description="기금금액")
    sa_07: int = Field(default=0, description="기타금액")
    sa_00: int = Field(default=0, description="사모펀드금액")
    sa_09: int = Field(default=0, description="등록외국인금액")
    sa_10: int = Field(default=0, description="미등록외국인금액")
    sa_11: int = Field(default=0, description="국가금액")
    sa_99: int = Field(default=0, description="기타계금액(기타+국가)")
    jisu: float = Field(default=0.0, description="시장지수")


class T1665Request(BaseModel):
    """TR명 요청 모델"""
    header: T1665RequestHeader = T1665RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1665",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict = {}
    options: SetupOptions = SetupOptions(rate_limit_count=1, rate_limit_seconds=1)
    _raw_data: Optional[Response] = PrivateAttr(default=None)


class T1665Response(BaseModel):
    """TR명 응답 모델"""
    header: Optional[T1665ResponseHeader] = None
    cont_block: Optional[T1665OutBlock] = None
    block: list[T1665OutBlock1] = []
    rsp_cd: str = ""
    rsp_msg: str = ""
    status_code: Optional[int] = None
    error_msg: Optional[str] = None
    raw_data: Optional[object] = None


__all__ = [
    "T1665RequestHeader",
    "T1665ResponseHeader",
    "T1665InBlock",
    "T1665OutBlock",
    "T1665OutBlock1",
    "T1665Request",
    "T1665Response",
]
