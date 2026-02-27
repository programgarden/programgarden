from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1617RequestHeader(BlockRequestHeader):
    """t1617 요청용 Header"""
    pass


class T1617ResponseHeader(BlockResponseHeader):
    """t1617 응답용 Header"""
    pass


class T1617InBlock(BaseModel):
    """
    t1617InBlock - 투자자매매종합2 입력 블록

    Attributes:
        gubun1 (str): 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션 6:주식선물 7:변동성 8:M선물 9:M콜옵션 0:M풋옵션)
        gubun2 (str): 수량금액구분 (1:수량 2:금액)
        gubun3 (str): 일자구분 (1:시간대별 2:일별)
        cts_date (str): 연속키 일자 (처음 조회시 Space)
        cts_time (str): 연속키 시간 (처음 조회시 Space)
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    gubun1: Literal["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    """ 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션 6:주식선물 7:변동성 8:M선물 9:M콜옵션 0:M풋옵션) """
    gubun2: Literal["1", "2"]
    """ 수량금액구분 (1:수량 2:금액) """
    gubun3: Literal["1", "2"]
    """ 일자구분 (1:시간대별 2:일별) """
    cts_date: str = ""
    """ 연속키 일자 (처음 조회시 Space) """
    cts_time: str = ""
    """ 연속키 시간 (처음 조회시 Space) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1617Request(BaseModel):
    """
    T1617 API 요청 - 투자자매매종합2
    """
    header: T1617RequestHeader = T1617RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1617",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1617InBlock"], T1617InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1617"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1617OutBlock(BaseModel):
    """
    t1617OutBlock - 투자자매매종합2 합계/연속 블록
    """
    cts_date: str = ""
    """ 연속키 일자 """
    cts_time: str = ""
    """ 연속키 시간 """
    ms_08: int = 0
    """ 개인매수 """
    md_08: int = 0
    """ 개인매도 """
    sv_08: int = 0
    """ 개인순매수 """
    ms_17: int = 0
    """ 외국인매수 """
    md_17: int = 0
    """ 외국인매도 """
    sv_17: int = 0
    """ 외국인순매수 """
    ms_18: int = 0
    """ 기관계매수 """
    md_18: int = 0
    """ 기관계매도 """
    sv_18: int = 0
    """ 기관계순매수 """
    ms_01: int = 0
    """ 증권매수 """
    md_01: int = 0
    """ 증권매도 """
    sv_01: int = 0
    """ 증권순매수 """


class T1617OutBlock1(BaseModel):
    """
    t1617OutBlock1 - 투자자매매종합2 시간/일별 리스트
    """
    date: str = ""
    """ 날짜 """
    time: str = ""
    """ 시간 """
    sv_08: int = 0
    """ 개인 """
    sv_17: int = 0
    """ 외국인 """
    sv_18: int = 0
    """ 기관계 """
    sv_01: int = 0
    """ 증권 """


class T1617Response(BaseModel):
    """
    T1617 API 전체 응답 - 투자자매매종합2
    """
    header: Optional[T1617ResponseHeader] = None
    cont_block: Optional[T1617OutBlock] = Field(
        None, title="합계/연속 데이터",
        description="투자자별 합계 및 연속조회 키 (cts_date, cts_time)"
    )
    block: List[T1617OutBlock1] = Field(
        default_factory=list, title="시간/일별 리스트",
        description="시간대별 또는 일별 투자자 순매수 리스트"
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
