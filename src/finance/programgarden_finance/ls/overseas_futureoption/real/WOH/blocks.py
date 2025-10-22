from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class WOHRealRequestHeader(BlockRealRequestHeader):
    pass


class WOHRealResponseHeader(BlockRealResponseHeader):
    pass


class WOHRealRequestBody(BaseModel):
    tr_cd: str = Field("WOH", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드")

    @field_validator("tr_key", mode="before")
    def ensure_trailing_8_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)[:8]
        return s.ljust(8)

    model_config = ConfigDict(validate_assignment=True)


class WOHRealRequest(BaseModel):
    header: WOHRealRequestHeader = Field(
        WOHRealRequestHeader(
            token="",
            tr_type="1"
        ),
        title="요청 헤더 데이터 블록",
        description="WOH API 요청을 위한 헤더 데이터 블록"
    )
    body: WOHRealRequestBody = Field(
        ...,
        title="입력 데이터 블록",
        description="해외옵션 호가 입력 데이터 블록",
    )


class WOHRealResponseBody(BaseModel):
    symbol: str = Field(..., title="종목코드", description="종목코드")
    """종목코드"""
    hotime: str = Field(..., title="호가시간", description="호가시간")
    """호가시간"""

    offerho1: str = Field(..., title="매도호가 1", description="매도호가 1")
    """매도호가 1"""
    bidho1: str = Field(..., title="매수호가 1", description="매수호가 1")
    """매수호가 1"""
    offerrem1: str = Field(..., title="매도호가 잔량 1", description="매도호가 잔량 1")
    """매도호가 잔량 1"""
    bidrem1: str = Field(..., title="매수호가 잔량 1", description="매수호가 잔량 1")
    """매수호가 잔량 1"""
    offerno1: str = Field(..., title="매도호가 건수 1", description="매도호가 건수 1")
    """매도호가 건수 1"""
    bidno1: str = Field(..., title="매수호가 건수 1", description="매수호가 건수 1")
    """매수호가 건수 1"""

    offerho2: str = Field(..., title="매도호가 2", description="매도호가 2")
    """매도호가 2"""
    bidho2: str = Field(..., title="매수호가 2", description="매수호가 2")
    """매수호가 2"""
    offerrem2: str = Field(..., title="매도호가 잔량 2", description="매도호가 잔량 2")
    """매도호가 잔량 2"""
    bidrem2: str = Field(..., title="매수호가 잔량 2", description="매수호가 잔량 2")
    """매수호가 잔량 2"""
    offerno2: str = Field(..., title="매도호가 건수 2", description="매도호가 건수 2")
    """매도호가 건수 2"""
    bidno2: str = Field(..., title="매수호가 건수 2", description="매수호가 건수 2")
    """매수호가 건수 2"""

    offerho3: str = Field(..., title="매도호가 3", description="매도호가 3")
    """매도호가 3"""
    bidho3: str = Field(..., title="매수호가 3", description="매수호가 3")
    """매수호가 3"""
    offerrem3: str = Field(..., title="매도호가 잔량 3", description="매도호가 잔량 3")
    """매도호가 잔량 3"""
    bidrem3: str = Field(..., title="매수호가 잔량 3", description="매수호가 잔량 3")
    """매수호가 잔량 3"""
    offerno3: str = Field(..., title="매도호가 건수 3", description="매도호가 건수 3")
    """매도호가 건수 3"""
    bidno3: str = Field(..., title="매수호가 건수 3", description="매수호가 건수 3")
    """매수호가 건수 3"""

    offerho4: str = Field(..., title="매도호가 4", description="매도호가 4")
    """매도호가 4"""
    bidho4: str = Field(..., title="매수호가 4", description="매수호가 4")
    """매수호가 4"""
    offerrem4: str = Field(..., title="매도호가 잔량 4", description="매도호가 잔량 4")
    """매도호가 잔량 4"""
    bidrem4: str = Field(..., title="매수호가 잔량 4", description="매수호가 잔량 4")
    """매수호가 잔량 4"""
    offerno4: str = Field(..., title="매도호가 건수 4", description="매도호가 건수 4")
    """매도호가 건수 4"""
    bidno4: str = Field(..., title="매수호가 건수 4", description="매수호가 건수 4")
    """매수호가 건수 4"""

    offerho5: str = Field(..., title="매도호가 5", description="매도호가 5")
    """매도호가 5"""
    bidho5: str = Field(..., title="매수호가 5", description="매수호가 5")
    """매수호가 5"""
    offerrem5: str = Field(..., title="매도호가 잔량 5", description="매도호가 잔량 5")
    """매도호가 잔량 5"""
    bidrem5: str = Field(..., title="매수호가 잔량 5", description="매수호가 잔량 5")
    """매수호가 잔량 5"""
    offerno5: str = Field(..., title="매도호가 건수 5", description="매도호가 건수 5")
    """매도호가 건수 5"""
    bidno5: str = Field(..., title="매수호가 건수 5", description="매수호가 건수 5")
    """매수호가 건수 5"""

    totoffercnt: str = Field(..., title="매도호가총건수", description="매도호가총건수")
    """매도호가총건수"""
    totbidcnt: str = Field(..., title="매수호가총건수", description="매수호가총건수")
    """매수호가총건수"""
    totofferrem: str = Field(..., title="매도호가총수량", description="매도호가총수량")
    """매도호가총수량"""
    totbidrem: str = Field(..., title="매수호가총수량", description="매수호가총수량")
    """매수호가총수량"""


class WOHRealResponse(BaseModel):
    header: Optional[WOHRealResponseHeader]
    body: Optional[WOHRealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드")
    rsp_msg: str = Field(..., title="응답 메시지")
    error_msg: Optional[str] = Field(None, title="오류 메시지")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
