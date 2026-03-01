from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1602RequestHeader(BlockRequestHeader):
    """t1602 요청용 Header"""
    pass


class T1602ResponseHeader(BlockResponseHeader):
    """t1602 응답용 Header"""
    pass


class T1602InBlock(BaseModel):
    """
    t1602InBlock - 시간대별투자자매매추이 입력 블록

    Attributes:
        market (str): 시장구분 (1:코스피 2:KP200 3:코스닥 4:선물 5:콜옵션 6:풋옵션 7:ELW 8:ETF)
        upcode (str): 업종코드
        gubun1 (str): 수량구분 (1:수량 2:금액)
        gubun2 (str): 전일분구분 (0:금일 1:전일)
        cts_time (str): 연속키 시간 (처음 조회시 Space)
        cts_idx (int): 연속키 인덱스 (사용안함)
        cnt (int): 조회건수
        gubun3 (str): 직전대비구분 (C:직전대비)
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    market: Literal["1", "2", "3", "4", "5", "6", "7", "8"]
    """ 시장구분 (1:코스피 2:KP200 3:코스닥 4:선물 5:콜옵션 6:풋옵션 7:ELW 8:ETF) """
    upcode: str
    """ 업종코드 """
    gubun1: Literal["1", "2"]
    """ 수량구분 (1:수량 2:금액) """
    gubun2: Literal["0", "1"]
    """ 전일분구분 (0:금일 1:전일) """
    cts_time: str = ""
    """ 연속키 시간 (처음 조회시 Space) """
    cts_idx: int = 0
    """ 연속키 인덱스 (사용안함) """
    cnt: int = 20
    """ 조회건수 """
    gubun3: str = ""
    """ 직전대비구분 (C:직전대비) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1602Request(BaseModel):
    """
    T1602 API 요청 - 시간대별투자자매매추이
    """
    header: T1602RequestHeader = T1602RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1602",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1602InBlock"], T1602InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=1,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1602"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1602OutBlock(BaseModel):
    """
    t1602OutBlock - 시간대별투자자매매추이 연속/합계 블록
    """
    cts_time: str = ""
    """ 연속키 시간 """
    tjjcode_08: str = ""
    """ 개인투자자코드 """
    ms_08: int = 0
    """ 개인매수 """
    md_08: int = 0
    """ 개인매도 """
    rate_08: int = 0
    """ 개인증감 """
    svolume_08: int = 0
    """ 개인순매수 """
    jjcode_17: str = ""
    """ 외국인투자자코드 """
    ms_17: int = 0
    """ 외국인매수 """
    md_17: int = 0
    """ 외국인매도 """
    rate_17: int = 0
    """ 외국인증감 """
    svolume_17: int = 0
    """ 외국인순매수 """
    jjcode_18: str = ""
    """ 기관계투자자코드 """
    ms_18: int = 0
    """ 기관계매수 """
    md_18: int = 0
    """ 기관계매도 """
    rate_18: int = 0
    """ 기관계증감 """
    svolume_18: int = 0
    """ 기관계순매수 """
    jjcode_01: str = ""
    """ 증권투자자코드 """
    ms_01: int = 0
    """ 증권매수 """
    md_01: int = 0
    """ 증권매도 """
    rate_01: int = 0
    """ 증권증감 """
    svolume_01: int = 0
    """ 증권순매수 """
    jjcode_03: str = ""
    """ 투신투자자코드 """
    ms_03: int = 0
    """ 투신매수 """
    md_03: int = 0
    """ 투신매도 """
    rate_03: int = 0
    """ 투신증감 """
    svolume_03: int = 0
    """ 투신순매수 """
    jjcode_04: str = ""
    """ 은행투자자코드 """
    ms_04: int = 0
    """ 은행매수 """
    md_04: int = 0
    """ 은행매도 """
    rate_04: int = 0
    """ 은행증감 """
    svolume_04: int = 0
    """ 은행순매수 """
    jjcode_02: str = ""
    """ 보험투자자코드 """
    ms_02: int = 0
    """ 보험매수 """
    md_02: int = 0
    """ 보험매도 """
    rate_02: int = 0
    """ 보험증감 """
    svolume_02: int = 0
    """ 보험순매수 """
    jjcode_05: str = ""
    """ 종금투자자코드 """
    ms_05: int = 0
    """ 종금매수 """
    md_05: int = 0
    """ 종금매도 """
    rate_05: int = 0
    """ 종금증감 """
    svolume_05: int = 0
    """ 종금순매수 """
    jjcode_06: str = ""
    """ 기금투자자코드 """
    ms_06: int = 0
    """ 기금매수 """
    md_06: int = 0
    """ 기금매도 """
    rate_06: int = 0
    """ 기금증감 """
    svolume_06: int = 0
    """ 기금순매수 """
    jjcode_07: str = ""
    """ 기타투자자코드 """
    ms_07: int = 0
    """ 기타매수 """
    md_07: int = 0
    """ 기타매도 """
    rate_07: int = 0
    """ 기타증감 """
    svolume_07: int = 0
    """ 기타순매수 """
    jjcode_11: str = ""
    """ 국가투자자코드 """
    ms_11: int = 0
    """ 국가매수 """
    md_11: int = 0
    """ 국가매도 """
    rate_11: int = 0
    """ 국가증감 """
    svolume_11: int = 0
    """ 국가순매수 """
    jjcode_00: str = ""
    """ 사모펀드코드 """
    ms_00: int = 0
    """ 사모펀드매수 """
    md_00: int = 0
    """ 사모펀드매도 """
    rate_00: int = 0
    """ 사모펀드증감 """
    svolume_00: int = 0
    """ 사모펀드순매수 """
    ex_upcode: str = ""
    """ 거래소별업종코드 """


class T1602OutBlock1(BaseModel):
    """
    t1602OutBlock1 - 시간대별 투자자 순매수 리스트
    """
    time: str = ""
    """ 시간 """
    sv_08: int = 0
    """ 개인순매수 """
    sv_17: int = 0
    """ 외국인순매수 """
    sv_18: int = 0
    """ 기관계순매수 """
    sv_01: int = 0
    """ 증권순매수 """
    sv_03: int = 0
    """ 투신순매수 """
    sv_04: int = 0
    """ 은행순매수 """
    sv_02: int = 0
    """ 보험순매수 """
    sv_05: int = 0
    """ 종금순매수 """
    sv_06: int = 0
    """ 기금순매수 """
    sv_07: int = 0
    """ 기타순매수 """
    sv_11: int = 0
    """ 국가순매수 """
    sv_00: int = 0
    """ 사모펀드순매수 """


class T1602Response(BaseModel):
    """
    T1602 API 전체 응답 - 시간대별투자자매매추이
    """
    header: Optional[T1602ResponseHeader] = None
    cont_block: Optional[T1602OutBlock] = Field(
        None, title="합계/연속 데이터",
        description="투자자별 합계 및 연속조회 키"
    )
    block: List[T1602OutBlock1] = Field(
        default_factory=list, title="시간대별 리스트",
        description="시간대별 투자자 순매수 리스트"
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
