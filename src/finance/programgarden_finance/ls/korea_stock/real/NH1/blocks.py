"""(NXT) 호가잔량(NH1) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the NH1 (NXT Order Book) real-time WebSocket stream.
    Provides real-time 10-level order book (bid/ask) data for NXT(Next Trading System)-listed stocks.
    Price and quantity fields use int type (Number in API spec).

KO:
    NXT(넥스트거래소) 종목의 실시간 호가잔량(10단계 매도/매수 호가) 데이터를 수신하기 위한
    WebSocket 요청/응답 모델입니다. 가격/수량 필드는 int 타입이며,
    tr_key는 10자리 패딩('N' + 종목코드 6자리 + 공백 3자리)이 필요합니다.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class NH1RealRequestHeader(BlockRealRequestHeader):
    pass


class NH1RealResponseHeader(BlockRealResponseHeader):
    pass


class NH1RealRequestBody(BaseModel):
    tr_cd: str = Field("NH1", description="거래 CD")
    tr_key: str = Field(..., max_length=10, description="'N' + 종목코드 6자리 + 공백 3자리 (예: 'N000880   ')")

    @field_validator("tr_key", mode="before")
    def ensure_10_char_padding(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 10:
            return s.ljust(10)
        return s

    model_config = ConfigDict(validate_assignment=True)


class NH1RealRequest(BaseModel):
    """(NXT) 호가잔량(NH1) 실시간 시세 등록/해제 요청

    EN:
        WebSocket subscription request for NXT real-time order book data.
        Use tr_type='3' to subscribe, '4' to unsubscribe.
        The tr_key must be 10 characters: 'N' + 6-digit code + 3 spaces.

    KO:
        NXT 종목의 실시간 호가잔량 데이터 수신을 위한 WebSocket 등록/해제 요청입니다.
        tr_type '3'으로 실시간 등록, '4'로 해제합니다.
        tr_key는 'N' + 종목코드 6자리 + 공백 3자리 = 10자리로 패딩됩니다.
    """
    header: NH1RealRequestHeader = Field(
        NH1RealRequestHeader(token="", tr_type="3"),
        title="요청 헤더",
        description="NH1 실시간 시세 등록/해제를 위한 헤더 블록"
    )
    body: NH1RealRequestBody = Field(
        NH1RealRequestBody(tr_cd="NH1", tr_key=""),
        title="요청 바디",
        description="NXT 호가잔량 실시간 등록에 필요한 종목코드 정보"
    )


class NH1RealResponseBody(BaseModel):
    """(NXT) 호가잔량(NH1) 실시간 응답 바디

    EN:
        Real-time NXT 10-level order book data body.
        Contains 10 levels of bid/ask prices (int) and quantities (int),
        total quantities, mid-price, and exchange-specific short code.

    KO:
        NXT 종목의 실시간 10단계 호가잔량 데이터 바디입니다.
        매도/매수 각 10단계 호가(int)와 잔량(int), 총잔량, 중간가격,
        거래소별단축코드 등을 포함합니다.
    """
    hotime: str = Field(..., title="호가시간", description="호가 수신 시간 (HHMMSS, 예: '111244')")
    """호가시간"""
    offerho1: int = Field(..., title="매도호가1", description="매도 최우선호가 (1차)")
    """매도호가1"""
    bidho1: int = Field(..., title="매수호가1", description="매수 최우선호가 (1차)")
    """매수호가1"""
    offerrem1: int = Field(..., title="매도호가잔량1", description="매도 1차 호가 잔량")
    """매도호가잔량1"""
    bidrem1: int = Field(..., title="매수호가잔량1", description="매수 1차 호가 잔량")
    """매수호가잔량1"""
    offerho2: int = Field(..., title="매도호가2", description="매도 2차 호가")
    """매도호가2"""
    bidho2: int = Field(..., title="매수호가2", description="매수 2차 호가")
    """매수호가2"""
    offerrem2: int = Field(..., title="매도호가잔량2", description="매도 2차 호가 잔량")
    """매도호가잔량2"""
    bidrem2: int = Field(..., title="매수호가잔량2", description="매수 2차 호가 잔량")
    """매수호가잔량2"""
    offerho3: int = Field(..., title="매도호가3", description="매도 3차 호가")
    """매도호가3"""
    bidho3: int = Field(..., title="매수호가3", description="매수 3차 호가")
    """매수호가3"""
    offerrem3: int = Field(..., title="매도호가잔량3", description="매도 3차 호가 잔량")
    """매도호가잔량3"""
    bidrem3: int = Field(..., title="매수호가잔량3", description="매수 3차 호가 잔량")
    """매수호가잔량3"""
    offerho4: int = Field(..., title="매도호가4", description="매도 4차 호가")
    """매도호가4"""
    bidho4: int = Field(..., title="매수호가4", description="매수 4차 호가")
    """매수호가4"""
    offerrem4: int = Field(..., title="매도호가잔량4", description="매도 4차 호가 잔량")
    """매도호가잔량4"""
    bidrem4: int = Field(..., title="매수호가잔량4", description="매수 4차 호가 잔량")
    """매수호가잔량4"""
    offerho5: int = Field(..., title="매도호가5", description="매도 5차 호가")
    """매도호가5"""
    bidho5: int = Field(..., title="매수호가5", description="매수 5차 호가")
    """매수호가5"""
    offerrem5: int = Field(..., title="매도호가잔량5", description="매도 5차 호가 잔량")
    """매도호가잔량5"""
    bidrem5: int = Field(..., title="매수호가잔량5", description="매수 5차 호가 잔량")
    """매수호가잔량5"""
    offerho6: int = Field(..., title="매도호가6", description="매도 6차 호가")
    """매도호가6"""
    bidho6: int = Field(..., title="매수호가6", description="매수 6차 호가")
    """매수호가6"""
    offerrem6: int = Field(..., title="매도호가잔량6", description="매도 6차 호가 잔량")
    """매도호가잔량6"""
    bidrem6: int = Field(..., title="매수호가잔량6", description="매수 6차 호가 잔량")
    """매수호가잔량6"""
    offerho7: int = Field(..., title="매도호가7", description="매도 7차 호가")
    """매도호가7"""
    bidho7: int = Field(..., title="매수호가7", description="매수 7차 호가")
    """매수호가7"""
    offerrem7: int = Field(..., title="매도호가잔량7", description="매도 7차 호가 잔량")
    """매도호가잔량7"""
    bidrem7: int = Field(..., title="매수호가잔량7", description="매수 7차 호가 잔량")
    """매수호가잔량7"""
    offerho8: int = Field(..., title="매도호가8", description="매도 8차 호가")
    """매도호가8"""
    bidho8: int = Field(..., title="매수호가8", description="매수 8차 호가")
    """매수호가8"""
    offerrem8: int = Field(..., title="매도호가잔량8", description="매도 8차 호가 잔량")
    """매도호가잔량8"""
    bidrem8: int = Field(..., title="매수호가잔량8", description="매수 8차 호가 잔량")
    """매수호가잔량8"""
    offerho9: int = Field(..., title="매도호가9", description="매도 9차 호가")
    """매도호가9"""
    bidho9: int = Field(..., title="매수호가9", description="매수 9차 호가")
    """매수호가9"""
    offerrem9: int = Field(..., title="매도호가잔량9", description="매도 9차 호가 잔량")
    """매도호가잔량9"""
    bidrem9: int = Field(..., title="매수호가잔량9", description="매수 9차 호가 잔량")
    """매수호가잔량9"""
    offerho10: int = Field(..., title="매도호가10", description="매도 10차 호가")
    """매도호가10"""
    bidho10: int = Field(..., title="매수호가10", description="매수 10차 호가")
    """매수호가10"""
    offerrem10: int = Field(..., title="매도호가잔량10", description="매도 10차 호가 잔량")
    """매도호가잔량10"""
    bidrem10: int = Field(..., title="매수호가잔량10", description="매수 10차 호가 잔량")
    """매수호가잔량10"""
    totofferrem: int = Field(..., title="총매도호가잔량", description="매도호가 1~10차 잔량 합계")
    """총매도호가잔량"""
    totbidrem: int = Field(..., title="총매수호가잔량", description="매수호가 1~10차 잔량 합계")
    """총매수호가잔량"""
    donsigubun: str = Field(..., title="동시호가구분", description="동시호가구분 ('1':장개시전, '2':장마감전, '3':장중, '4':장후)")
    """동시호가구분"""
    shcode: str = Field(..., title="단축코드", description="NXT 종목 단축코드 9자리")
    """단축코드"""
    alloc_gubun: str = Field(..., title="배분적용구분", description="배분적용구분")
    """배분적용구분"""
    volume: int = Field(..., title="누적거래량", description="당일 누적 거래량")
    """누적거래량"""
    midprice: int = Field(..., title="중간가격", description="매도1호가와 매수1호가의 중간가격")
    """중간가격"""
    offermidsumrem: int = Field(..., title="매도중간가잔량합계수량", description="매도 중간가 잔량 합계")
    """매도중간가잔량합계수량"""
    bidmidsumrem: int = Field(..., title="매수중간가잔량합계수량", description="매수 중간가 잔량 합계")
    """매수중간가잔량합계수량"""
    midsumrem: int = Field(..., title="중간가잔량합계수량", description="중간가 잔량 합계 (매도+매수)")
    """중간가잔량합계수량"""
    midsumremgubun: str = Field(..., title="중간가잔량구분", description="중간가잔량구분 (' ':없음, '1':매도, '2':매수)")
    """중간가잔량구분"""
    ex_shcode: str = Field(..., title="거래소별단축코드", description="거래소별 단축코드 (예: 'N000880')")
    """거래소별단축코드"""


class NH1RealResponse(BaseModel):
    """(NXT) 호가잔량(NH1) 실시간 응답

    EN:
        Complete response model for NH1 real-time NXT order book data.
        Contains header (TR code) and body (10-level order book details).

    KO:
        NXT 호가잔량 실시간 데이터의 전체 응답 모델입니다.
        header에 TR코드, body에 10단계 호가잔량 상세 데이터가 포함됩니다.
    """
    header: Optional[NH1RealResponseHeader]
    body: Optional[NH1RealResponseBody]

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
