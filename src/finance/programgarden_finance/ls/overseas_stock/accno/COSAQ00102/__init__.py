
from typing import Optional, Callable, Dict, Any

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSAQ00102InBlock1,
    COSAQ00102OutBlock1,
    COSAQ00102OutBlock2,
    COSAQ00102OutBlock3,
    COSAQ00102Request,
    COSAQ00102Response,
    COSAQ00102ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCOSAQ00102(TRAccnoAbstract):
    """LS증권 OpenAPI의 COSAQ00102 계좌 주문 내역 조회를 위한 클래스입니다.

    This class is structured to use GenericTR similar to COSAQ01400 for
    consistent request/response handling.
    """

    def __init__(self, request_data: COSAQ00102Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSAQ00102Request):
            raise TrRequestDataNotFoundException()

        # generic helper
        self._generic: GenericTR[COSAQ00102Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSAQ00102Response:
        if exc is not None:
            return COSAQ00102Response(
                header=None,
                block1=None,
                block2=None,
                block3=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(exc),
            )

        resp_json = resp_json or {}
        block1 = resp_json.get("COSAQ00102OutBlock1", None)
        block2 = resp_json.get("COSAQ00102OutBlock2", None)
        block3 = resp_json.get("COSAQ00102OutBlock3", [])

        result = COSAQ00102Response(
            header=COSAQ00102ResponseHeader.model_validate(resp_headers),
            block1=COSAQ00102OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=COSAQ00102OutBlock2.model_validate(block2) if block2 is not None else None,
            block3=[COSAQ00102OutBlock3.model_validate(item) for item in block3],
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    async def req_async(self) -> COSAQ00102Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSAQ00102Response:
        # kept for backward compatibility
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSAQ00102Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSAQ00102Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSAQ00102Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSAQ00102Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSAQ00102,
    COSAQ00102InBlock1,
    COSAQ00102OutBlock1,
    COSAQ00102OutBlock2,
    COSAQ00102OutBlock3,
    COSAQ00102Request,
    COSAQ00102Response,
    COSAQ00102ResponseHeader
]
