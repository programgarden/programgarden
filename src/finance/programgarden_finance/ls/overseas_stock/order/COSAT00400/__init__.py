from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSAT00400InBlock1,
    COSAT00400OutBlock1,
    COSAT00400OutBlock2,
    COSAT00400Request,
    COSAT00400Response,
    COSAT00400ResponseHeader,
)
from ....tr_base import TROrderAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
# pg_logger intentionally unused here; GenericTR handles logging


class TrCOSAT00400(TROrderAbstract):
    def __init__(self, request_data: COSAT00400Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSAT00400Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSAT00400Response] = GenericTR(self.request_data, self._build_response, url=URLS.ORDER_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSAT00400Response:
        if exc is not None:
            return COSAT00400Response(header=None, block1=None, block2=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block1 = resp_json.get("COSAT00400OutBlock1", None)
        block2 = resp_json.get("COSAT00400OutBlock2", None)
        result = COSAT00400Response(
            header=COSAT00400ResponseHeader.model_validate(resp_headers),
            block1=COSAT00400OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=COSAT00400OutBlock2.model_validate(block2) if block2 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> COSAT00400Response:
        return self._generic.req()

    async def req_async(self) -> COSAT00400Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> COSAT00400Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()


__all__ = [
    TrCOSAT00400,
    COSAT00400InBlock1,
    COSAT00400OutBlock1,
    COSAT00400OutBlock2,
    COSAT00400Request,
    COSAT00400Response,
    COSAT00400ResponseHeader
]
