from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1531RequestHeader(BlockRequestHeader):
    """t1531 요청용 Header"""
    pass


class T1531ResponseHeader(BlockResponseHeader):
    """t1531 응답용 Header"""
    pass


class T1531InBlock(BaseModel):
    """
    t1531InBlock - 테마별종목 입력 블록

    Attributes:
        tmname (str): 테마명 (t8425 조회하여 확인 후 입력)
        tmcode (str): 테마코드 (t8425 조회하여 확인 후 입력)
    """
    tmname: str = ""
    """ 테마명 (t8425 조회하여 확인 후 입력) """
    tmcode: str = ""
    """ 테마코드 (t8425 조회하여 확인 후 입력) """


class T1531Request(BaseModel):
    """
    T1531 API 요청 - 테마별종목

    Attributes:
        header (T1531RequestHeader)
        body (Dict[Literal["t1531InBlock"], T1531InBlock])
    """
    header: T1531RequestHeader = T1531RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1531",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1531InBlock"], T1531InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1531"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1531OutBlock(BaseModel):
    """
    t1531OutBlock - 테마별종목 응답 블록 (배열)
    """
    tmname: str = ""
    """ 테마명 """
    avgdiff: float = 0.0
    """ 평균등락율 """
    tmcode: str = ""
    """ 테마코드 """


class T1531Response(BaseModel):
    """
    T1531 API 전체 응답 - 테마별종목
    """
    header: Optional[T1531ResponseHeader] = None
    block: List[T1531OutBlock] = Field(
        default_factory=list, title="테마 리스트",
        description="테마별종목 리스트"
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
