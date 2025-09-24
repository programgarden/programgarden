from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    CIDBQ01400InBlock1,
    CIDBQ01400OutBlock1,
    CIDBQ01400OutBlock2,
    CIDBQ01400Request,
    CIDBQ01400Response,
    CIDBQ01400ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCIDBQ01400(TRAccnoAbstract):
    def __init__(self, request_data: CIDBQ01400Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBQ01400Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CIDBQ01400Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBQ01400Response:
        if exc is not None:
            return CIDBQ01400Response(header=None, block1=None, block2=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBQ01400OutBlock1", None)
        block2 = resp_json.get("CIDBQ01400OutBlock2", None)
        result = CIDBQ01400Response(
            header=CIDBQ01400ResponseHeader.model_validate(resp_headers),
            block1=CIDBQ01400OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=CIDBQ01400OutBlock2.model_validate(block2) if block2 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> CIDBQ01400Response:
        return self._generic.req()

    async def req_async(self) -> CIDBQ01400Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBQ01400Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[CIDBQ01400Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[CIDBQ01400Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> CIDBQ01400Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCIDBQ01400,
    CIDBQ01400InBlock1,
    CIDBQ01400OutBlock1,
    CIDBQ01400OutBlock2,
    CIDBQ01400Request,
    CIDBQ01400Response,
    CIDBQ01400ResponseHeader,
]
