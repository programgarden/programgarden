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

    ⚠️ LS증권 API 제약 (해외주식 한정):
    - 호가 가격(offerho/bidho 1~10): 정상 제공
    - 잔량(offerrem/bidrem 2~10): 항상 0 (개별 호가단계 잔량 미제공)
    - 잔량(offerrem1/bidrem1): totofferrem/totbidrem과 동일 (총잔량이 1단계에 합산)
    - 건수(offerno/bidno 1~10): 항상 0 (호가 건수 미제공)
    - 해외선물(OVH/WOH), 국내주식(H1_/HA_)은 개별 단계별 데이터 정상 제공됨

    개별 잔량이 필요하면 REST API(g3106)를 사용하세요.
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
    offerrem1: int = Field(..., title="매도호가잔량1", description="매도호가 잔량 (⚠️ 실제로는 totofferrem과 동일한 총잔량)")
    """매도호가 잔량1 — 실제로는 총잔량(totofferrem)이 합산되어 나옴"""
    bidrem1: int = Field(..., title="매수호가잔량1", description="매수호가 잔량 (⚠️ 실제로는 totbidrem과 동일한 총잔량)")
    """매수호가 잔량1 — 실제로는 총잔량(totbidrem)이 합산되어 나옴"""
    offerno1: int = Field(..., title="매도호가건수1", description="매도호가 건수 (⚠️ API 미제공: 항상 0)")
    """매도호가 건수1 — API 미제공: 항상 0"""
    bidno1: int = Field(..., title="매수호가건수1", description="매수호가 건수 (⚠️ API 미제공: 항상 0)")
    """매수호가 건수1 — API 미제공: 항상 0"""

    offerho2: float = Field(..., title="매도호가2", description="매도호가2 (소수점 포함)")
    bidho2: float = Field(..., title="매수호가2", description="매수호가2 (소수점 포함)")
    offerrem2: int = Field(..., title="매도호가잔량2", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem2: int = Field(..., title="매수호가잔량2", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno2: int = Field(..., title="매도호가건수2", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno2: int = Field(..., title="매수호가건수2", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho3: float = Field(..., title="매도호가3", description="매도호가3 (소수점 포함)")
    bidho3: float = Field(..., title="매수호가3", description="매수호가3 (소수점 포함)")
    offerrem3: int = Field(..., title="매도호가잔량3", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem3: int = Field(..., title="매수호가잔량3", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno3: int = Field(..., title="매도호가건수3", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno3: int = Field(..., title="매수호가건수3", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho4: float = Field(..., title="매도호가4", description="매도호가4 (소수점 포함)")
    bidho4: float = Field(..., title="매수호가4", description="매수호가4 (소수점 포함)")
    offerrem4: int = Field(..., title="매도호가잔량4", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem4: int = Field(..., title="매수호가잔량4", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno4: int = Field(..., title="매도호가건수4", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno4: int = Field(..., title="매수호가건수4", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho5: float = Field(..., title="매도호가5", description="매도호가5 (소수점 포함)")
    bidho5: float = Field(..., title="매수호가5", description="매수호가5 (소수점 포함)")
    offerrem5: int = Field(..., title="매도호가잔량5", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem5: int = Field(..., title="매수호가잔량5", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno5: int = Field(..., title="매도호가건수5", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno5: int = Field(..., title="매수호가건수5", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho6: float = Field(..., title="매도호가6", description="매도호가6 (소수점 포함)")
    bidho6: float = Field(..., title="매수호가6", description="매수호가6 (소수점 포함)")
    offerrem6: int = Field(..., title="매도호가잔량6", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem6: int = Field(..., title="매수호가잔량6", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno6: int = Field(..., title="매도호가건수6", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno6: int = Field(..., title="매수호가건수6", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho7: float = Field(..., title="매도호가7", description="매도호가7 (소수점 포함)")
    bidho7: float = Field(..., title="매수호가7", description="매수호가7 (소수점 포함)")
    offerrem7: int = Field(..., title="매도호가잔량7", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem7: int = Field(..., title="매수호가잔량7", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno7: int = Field(..., title="매도호가건수7", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno7: int = Field(..., title="매수호가건수7", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho8: float = Field(..., title="매도호가8", description="매도호가8 (소수점 포함)")
    bidho8: float = Field(..., title="매수호가8", description="매수호가8 (소수점 포함)")
    offerrem8: int = Field(..., title="매도호가잔량8", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem8: int = Field(..., title="매수호가잔량8", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno8: int = Field(..., title="매도호가건수8", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno8: int = Field(..., title="매수호가건수8", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho9: float = Field(..., title="매도호가9", description="매도호가9 (소수점 포함)")
    bidho9: float = Field(..., title="매수호가9", description="매수호가9 (소수점 포함)")
    offerrem9: int = Field(..., title="매도호가잔량9", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem9: int = Field(..., title="매수호가잔량9", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno9: int = Field(..., title="매도호가건수9", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno9: int = Field(..., title="매수호가건수9", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    offerho10: float = Field(..., title="매도호가10", description="매도호가10 (소수점 포함)")
    bidho10: float = Field(..., title="매수호가10", description="매수호가10 (소수점 포함)")
    offerrem10: int = Field(..., title="매도호가잔량10", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidrem10: int = Field(..., title="매수호가잔량10", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    offerno10: int = Field(..., title="매도호가건수10", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")
    bidno10: int = Field(..., title="매수호가건수10", description="⚠️ API 미제공: 항상 0 (해외주식 제약)")

    totoffercnt: int = Field(..., title="매도호가총건수", description="매도호가의 총 건수 (⚠️ API 미제공: 항상 0)")
    totbidcnt: int = Field(..., title="매수호가총건수", description="매수호가의 총 건수 (⚠️ API 미제공: 항상 0)")
    totofferrem: int = Field(..., title="매도호가총수량", description="매도호가의 총 수량 (유일하게 유효한 잔량 — offerrem1과 동일)")
    totbidrem: int = Field(..., title="매수호가총수량", description="매수호가의 총 수량 (유일하게 유효한 잔량 — bidrem1과 동일)")


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
