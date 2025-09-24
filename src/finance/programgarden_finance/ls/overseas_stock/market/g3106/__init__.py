from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from programgarden_finance.ls.status import RequestStatus
from .blocks import (
    G3106InBlock,
    G3106OutBlock,
    G3106Request,
    G3106Response,
    G3106ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrG3106(TRRequestAbstract, RetryReqAbstract):
    def __init__(self, request_data: G3106Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3106Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[G3106Response] = GenericTR(self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3106Response:
        if exc is not None:
            return G3106Response(header=None, block=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block = resp_json.get("g3106OutBlock", None)
        result = G3106Response(
            header=G3106ResponseHeader.model_validate(resp_headers),
            block=G3106OutBlock.model_validate(block) if block is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> G3106Response:
        return self._generic.req()

    async def req_async(self) -> G3106Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3106Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[G3106Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[G3106Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> G3106Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrG3106,
    G3106InBlock,
    G3106OutBlock,
    G3106Request,
    G3106Response,
    G3106ResponseHeader,
]
