from typing import Optional, Callable, Dict, Any

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSOQ02701InBlock1,
    COSOQ02701OutBlock1,
    COSOQ02701OutBlock2,
    COSOQ02701OutBlock3,
    COSOQ02701OutBlock4,
    COSOQ02701OutBlock5,
    COSOQ02701Request,
    COSOQ02701Response,
    COSOQ02701ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
# ... no local logger needed; GenericTR handles errors in the response builder


class TrCOSOQ02701(TRAccnoAbstract):
    """LS OpenAPI의 COSOQ02701 외화 예수금 및 주문 가능 금액을 조회하는 클래스입니다.

    Uses GenericTR for consistent behavior and error propagation.
    """

    def __init__(self, request_data: COSOQ02701Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSOQ02701Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSOQ02701Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSOQ02701Response:
        if exc is not None:
            return COSOQ02701Response(
                header=None,
                block1=None,
                block2=[],
                block3=[],
                block4=None,
                block5=None,
                rsp_cd="",
                rsp_msg="",
                error_msg=str(exc),
            )

        resp_json = resp_json or {}
        block1 = resp_json.get("COSOQ02701OutBlock1", None)
        block4 = resp_json.get("COSOQ02701OutBlock4", None)
        block5 = resp_json.get("COSOQ02701OutBlock5", None)

        result = COSOQ02701Response(
            header=COSOQ02701ResponseHeader.model_validate(resp_headers),
            block1=COSOQ02701OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=[COSOQ02701OutBlock2.model_validate(item) for item in resp_json.get("COSOQ02701OutBlock2", [])],
            block3=[COSOQ02701OutBlock3.model_validate(item) for item in resp_json.get("COSOQ02701OutBlock3", [])],
            block4=COSOQ02701OutBlock4.model_validate(block4) if block4 is not None else None,
            block5=COSOQ02701OutBlock5.model_validate(block5) if block5 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )

        result.raw_data = resp
        return result

    async def req_async(self) -> COSOQ02701Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSOQ02701Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSOQ02701Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSOQ02701Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSOQ02701Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSOQ02701Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSOQ02701,
    COSOQ02701InBlock1,
    COSOQ02701OutBlock1,
    COSOQ02701OutBlock2,
    COSOQ02701OutBlock3,
    COSOQ02701OutBlock4,
    COSOQ02701OutBlock5,
    COSOQ02701Request,
    COSOQ02701Response,
    COSOQ02701ResponseHeader
]
