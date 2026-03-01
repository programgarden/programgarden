from typing import Dict, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class T1601RequestHeader(BlockRequestHeader):
    """t1601 요청용 Header"""
    pass


class T1601ResponseHeader(BlockResponseHeader):
    """t1601 응답용 Header"""
    pass


class T1601InBlock(BaseModel):
    """
    t1601InBlock - 투자자별종합 입력 블록

    Attributes:
        gubun1 (str): 주식금액수량구분1 (1:수량 2:금액)
        gubun2 (str): 옵션금액수량구분2 (1:수량 2:금액)
        gubun3 (str): 금액단위 (사용안함)
        gubun4 (str): 선물금액수량구분4 (1:수량 2:금액)
        exchgubun (str): 거래소구분코드 (K:KRX N:NXT U:통합)
    """
    gubun1: Literal["1", "2"]
    """ 주식금액수량구분1 (1:수량 2:금액) """
    gubun2: Literal["1", "2"]
    """ 옵션금액수량구분2 (1:수량 2:금액) """
    gubun3: str = ""
    """ 금액단위 (사용안함) """
    gubun4: Literal["1", "2"]
    """ 선물금액수량구분4 (1:수량 2:금액) """
    exchgubun: Literal["K", "N", "U"] = "K"
    """ 거래소구분코드 (K:KRX N:NXT U:통합) """


class T1601Request(BaseModel):
    """
    T1601 API 요청 - 투자자별종합

    Attributes:
        header (T1601RequestHeader)
        body (Dict[Literal["t1601InBlock"], T1601InBlock])
    """
    header: T1601RequestHeader = T1601RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="t1601",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: Dict[Literal["t1601InBlock"], T1601InBlock]
    options: SetupOptions = SetupOptions(
        rate_limit_count=2,
        rate_limit_seconds=1,
        on_rate_limit="wait",
        rate_limit_key="t1601"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class T1601InvestorBlock(BaseModel):
    """
    t1601 투자자별 데이터 블록 (OutBlock1~6 공통 구조)

    12개 투자자 유형별 매수/매도/증감/순매수 데이터를 포함합니다.
    """
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
    jjcode_11: str = ""
    """ 국가투자코드 """
    ms_11: int = 0
    """ 국가매수 """
    md_11: int = 0
    """ 국가매도 """
    rate_11: int = 0
    """ 국가증감 """
    svolume_11: int = 0
    """ 국가순매수 """
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
    jjcode_00: str = ""
    """ 사모펀드투자자코드 """
    ms_00: int = 0
    """ 사모펀드매수 """
    md_00: int = 0
    """ 사모펀드매도 """
    rate_00: int = 0
    """ 사모펀드증감 """
    svolume_00: int = 0
    """ 사모펀드순매수 """


class T1601Response(BaseModel):
    """
    T1601 API 전체 응답 - 투자자별종합

    OutBlock1: 코스피(주식)
    OutBlock2: 코스닥(주식)
    OutBlock3: 선물
    OutBlock4: 콜옵션
    OutBlock5: 풋옵션
    OutBlock6: ELW
    """
    header: Optional[T1601ResponseHeader] = None
    block1: Optional[T1601InvestorBlock] = Field(
        None, title="코스피(주식)",
        description="코스피 투자자별 매매 데이터"
    )
    block2: Optional[T1601InvestorBlock] = Field(
        None, title="코스닥(주식)",
        description="코스닥 투자자별 매매 데이터"
    )
    block3: Optional[T1601InvestorBlock] = Field(
        None, title="선물",
        description="선물 투자자별 매매 데이터"
    )
    block4: Optional[T1601InvestorBlock] = Field(
        None, title="콜옵션",
        description="콜옵션 투자자별 매매 데이터"
    )
    block5: Optional[T1601InvestorBlock] = Field(
        None, title="풋옵션",
        description="풋옵션 투자자별 매매 데이터"
    )
    block6: Optional[T1601InvestorBlock] = Field(
        None, title="ELW",
        description="ELW 투자자별 매매 데이터"
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
