from typing import Dict, Literal, Optional, List

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1444RequestHeader(BlockRequestHeader):
    """t1444 요청용 Header"""
    pass


class T1444ResponseHeader(BlockResponseHeader):
    """t1444 응답용 Header"""
    pass


class T1444InBlock(BaseModel):
    """
    t1444InBlock - 시가총액상위 입력 블록

    업종코드별 시가총액 상위 종목을 조회합니다.
    연속조회 시 이전 응답의 OutBlock.idx 값을 idx에 설정합니다.

    Attributes:
        upcode (str): 업종코드 3자리 (예: "001"=코스피, "301"=코스닥)
        idx (int): 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx)
    """
    upcode: str
    """ 업종코드 3자리 (예: "001"=코스피, "301"=코스닥) """
    idx: int = 0
    """ 연속조회키 (최초 0, 연속조회 시 이전 OutBlock.idx) """


class T1444Request(BaseModel):
    """
    T1444 API 요청 - 시가총액상위

    Attributes:
        header (T1444RequestHeader)
        body (Dict[Literal["t1444InBlock"], T1444InBlock])
    """
    header: T1444RequestHeader = T1444RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1444",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1444InBlock"], T1444InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1444"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1444OutBlock(BaseModel):
    """
    t1444OutBlock - 시가총액상위 연속조회 블록

    연속조회에 사용되는 idx를 반환합니다.
    다음 페이지 조회 시 이 값을 InBlock.idx에 설정합니다.

    Attributes:
        idx (int): 연속조회키
    """
    idx: int
    """ 연속조회키 (다음 페이지 조회 시 InBlock.idx에 설정) """


class T1444OutBlock1(BaseModel):
    """
    t1444OutBlock1 - 시가총액상위 종목 정보

    업종 내 시가총액 순위별 종목의 현재가, 등락률, 거래량,
    시가총액, 업종 내 비중, 외국인 보유비중을 제공합니다.

    Attributes:
        shcode (str): 종목코드 6자리
        hname (str): 종목명
        price (int): 현재가
        sign (str): 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락)
        change (int): 전일대비
        diff (float): 등락율(%)
        volume (int): 거래량
        vol_rate (float): 거래비중(%) - 전체 거래량 대비 해당 종목 비중
        total (int): 시가총액(억원)
        rate (float): 비중(%) - 업종 내 시가총액 비중
        for_rate (float): 외인비중(%) - 외국인 보유비중
    """
    shcode: str
    """ 종목코드 6자리 """
    hname: str
    """ 종목명 """
    price: int
    """ 현재가 """
    sign: str
    """ 전일대비구분 (1:상한 2:상승 3:보합 4:하한 5:하락) """
    change: int
    """ 전일대비 """
    diff: float
    """ 등락율(%) """
    volume: int
    """ 거래량 """
    vol_rate: float
    """ 거래비중(%) - 전체 거래량 대비 해당 종목 비중 """
    total: int
    """ 시가총액(억원) """
    rate: float
    """ 비중(%) - 업종 내 시가총액 비중 """
    for_rate: float
    """ 외인비중(%) - 외국인 보유비중 """


class T1444Response(BaseModel):
    """
    T1444 API 전체 응답 - 시가총액상위

    업종별 시가총액 상위 종목 리스트를 반환합니다.
    연속조회가 필요하면 cont_block.idx를 다음 요청의 InBlock.idx에 설정합니다.

    Attributes:
        header (Optional[T1444ResponseHeader])
        cont_block (Optional[T1444OutBlock]): 연속조회 블록 (idx 포함)
        block (List[T1444OutBlock1]): 시가총액상위 종목 리스트
        rsp_cd (str): 응답코드 ("00000" = 정상)
        rsp_msg (str): 응답메시지
        error_msg (Optional[str]): 에러 시 메시지
    """
    header: Optional[T1444ResponseHeader]
    cont_block: Optional[T1444OutBlock] = Field(
        None,
        title="연속조회 블록",
        description="연속조회키(idx)를 포함하는 블록"
    )
    block: List[T1444OutBlock1] = Field(
        default_factory=list,
        title="시가총액상위 종목 리스트",
        description="업종별 시가총액 상위 종목 리스트"
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
