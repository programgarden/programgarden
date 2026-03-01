from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T9945RequestHeader(BlockRequestHeader):
    """t9945 요청용 Header"""
    pass


class T9945ResponseHeader(BlockResponseHeader):
    """t9945 응답용 Header"""
    pass


class T9945InBlock(BaseModel):
    """
    t9945InBlock 입력 블록

    Attributes:
        gubun (Literal["1", "2"]): 구분 (1: KOSPI, 2: KOSDAQ)
    """
    gubun: Literal["1", "2"]
    """ 구분 (KSP:1, KSD:2) """


class T9945Request(BaseModel):
    """
    T9945 API 요청

    Attributes:
        header (T9945RequestHeader)
        body (Dict[Literal["t9945InBlock"], T9945InBlock])
    """
    header: T9945RequestHeader = T9945RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t9945",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t9945InBlock"], T9945InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t9945"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T9945OutBlock(BaseModel):
    """
    t9945OutBlock 응답 블록 (개별 종목 정보)

    Attributes:
        hname (str): 종목명
        shcode (str): 단축코드
        expcode (str): 확장코드
        etfchk (str): ETF구분
        nxt_chk (str): NXT상장구분 (1: NXT 거래소 제공, 0: NXT 거래소 미제공)
        filler (str): filler
    """
    hname: str
    """ 종목명 """
    shcode: str
    """ 단축코드 """
    expcode: str
    """ 확장코드 """
    etfchk: str
    """ ETF구분 """
    nxt_chk: str = ""
    """ NXT상장구분 (1: NXT 거래소 제공, 0: NXT 거래소 미제공) """
    filler: str = ""
    """ filler """


class T9945Response(BaseModel):
    """
    T9945 API 전체 응답

    Attributes:
        header (Optional[T9945ResponseHeader])
        block (List[T9945OutBlock]): 종목 리스트
        rsp_cd (str)
        rsp_msg (str)
        error_msg (Optional[str])
    """
    header: Optional[T9945ResponseHeader]
    block: List[T9945OutBlock] = Field(
        default_factory=list,
        title="종목 리스트",
        description="주식마스터 종목 리스트"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="요청에 대한 HTTP 상태 코드"
    )
    rsp_cd: str
    rsp_msg: str
    error_msg: Optional[str] = Field(
        None,
        title="오류메시지",
        description="오류메시지 (있으면)"
    )

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
