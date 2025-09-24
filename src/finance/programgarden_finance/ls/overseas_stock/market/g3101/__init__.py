from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    G3101InBlock,
    G3101OutBlock,
    G3101Request,
    G3101Response,
    G3101ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrG3101(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 g3101 시세 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: G3101Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3101Request):
            raise TrRequestDataNotFoundException()

        # generic helper delegates HTTP/serialization
        self._generic: GenericTR[G3101Response] = GenericTR(self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3101Response:
        if exc is not None:
            return G3101Response(header=None, block=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block = resp_json.get("g3101OutBlock", None)
        result = G3101Response(
            header=G3101ResponseHeader.model_validate(resp_headers),
            block=G3101OutBlock.model_validate(block) if block is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> G3101Response:
        return self._generic.req()

    async def req_async(self) -> G3101Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3101Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[G3101Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[G3101Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> G3101Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrG3101,
    G3101InBlock,
    G3101OutBlock,
    G3101Request,
    G3101Response,
    G3101ResponseHeader,
]
