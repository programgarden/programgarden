from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1603RequestHeader(BlockRequestHeader):
    """t1603 요청용 Header"""
    pass


class T1603ResponseHeader(BlockResponseHeader):
    """t1603 응답용 Header"""
    pass


class T1603InBlock(BaseModel):
    """
    t1603InBlock - 시간대별투자자매매추이상세 입력 블록

    Attributes:
        market (str): 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션 6:ELW 7:ETF)
        gubun1 (str): 투자자구분 (1:개인 2:외인 3:기관계 4:증권 5:투신 6:은행 7:보험 8:종금 9:기금 A:국가 B:기타 C:사모펀드)
        gubun2 (str): 전일분구분 (0:당일 1:전일)
        cts_time (str): 연속키 시간 (처음 조회시 Space)
        cts_idx (int): 연속키 인덱스 (처음 조회시 0)
        cnt (int): 조회건수
        upcode (str): 업종코드
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    market: Literal["1", "2", "3", "4", "5", "6", "7"]
    """ 시장구분 (1:코스피 2:코스닥 3:선물 4:콜옵션 5:풋옵션 6:ELW 7:ETF) """
    gubun1: Literal["1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C"]
    """ 투자자구분 (1:개인 2:외인 3:기관계 4:증권 5:투신 6:은행 7:보험 8:종금 9:기금 A:국가 B:기타 C:사모펀드) """
    gubun2: Literal["0", "1"]
    """ 전일분구분 (0:당일 1:전일) """
    cts_time: str = ""
    """ 연속키 시간 (처음 조회시 Space) """
    cts_idx: int = 0
    """ 연속키 인덱스 (처음 조회시 0) """
    cnt: int = 20
    """ 조회건수 """
    upcode: str = ""
    """ 업종코드 """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1603Request(BaseModel):
    """
    T1603 API 요청 - 시간대별투자자매매추이상세
    """
    header: T1603RequestHeader = T1603RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1603",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1603InBlock"], T1603InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1603"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1603OutBlock(BaseModel):
    """
    t1603OutBlock - 시간대별투자자매매추이상세 연속 블록
    """
    cts_idx: int = 0
    """ 연속키 인덱스 """
    cts_time: str = ""
    """ 연속키 시간 """
    ex_upcode: str = ""
    """ 거래소별업종코드 """


class T1603OutBlock1(BaseModel):
    """
    t1603OutBlock1 - 시간대별 투자자 매매 상세 리스트
    """
    time: str = ""
    """ 시간 """
    tjjcode: str = ""
    """ 투자자구분 """
    msvolume: int = 0
    """ 매수수량 """
    mdvolume: int = 0
    """ 매도수량 """
    msvalue: int = 0
    """ 매수금액 """
    mdvalue: int = 0
    """ 매도금액 """
    svolume: int = 0
    """ 순매수수량 """
    svalue: int = 0
    """ 순매수금액 """


class T1603Response(BaseModel):
    """
    T1603 API 전체 응답 - 시간대별투자자매매추이상세
    """
    header: Optional[T1603ResponseHeader] = None
    cont_block: Optional[T1603OutBlock] = Field(
        None, title="연속 데이터",
        description="연속조회 키 (cts_time, cts_idx)"
    )
    block: List[T1603OutBlock1] = Field(
        default_factory=list, title="시간대별 상세 리스트",
        description="시간대별 투자자 매매 상세 리스트"
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
