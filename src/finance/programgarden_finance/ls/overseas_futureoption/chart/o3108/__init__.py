from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3108InBlock,
    O3108OutBlock,
    O3108OutBlock1,
    O3108Request,
    O3108Response,
    O3108ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrO3108(TRRequestAbstract, OccursReqAbstract):
    def __init__(self, request_data: O3108Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3108Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3108Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3108Response:
        resp_json = resp_json or {}
        block = resp_json.get("o3108OutBlock", None)
        block1 = resp_json.get("o3108OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3108ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        parsed_block1 = []
        if exc is None and not is_error_status:
            if block is not None:
                parsed_block = O3108OutBlock.model_validate(block)
            parsed_block1 = [O3108OutBlock1.model_validate(item) for item in block1]

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"

        result = O3108Response(
            header=header,
            block=parsed_block,
            block1=parsed_block1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        result.raw_data = resp
        return result

    def req(self) -> O3108Response:
        return self._generic.req()

    def occurs_req(self, callback: Optional[Callable[[Optional[O3108Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3108Response]:
        def _updater(req_data, resp: O3108Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["o3108InBlock"].cts_date = resp.block.cts_date

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> O3108Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3108Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[O3108Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3108Response]:
        def _updater(req_data, resp: O3108Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["o3108InBlock"].cts_date = resp.block.cts_date

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrO3108,
    O3108InBlock,
    O3108OutBlock,
    O3108OutBlock1,
    O3108Request,
    O3108Response,
    O3108ResponseHeader,
]
