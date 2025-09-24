from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3103InBlock,
    O3103OutBlock,
    O3103OutBlock1,
    O3103Request,
    O3103Response,
    O3103ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrO3103(TRRequestAbstract, OccursReqAbstract):
    def __init__(self, request_data: O3103Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3103Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3103Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3103Response:
        if exc is not None:
            return O3103Response(header=None, block=None, block1=[], rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block = resp_json.get("o3103OutBlock", None)
        block1 = resp_json.get("o3103OutBlock1", [])
        result = O3103Response(
            header=O3103ResponseHeader.model_validate(resp_headers),
            block=O3103OutBlock.model_validate(block) if block is not None else None,
            block1=[O3103OutBlock1.model_validate(item) for item in block1],
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3103Response:
        return self._generic.req()

    def occurs_req(self, callback: Optional[Callable[[Optional[O3103Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3103Response]:
        def _updater(req_data, resp: O3103Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["o3103InBlock"].cts_date = resp.block.cts_date
            req_data.body["o3103InBlock"].cts_time = resp.block.cts_time

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> O3103Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3103Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[O3103Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3103Response]:
        def _updater(req_data, resp: O3103Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["o3103InBlock"].cts_date = resp.block.cts_date
            req_data.body["o3103InBlock"].cts_time = resp.block.cts_time

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrO3103,
    O3103InBlock,
    O3103OutBlock,
    O3103OutBlock1,
    O3103Request,
    O3103Response,
    O3103ResponseHeader,
]
