from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader


class GSCRealRequestHeader(BlockRealRequestHeader):
    pass


class GSCRealResponseHeader(BlockRealResponseHeader):
    pass


class GSCRealRequestBody(BaseModel):
    tr_cd: str = Field("GSC", description="거래 CD")
    tr_key: str = Field(..., max_length=18, description="단축코드 + padding(공백12자리)")

    @field_validator("tr_key", mode="before")
    def ensure_trailing_12_spaces(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) < 18:
            return s.ljust(18)
        return s

    model_config = ConfigDict(validate_assignment=True)


class GSCRealRequest(BaseModel):
    """
    해외주식 실시간 시세 요청
    """
    header: GSCRealRequestHeader = Field(
        GSCRealRequestHeader(
            token="",
            tr_type="3"
        ),
        title="요청 헤더 데이터 블록",
        description="GSC API 요청을 위한 헤더 데이터 블록"
    )
    """요청 헤더 데이터 블록"""
    body: GSCRealRequestBody = Field(
        GSCRealRequestBody(
            tr_cd="GSC",
            tr_key=""
        ),
        title="입력 데이터 블록",
        description="해외증권 매도상환주문(미국) 입력 데이터 블록",
    )


class GSCRealResponseBody(BaseModel):
    """
    GSC 실시간 응답 바디 모델

    필드 설명은 LS증권 WSS GSC 응답 규격에 따릅니다.
    """
    symbol: str = Field(..., title="종목코드", description="종목코드 (예: SOXL)")
    """종목코드"""
    ovsdate: str = Field(..., title="체결일자(현지)", description="체결일자(현지, YYYYMMDD)")
    """체결일자(현지)"""
    kordate: str = Field(..., title="체결일자(한국)", description="체결일자(한국, YYYYMMDD)")
    """체결일자(한국)"""
    trdtm: str = Field(..., title="체결시간(현지)", description="체결시간(현지, HHMMSS)")
    """체결시간(현지)"""
    kortm: str = Field(..., title="체결시간(한국)", description="체결시간(한국, HHMMSS)")
    """체결시간(한국)"""
    sign: str = Field(..., title="전일대비구분", description="전일대비구분 코드")
    """전일대비구분"""
    price: float = Field(..., title="체결가격", description="체결가격 (문자열, 소수점 포함)")
    """체결가격"""
    diff: float = Field(..., title="전일대비", description="전일대비 금액")
    """전일대비"""
    rate: float = Field(..., title="등락율", description="등락율 (예: -0.65)")
    """등락율"""
    open: float = Field(..., title="시가", description="시가")
    """시가"""
    high: float = Field(..., title="고가", description="고가")
    """고가"""
    low: float = Field(..., title="저가", description="저가")
    """저가"""
    trdq: int = Field(..., title="건별체결수량", description="건별 체결 수량")
    """건별체결수량"""
    totq: int = Field(..., title="누적체결수량", description="누적 체결 수량")
    """누적체결수량"""
    cgubun: str = Field(..., title="체결구분", description="체결구분 (예: +)")
    """체결구분"""
    lSeq: int = Field(..., title="초당시퀀스", description="초당 시퀀스 번호")
    """초당시퀀스"""
    amount: int = Field(..., title="누적거래대금", description="누적 거래대금")
    """누적거래대금"""
    high52p: float = Field(..., title="52주고가", description="52주 고가")
    """52주 고가"""
    low52p: float = Field(..., title="52주저가", description="52주 저가")
    """52주 저가"""


class GSCRealResponse(BaseModel):
    header: Optional[GSCRealResponseHeader]
    body: Optional[GSCRealResponseBody]

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
