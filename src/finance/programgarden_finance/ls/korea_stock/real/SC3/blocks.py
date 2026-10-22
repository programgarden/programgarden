"""Pydantic models for LS Securities OpenAPI SC3 (Stock order cancel-confirm push).

SC3 is a Real-time WebSocket TR that pushes per-event notifications when
a stock order cancellation is confirmed by the exchange.  Subscription
is account-keyed (``tr_type='1'``); a single SC0..SC4 registration
enables all five order-event streams.

The ``SC3RealResponseBody`` inherits ``SC1RealResponseBody`` — same
~130 fields.  When ``ordxctptncode='13'`` the event is a cancel-confirm.

Field source policy: identical to SC1 (see that module's docstring for
the full policy).
"""

from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from websockets import Response

from ....models import BlockRealRequestHeader, BlockRealResponseHeader
from ..SC1.blocks import SC1RealResponseBody


class SC3RealRequestHeader(BlockRealRequestHeader):
    """SC3 real-time request header. Inherits the standard LS WS request header schema."""
    pass


class SC3RealResponseHeader(BlockRealResponseHeader):
    """SC3 real-time response header. Inherits the standard LS WS response header schema."""
    pass


class SC3RealRequestBody(BaseModel):
    """SC3RealRequestBody — WebSocket subscription envelope for stock order cancel-confirm push."""

    tr_cd: str = Field(
        default="SC3",
        title="거래 CD (TR code)",
        description="Fixed TR code identifier for this subscription. Always 'SC3'.",
        examples=["SC3"],
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


class SC3RealRequest(BaseModel):
    """SC3 (stock-order cancel-confirm) real-time subscription request."""
    header: SC3RealRequestHeader = Field(
        SC3RealRequestHeader(token="", tr_type="1"),
        title="요청 헤더 (Request header)",
        description="SC3 WebSocket subscription header block (token + tr_type; tr_type='1' register account / '2' unregister)."
    )
    body: SC3RealRequestBody = Field(
        SC3RealRequestBody(tr_cd="SC3", tr_key=""),
        title="요청 바디 (Request body)",
        description="SC3 input body — TR code 'SC3' for stock-order cancel-confirm events; tr_key empty (account-level subscription)."
    )


class SC3RealResponseBody(SC1RealResponseBody):
    """SC3RealResponseBody — cancel-confirm event (ordxctptncode='13').

    Inherits ``SC1RealResponseBody`` verbatim.  ``ordxctptncode='13'``
    indicates this event is a cancel confirmation.
    """
    pass


class SC3RealResponse(BaseModel):
    """SC3 (stock-order cancel-confirm) real-time response."""
    header: Optional[SC3RealResponseHeader]
    body: Optional[SC3RealResponseBody]

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
