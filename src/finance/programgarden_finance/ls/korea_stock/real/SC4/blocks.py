"""주식주문거부(SC4) 실시간 WebSocket 요청/응답 모델

EN:
    Pydantic models for the SC4 (Stock Order Rejection) real-time WebSocket stream.
    Receives real-time notifications when a stock order is rejected by the exchange.
    Response body has the same field structure as SC1 (Stock Order Execution).

KO:
    주식 주문거부 시 실시간 알림을 수신하기 위한 WebSocket 요청/응답 모델입니다.
    응답 바디는 SC1(주식주문체결)과 동일한 필드 구조를 사용합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader
from ..SC1.blocks import SC1RealResponseBody


class SC4RealRequestHeader(BlockRealRequestHeader):
    pass


class SC4RealResponseHeader(BlockRealResponseHeader):
    pass


class SC4RealRequestBody(BaseModel):
    tr_cd: str = Field("SC4", description="거래 CD")
    tr_key: Optional[str] = Field(None, max_length=8, description="단축코드 (계좌등록/해제 시 필수값 아님)")


class SC4RealRequest(BaseModel):
    """주식주문거부(SC4) 실시간 등록/해제 요청

    EN:
        WebSocket subscription request for stock order rejection notifications.
        Use tr_type='1' to register, '2' to unregister.
        SC0-SC4 share the same registration - registering any one enables all five.

    KO:
        주식주문거부 실시간 알림을 위한 WebSocket 등록/해제 요청입니다.
        SC0-SC4는 하나만 등록해도 5개 주문 이벤트가 모두 활성화됩니다.
    """
    header: SC4RealRequestHeader = Field(
        SC4RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더",
        description="SC4 실시간 계좌등록/해제를 위한 헤더 블록"
    )
    body: SC4RealRequestBody = Field(
        SC4RealRequestBody(tr_cd="SC4", tr_key=""),
        title="요청 바디",
        description="주식주문거부 실시간 등록 바디"
    )


class SC4RealResponseBody(SC1RealResponseBody):
    """주식주문거부(SC4) 실시간 응답 바디

    EN:
        Inherits SC1RealResponseBody. Same ~107 fields.
        When ordxctptncode='14', it indicates an order rejection.

    KO:
        SC1RealResponseBody를 상속합니다. 동일한 약 107개 필드.
        ordxctptncode='14'이면 주문거부를 의미합니다.
    """
    pass


class SC4RealResponse(BaseModel):
    """주식주문거부(SC4) 실시간 응답

    EN:
        Complete response model for SC4 real-time order rejection data.

    KO:
        주식주문거부 실시간 데이터의 전체 응답 모델입니다.
    """
    header: Optional[SC4RealResponseHeader]
    body: Optional[SC4RealResponseBody]

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
