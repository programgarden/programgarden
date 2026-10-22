"""Pydantic models for LS Securities OpenAPI SC4 (Stock order reject push).

SC4 is a Real-time WebSocket TR that pushes per-event notifications when
a stock order is rejected by the exchange.  Subscription is account-keyed
(``tr_type='1'``); a single SC0..SC4 registration enables all five
order-event streams.

The ``SC4RealResponseBody`` inherits ``SC1RealResponseBody`` — same
~130 fields.  When ``ordxctptncode='14'`` the event is an order reject.

Field source policy: identical to SC1 (see that module's docstring for
the full policy).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader
from ..SC1.blocks import SC1RealResponseBody


class SC4RealRequestHeader(BlockRealRequestHeader):
    """SC4 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class SC4RealResponseHeader(BlockRealResponseHeader):
    """SC4 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class SC4RealRequestBody(BaseModel):
    """SC4RealRequestBody — WebSocket subscription envelope for stock order reject push."""

    tr_cd: str = Field(
        default="SC4",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'SC4'.",
        examples=["SC4"],
    )
    tr_key: Optional[str] = Field(
        default=None,
        max_length=8,
        title="단축코드 (Short symbol code, optional)",
        description=(
            "Optional short symbol code. SC0..SC4 subscriptions are "
            "account-scoped (``tr_type='1'``) so this is typically left "
            "blank."
        ),
        examples=["", "005930"],
    )


class SC4RealRequest(BaseModel):
    """SC4 (stock-order rejection) real-time subscription request."""
    header: SC4RealRequestHeader = Field(
        SC4RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더 (Request header)",
        description="SC4 WebSocket subscription header block (token + tr_type; tr_type='1' register account / '2' unregister)."
    )
    body: SC4RealRequestBody = Field(
        SC4RealRequestBody(tr_cd="SC4", tr_key=""),
        title="요청 바디 (Request body)",
        description="SC4 input body — TR code 'SC4' for stock-order rejection events; tr_key empty (account-level subscription)."
    )


class SC4RealResponseBody(SC1RealResponseBody):
    """SC4RealResponseBody — order-reject event (ordxctptncode='14').

    Inherits ``SC1RealResponseBody`` verbatim.  ``ordxctptncode='14'``
    indicates this event is an order rejection.
    """
    pass


class SC4RealResponse(BaseModel):
    """SC4 (stock-order rejection) real-time response."""
    header: Optional[SC4RealResponseHeader]
    body: Optional[SC4RealResponseBody]

    rsp_cd: str = Field(..., title="응답 코드 (Response code)")
    rsp_msg: str = Field(..., title="응답 메시지 (Response message)")
    error_msg: Optional[str] = Field(None, title="오류 메시지 (Error message)")
    _raw_data: Optional[Response] = PrivateAttr(default=None)

    @property
    def raw_data(self) -> Optional[Response]:
        return self._raw_data

    @raw_data.setter
    def raw_data(self, raw_resp: Response) -> None:
        self._raw_data = raw_resp
