from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1532RequestHeader(BlockRequestHeader):
    """t1532 요청용 Header"""
    pass


class T1532ResponseHeader(BlockResponseHeader):
    """t1532 응답용 Header"""
    pass


class T1532InBlock(BaseModel):
    """
    t1532InBlock - 종목별테마 입력 블록

    Attributes:
        shcode (str): 종목코드 (6자리)
    """
    shcode: str
    """ 종목코드 """


class T1532Request(BaseModel):
    """
    T1532 API 요청 - 종목별테마

    Attributes:
        header (T1532RequestHeader)
        body (Dict[Literal["t1532InBlock"], T1532InBlock])
    """
    header: T1532RequestHeader = T1532RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1532",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1532InBlock"], T1532InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1532"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1532OutBlock(BaseModel):
    """
    t1532OutBlock - 종목별테마 응답 블록 (배열)
    """
    tmname: str = ""
    """ 테마명 """
    avgdiff: float = 0.0
    """ 평균등락율 """
    tmcode: str = ""
    """ 테마코드 """


class T1532Response(BaseModel):
    """
    T1532 API 전체 응답 - 종목별테마
    """
    header: Optional[T1532ResponseHeader] = None
    block: List[T1532OutBlock] = Field(
        default_factory=list, title="테마 리스트",
        description="종목에 해당하는 테마 리스트"
    )
    status_code: Optional[int] = Field(None, title="HTTP 상태 코드")
    rsp_cd: str = ""
    rsp_msg: str = ""
    error_msg: Optional[str] = Field(None, title="오류메시지")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
