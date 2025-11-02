from typing import Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3106RequestHeader(BlockRequestHeader):
    pass


class O3106ResponseHeader(BlockResponseHeader):
    pass


class O3106InBlock(BaseModel):
    """
    o3106InBlock 데이터 블록

    Attributes:
        symbol (str): 종목심볼
    """
    symbol: str = Field(
        ...,
        title="종목심볼",
        description="종목심볼"
    )


class O3106Request(BaseModel):
    """
    o3106 API 요청 전체 구조
    """
    header: O3106RequestHeader = O3106RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3106",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3106InBlock"], O3106InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3106InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3106"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3106OutBlock(BaseModel):
    """
    o3106OutBlock 데이터 블록 리스트 항목
    """
    symbol: str = Field(default="", title="종목코드", description="종목코드")
    """종목코드"""
    symbolname: str = Field(default="", title="종목명", description="종목명")
    """종목명"""
    price: float = Field(default=0.0, title="현재가", description="현재가")
    """현재가 (Number - precision 15.9)"""
    sign: str = Field(default="", title="전일대비구분", description="전일대비구분")
    """전일대비구분"""
    change: float = Field(default=0.0, title="전일대비", description="전일대비")
    """전일대비 (Number - precision 15.9)"""
    diff: float = Field(default=0.0, title="등락율", description="등락율")
    """등락율 (Number - precision 6.2)"""
    volume: int = Field(default=0, title="누적거래량", description="누적거래량")
    """누적거래량"""
    jnilclose: float = Field(default=0.0, title="전일종가", description="전일종가")
    """전일종가 (Number - precision 15.9)"""
    open: float = Field(default=0.0, title="시가", description="시가")
    """시가 (Number - precision 15.9)"""
    high: float = Field(default=0.0, title="고가", description="고가")
    """고가 (Number - precision 15.9)"""
    low: float = Field(default=0.0, title="저가", description="저가")
    """저가 (Number - precision 15.9)"""
    hotime: str = Field(default="", title="호가수신시간", description="호가수신시간")
    """호가수신시간"""

    # 호가 1~5
    offerho1: float = Field(default=0.0, title="매도호가1", description="매도호가1")
    """매도호가1"""
    bidho1: float = Field(default=0.0, title="매수호가1", description="매수호가1")
    """매수호가1"""
    offercnt1: int = Field(default=0, title="매도호가건수1", description="매도호가건수1")
    """매도호가건수1"""
    bidcnt1: int = Field(default=0, title="매수호가건수1", description="매수호가건수1")
    """매수호가건수1"""
    offerrem1: int = Field(default=0, title="매도호가수량1", description="매도호가수량1")
    """매도호가수량1"""
    bidrem1: int = Field(default=0, title="매수호가수량1", description="매수호가수량1")
    """매수호가수량1"""

    offerho2: float = Field(default=0.0, title="매도호가2", description="매도호가2")
    """매도호가2"""
    bidho2: float = Field(default=0.0, title="매수호가2", description="매수호가2")
    """매수호가2"""
    offercnt2: int = Field(default=0, title="매도호가건수2", description="매도호가건수2")
    """매도호가건수2"""
    bidcnt2: int = Field(default=0, title="매수호가건수2", description="매수호가건수2")
    """매수호가건수2"""
    offerrem2: int = Field(default=0, title="매도호가수량2", description="매도호가수량2")
    """매도호가수량2"""
    bidrem2: int = Field(default=0, title="매수호가수량2", description="매수호가수량2")
    """매수호가수량2"""

    offerho3: float = Field(default=0.0, title="매도호가3", description="매도호가3")
    """매도호가3"""
    bidho3: float = Field(default=0.0, title="매수호가3", description="매수호가3")
    """매수호가3"""
    offercnt3: int = Field(default=0, title="매도호가건수3", description="매도호가건수3")
    """매도호가건수3"""
    bidcnt3: int = Field(default=0, title="매수호가건수3", description="매수호가건수3")
    """매수호가건수3"""
    offerrem3: int = Field(default=0, title="매도호가수량3", description="매도호가수량3")
    """매도호가수량3"""
    bidrem3: int = Field(default=0, title="매수호가수량3", description="매수호가수량3")
    """매수호가수량3"""

    offerho4: float = Field(default=0.0, title="매도호가4", description="매도호가4")
    """매도호가4"""
    bidho4: float = Field(default=0.0, title="매수호가4", description="매수호가4")
    """매수호가4"""
    offercnt4: int = Field(default=0, title="매도호가건수4", description="매도호가건수4")
    """매도호가건수4"""
    bidcnt4: int = Field(default=0, title="매수호가건수4", description="매수호가건수4")
    """매수호가건수4"""
    offerrem4: int = Field(default=0, title="매도호가수량4", description="매도호가수량4")
    """매도호가수량4"""
    bidrem4: int = Field(default=0, title="매수호가수량4", description="매수호가수량4")
    """매수호가수량4"""

    offerho5: float = Field(default=0.0, title="매도호가5", description="매도호가5")
    """매도호가5"""
    bidho5: float = Field(default=0.0, title="매수호가5", description="매수호가5")
    """매수호가5"""
    offercnt5: int = Field(default=0, title="매도호가건수5", description="매도호가건수5")
    """매도호가건수5"""
    bidcnt5: int = Field(default=0, title="매수호가건수5", description="매수호가건수5")
    """매수호가건수5"""
    offerrem5: int = Field(default=0, title="매도호가수량5", description="매도호가수량5")
    """매도호가수량5"""
    bidrem5: int = Field(default=0, title="매수호가수량5", description="매수호가수량5")
    """매수호가수량5"""

    # 합계
    offercnt: int = Field(default=0, title="매도호가건수합", description="매도호가건수합")
    """매도호가건수합"""
    bidcnt: int = Field(default=0, title="매수호가건수합", description="매수호가건수합")
    """매수호가건수합"""
    offer: int = Field(default=0, title="매도호가수량합", description="매도호가수량합")
    """매도호가수량합"""
    bid: int = Field(default=0, title="매수호가수량합", description="매수호가수량합")
    """매수호가수량합"""


class O3106Response(BaseModel):
    """
    o3106 API 응답 전체 구조
    """
    header: Optional[O3106ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: Optional[O3106OutBlock] = Field(
        None,
        title="출력 블록",
        description="o3106 응답의 출력 블록"
    )
    status_code: Optional[int] = Field(
        None,
        title="HTTP 상태 코드",
        description="HTTP 상태 코드"
    )
    rsp_cd: str = Field(..., title="응답 코드", description="응답 코드")
    rsp_msg: str = Field(..., title="응답 메시지", description="응답 메시지")
    error_msg: Optional[str] = Field(None, title="오류 메시지", description="오류 메시지 (있으면)")

    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
