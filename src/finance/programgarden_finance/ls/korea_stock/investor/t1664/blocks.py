from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1664RequestHeader(BlockRequestHeader):
    """t1664 요청용 Header"""
    pass


class T1664ResponseHeader(BlockResponseHeader):
    """t1664 응답용 Header"""
    pass


class T1664InBlock(BaseModel):
    """
    t1664InBlock - 투자자매매종합(차트) 입력 블록

    Attributes:
        mgubun (str): 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션)
        vagubun (str): 금액수량구분 (1:수량 2:금액)
        bdgubun (str): 시간일별구분 (1:시간별 2:일별)
        cnt (int): 조회건수
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    mgubun: Literal["1", "2", "3", "4", "5"]
    """ 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션) """
    vagubun: Literal["1", "2"]
    """ 금액수량구분 (1:수량 2:금액) """
    bdgubun: Literal["1", "2"]
    """ 시간일별구분 (1:시간별 2:일별) """
    cnt: int = 20
    """ 조회건수 """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1664Request(BaseModel):
    """
    T1664 API 요청 - 투자자매매종합(차트)
    """
    header: T1664RequestHeader = T1664RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1664",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1664InBlock"], T1664InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1664"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1664OutBlock1(BaseModel):
    """
    t1664OutBlock1 - 투자자매매종합(차트) 데이터 리스트
    """
    dt: str = ""
    """ 일자시간 """
    tjj01: int = 0
    """ 증권순매수 """
    tjj02: int = 0
    """ 보험순매수 """
    tjj03: int = 0
    """ 투신순매수 """
    tjj04: int = 0
    """ 은행순매수 """
    tjj05: int = 0
    """ 종금순매수 """
    tjj06: int = 0
    """ 기금순매수 """
    tjj07: int = 0
    """ 기타순매수 """
    tjj08: int = 0
    """ 개인순매수 """
    tjj17: int = 0
    """ 외국인순매수 """
    tjj18: int = 0
    """ 기관순매수 """
    cha: int = 0
    """ 차익순매수 """
    bicha: int = 0
    """ 비차익순매수 """
    totcha: int = 0
    """ 종합순매수 """
    basis: float = 0.0
    """ 베이시스 """


class T1664Response(BaseModel):
    """
    T1664 API 전체 응답 - 투자자매매종합(차트)

    OutBlock 없이 OutBlock1만 존재하는 TR입니다.
    """
    header: Optional[T1664ResponseHeader] = None
    block: List[T1664OutBlock1] = Field(
        default_factory=list, title="차트 데이터",
        description="투자자매매종합 차트용 데이터 리스트"
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
