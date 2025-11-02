from typing import List, Literal, Optional

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3107RequestHeader(BlockRequestHeader):
    pass


class O3107ResponseHeader(BlockResponseHeader):
    pass


class O3107InBlock(BaseModel):
    """
    o3107InBlock 데이터 블록

    Attributes:
        symbol (str): 종목심볼
    """
    symbol: str = Field(
        ...,
        title="종목심볼",
        description="종목심볼"
    )


class O3107Request(BaseModel):
    """
    o3107 API 요청 전체 구조
    """
    header: O3107RequestHeader = O3107RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3107",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )
    body: dict[Literal["o3107InBlock"], O3107InBlock] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록 (키: 'o3107InBlock')"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3107"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )
    """코드 실행 전 설정(setup)을 위한 옵션"""


class O3107OutBlock(BaseModel):
    """
    o3107OutBlock 데이터 블록 리스트 항목
    """
    symbol: str = Field(default="", title="종목코드", description="종목코드")
    """종목코드 (심볼)"""
    symbolname: str = Field(default="", title="종목명", description="종목명")
    """종목명"""
    price: float = Field(default=0.0, title="현재가", description="현재가")
    """현재가 (마지막 체결가)"""
    sign: str = Field(default="", title="전일대비구분", description="전일대비구분")
    """전일 대비 구분 (예: 상승/하락/보합)"""
    change: float = Field(default=0.0, title="전일대비", description="전일대비")
    """전일 대비 가격 차이"""
    diff: float = Field(default=0.0, title="등락율", description="등락율")
    """등락률 (퍼센트)"""
    volume: int = Field(default=0, title="누적거래량", description="누적거래량")
    """누적 거래량"""
    jnilclose: float = Field(default=0.0, title="전일종가", description="전일종가")
    """전일 종가"""
    open: float = Field(default=0.0, title="시가", description="시가")
    """시가"""
    high: float = Field(default=0.0, title="고가", description="고가")
    """고가"""
    low: float = Field(default=0.0, title="저가", description="저가")
    """저가"""
    offerho1: float = Field(default=0.0, title="매도호가1", description="매도호가1")
    """매도호가 1"""
    bidho1: float = Field(default=0.0, title="매수호가1", description="매수호가1")
    """매수호가 1"""
    offercnt1: int = Field(default=0, title="매도호가건수1", description="매도호가건수1")
    """매도 호가 건수 1"""
    bidcnt1: int = Field(default=0, title="매수호가건수1", description="매수호가건수1")
    """매수 호가 건수 1"""
    offerrem1: int = Field(default=0, title="매도호가수량1", description="매도호가수량1")
    """매도 호가 수량 1"""
    bidrem1: int = Field(default=0, title="매수호가수량1", description="매수호가수량1")
    """매수 호가 수량 1"""
    offercnt: int = Field(default=0, title="매도호가건수합", description="매도호가건수합")
    """매도 호가 건수 합계"""
    bidcnt: int = Field(default=0, title="매수호가건수합", description="매수호가건수합")
    """매수 호가 건수 합계"""
    offer: int = Field(default=0, title="매도호가수량합", description="매도호가수량합")
    """매도 호가 수량 합계"""
    bid: int = Field(default=0, title="매수호가수량합", description="매수호가수량합")
    """매수 호가 수량 합계"""


class O3107Response(BaseModel):
    """
    o3107 API 응답 전체 구조
    """
    header: Optional[O3107ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: List[O3107OutBlock] = Field(
        ...,
        title="출력 블록 리스트",
        description="o3107 응답의 출력 블록 리스트"
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
