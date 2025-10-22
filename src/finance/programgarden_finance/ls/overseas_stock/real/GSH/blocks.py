from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class GSHRealRequestHeader(BlockRealRequestHeader):
    pass


class GSHRealResponseHeader(BlockRealResponseHeader):
    pass


class GSHRealRequestBody(BaseModel):
    tr_cd: str = Field("GSH", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=18, description="단축코드 + padding(공백12자리)")

    @field_validator("tr_key", mode="before")
    def ensure_trailing_12_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 18:
            return s.ljust(18)
        return s

    model_config = ConfigDict(validate_assignment=True)


class GSHRealRequest(BaseModel):
    """
    해외주식 호가 실시간 요청
    """
    header: GSHRealRequestHeader = Field(
        GSHRealRequestHeader(
            token="",
            tr_type="3"
        ),
        title="요청 헤더 데이터 블록",
        description="GSH API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: GSHRealRequestBody = Field(
        GSHRealRequestBody(
            tr_cd="GSH",
            tr_key=""
        ),
        title="입력 데이터 블록",
        description="해외주식 호가 입력 데이터 블록",
    )


class GSHRealResponseBody(BaseModel):
    """
    GSH 실시간 응답 바디 모델

    필드 설명은 LS증권 WSS GSH 응답 규격에 따릅니다.
    """
    symbol: str = Field(..., title="종목코드", description="종목코드 (예: SOXL)")
    """종목코드"""
    loctime: str = Field(..., title="현지호가시간", description="현지 호가 시간 (HHMMSS)")
    """현지 호가 시간 (HHMMSS)"""
    kortime: str = Field(..., title="한국호가시간", description="한국 호가 시간 (HHMMSS)")
    """한국 호가 시간 (HHMMSS)"""

    # Offer/Bid price and quantities for levels 1..10
    offerho1: float = Field(..., title="매도호가1", description="매도호가1 (소수점 포함, 예: 12.2400)")
    """매도호가1"""
    bidho1: float = Field(..., title="매수호가1", description="매수호가1 (소수점 포함, 예: 12.2000)")
    """매수호가1"""
    offerrem1: int = Field(..., title="매도호가잔량1", description="매도호가 잔량")
    """매도호가 잔량1"""
    bidrem1: int = Field(..., title="매수호가잔량1", description="매수호가 잔량")
    """매수호가 잔량1"""
    offerno1: int = Field(..., title="매도호가건수1", description="매도호가 건수")
    """매도호가 건수1"""
    bidno1: int = Field(..., title="매수호가건수1", description="매수호가 건수")
    """매수호가 건수1"""

    offerho2: float = Field(..., title="매도호가2", description="매도호가2 (소수점 포함)")
    bidho2: float = Field(..., title="매수호가2", description="매수호가2 (소수점 포함)")
    offerrem2: int = Field(..., title="매도호가잔량2", description="매도호가 잔량2")
    bidrem2: int = Field(..., title="매수호가잔량2", description="매수호가 잔량2")
    offerno2: int = Field(..., title="매도호가건수2", description="매도호가 건수2")
    bidno2: int = Field(..., title="매수호가건수2", description="매수호가 건수2")

    offerho3: float = Field(..., title="매도호가3", description="매도호가3 (소수점 포함)")
    bidho3: float = Field(..., title="매수호가3", description="매수호가3 (소수점 포함)")
    offerrem3: int = Field(..., title="매도호가잔량3", description="매도호가 잔량3")
    bidrem3: int = Field(..., title="매수호가잔량3", description="매수호가 잔량3")
    offerno3: int = Field(..., title="매도호가건수3", description="매도호가 건수3")
    bidno3: int = Field(..., title="매수호가건수3", description="매수호가 건수3")

    offerho4: float = Field(..., title="매도호가4", description="매도호가4 (소수점 포함)")
    bidho4: float = Field(..., title="매수호가4", description="매수호가4 (소수점 포함)")
    offerrem4: int = Field(..., title="매도호가잔량4", description="매도호가 잔량4")
    bidrem4: int = Field(..., title="매수호가잔량4", description="매수호가 잔량4")
    offerno4: int = Field(..., title="매도호가건수4", description="매도호가 건수4")
    bidno4: int = Field(..., title="매수호가건수4", description="매수호가 건수4")

    offerho5: float = Field(..., title="매도호가5", description="매도호가5 (소수점 포함)")
    bidho5: float = Field(..., title="매수호가5", description="매수호가5 (소수점 포함)")
    offerrem5: int = Field(..., title="매도호가잔량5", description="매도호가 잔량5")
    bidrem5: int = Field(..., title="매수호가잔량5", description="매수호가 잔량5")
    offerno5: int = Field(..., title="매도호가건수5", description="매도호가 건수5")
    bidno5: int = Field(..., title="매수호가건수5", description="매수호가 건수5")

    offerho6: float = Field(..., title="매도호가6", description="매도호가6 (소수점 포함)")
    bidho6: float = Field(..., title="매수호가6", description="매수호가6 (소수점 포함)")
    offerrem6: int = Field(..., title="매도호가잔량6", description="매도호가 잔량6")
    bidrem6: int = Field(..., title="매수호가잔량6", description="매수호가 잔량6")
    offerno6: int = Field(..., title="매도호가건수6", description="매도호가 건수6")
    bidno6: int = Field(..., title="매수호가건수6", description="매수호가 건수6")

    offerho7: float = Field(..., title="매도호가7", description="매도호가7 (소수점 포함)")
    bidho7: float = Field(..., title="매수호가7", description="매수호가7 (소수점 포함)")
    offerrem7: int = Field(..., title="매도호가잔량7", description="매도호가 잔량7")
    bidrem7: int = Field(..., title="매수호가잔량7", description="매수호가 잔량7")
    offerno7: int = Field(..., title="매도호가건수7", description="매도호가 건수7")
    bidno7: int = Field(..., title="매수호가건수7", description="매수호가 건수7")

    offerho8: float = Field(..., title="매도호가8", description="매도호가8 (소수점 포함)")
    bidho8: float = Field(..., title="매수호가8", description="매수호가8 (소수점 포함)")
    offerrem8: int = Field(..., title="매도호가잔량8", description="매도호가 잔량8")
    bidrem8: int = Field(..., title="매수호가잔량8", description="매수호가 잔량8")
    offerno8: int = Field(..., title="매도호가건수8", description="매도호가 건수8")
    bidno8: int = Field(..., title="매수호가건수8", description="매수호가 건수8")

    offerho9: float = Field(..., title="매도호가9", description="매도호가9 (소수점 포함)")
    bidho9: float = Field(..., title="매수호가9", description="매수호가9 (소수점 포함)")
    offerrem9: int = Field(..., title="매도호가잔량9", description="매도호가 잔량9")
    bidrem9: int = Field(..., title="매수호가잔량9", description="매수호가 잔량9")
    offerno9: int = Field(..., title="매도호가건수9", description="매도호가 건수9")
    bidno9: int = Field(..., title="매수호가건수9", description="매수호가 건수9")

    offerho10: float = Field(..., title="매도호가10", description="매도호가10 (소수점 포함)")
    bidho10: float = Field(..., title="매수호가10", description="매수호가10 (소수점 포함)")
    offerrem10: int = Field(..., title="매도호가잔량10", description="매도호가 잔량10")
    bidrem10: int = Field(..., title="매수호가잔량10", description="매수호가 잔량10")
    offerno10: int = Field(..., title="매도호가건수10", description="매도호가 건수10")
    bidno10: int = Field(..., title="매수호가건수10", description="매수호가 건수10")

    totoffercnt: int = Field(..., title="매도호가총건수", description="매도호가의 총 건수")
    totbidcnt: int = Field(..., title="매수호가총건수", description="매수호가의 총 건수")
    totofferrem: int = Field(..., title="매도호가총수량", description="매도호가의 총 수량")
    totbidrem: int = Field(..., title="매수호가총수량", description="매수호가의 총 수량")


class GSHRealResponse(BaseModel):
    header: Optional[GSHRealResponseHeader]
    body: Optional[GSHRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    """응답 코드"""
    rsp_msg: str = Field(..., title="응답 메시지")
    """응답 메시지"""
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    """오류 메시지 (있으면)"""
    _raw_data: Optional[Response] = PrivateAttr(default=None)
    """private으로 BaseModel의 직렬화에 포함시키지 않는다"""

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
