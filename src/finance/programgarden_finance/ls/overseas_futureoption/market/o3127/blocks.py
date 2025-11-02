from typing import List, Literal, Optional, Union

from pydantic import BaseModel, PrivateAttr, Field
from requests import Response

from ....models import BlockRequestHeader, BlockResponseHeader, SetupOptions


class O3127RequestHeader(BlockRequestHeader):
    pass


class O3127ResponseHeader(BlockResponseHeader):
    pass


class O3127InBlock1(BaseModel):
    """
    o3127InBlock1 (Occurs) 데이터 블록 항목

    Attributes:
        mktgb (Literal["F", "O"]): 기본입력 (F:선물, O:옵션)
        symbol (str): 종목심볼
    """
    mktgb: Literal["F", "O"] = Field(..., title="기본입력", description="예) F(선물), O(옵션)")
    symbol: str = Field(..., title="종목심볼", description="종목심볼 (예: 2ESF16_1915)")


class O3127InBlock(BaseModel):
    """
    o3127InBlock 데이터 블록

    Attributes:
        nrec (int): 건수
        inblock1 (Optional[List[O3127InBlock1]]): o3127InBlock1 발생 블록(선택)
    """
    nrec: int = Field(..., title="건수", description="요청 건수 (nrec)")


class O3127Request(BaseModel):
    """
    o3127 API 요청 전체 구조
    """
    header: O3127RequestHeader = O3127RequestHeader(
        content_type="application/json; charset=utf-8",
        authorization="",
        tr_cd="o3127",
        tr_cont="N",
        tr_cont_key="",
        mac_address=""
    )

    # 기존 $SELECTION_PLACEHOLDER$를 아래로 교체
    body: dict[Literal["o3127InBlock", "o3127InBlock1"],
               Union[O3127InBlock, Optional[List[O3127InBlock1]]]] = Field(
        ...,
        title="입력 데이터 블록",
        description="입력 데이터 블록"
    )
    options: SetupOptions = Field(
        SetupOptions(
            rate_limit_count=1,
            rate_limit_seconds=1,
            on_rate_limit="wait",
            rate_limit_key="o3127"
        ),
        title="설정 옵션",
        description="코드 실행 전 설정(setup)을 위한 옵션"
    )


class O3127OutBlock(BaseModel):
    """
    o3127OutBlock 데이터 블록 리스트 항목
    """
    symbol: str = Field(default="", title="종목코드", description="종목코드")
    symbolname: str = Field(default="", title="종목명", description="종목명")
    price: float = Field(default=0.0, title="현재가", description="현재가")
    sign: str = Field(default="", title="전일대비구분", description="전일대비구분")
    change: float = Field(default=0.0, title="전일대비", description="전일대비")
    diff: float = Field(default=0.0, title="등락율", description="등락율")
    volume: int = Field(default=0, title="누적거래량", description="누적거래량")
    jnilclose: float = Field(default=0.0, title="전일종가", description="전일종가")
    open: float = Field(default=0.0, title="시가", description="시가")
    high: float = Field(default=0.0, title="고가", description="고가")
    low: float = Field(default=0.0, title="저가", description="저가")
    offerho1: float = Field(default=0.0, title="매도호가1", description="매도호가1")
    bidho1: float = Field(default=0.0, title="매수호가1", description="매수호가1")
    offercnt1: int = Field(default=0, title="매도호가건수1", description="매도호가건수1")
    bidcnt1: int = Field(default=0, title="매수호가건수1", description="매수호가건수1")
    offerrem1: int = Field(default=0, title="매도호가수량1", description="매도호가수량1")
    bidrem1: int = Field(default=0, title="매수호가수량1", description="매수호가수량1")
    offercnt: int = Field(default=0, title="매도호가건수합", description="매도호가건수합")
    bidcnt: int = Field(default=0, title="매수호가건수합", description="매수호가건수합")
    offer: int = Field(default=0, title="매도호가수량합", description="매도호가수량합")
    bid: int = Field(default=0, title="매수호가수량합", description="매수호가수량합")


class O3127Response(BaseModel):
    """
    o3127 API 응답 전체 구조
    """
    header: Optional[O3127ResponseHeader] = Field(
        None,
        title="응답 헤더",
        description="응답 헤더 데이터 블록"
    )
    block: List[O3127OutBlock] = Field(
        ...,
        title="출력 블록 리스트",
        description="o3127 응답의 출력 블록 리스트"
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
