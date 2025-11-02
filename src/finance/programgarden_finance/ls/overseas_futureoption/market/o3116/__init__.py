"""
o3116 TR: 해외선물 시간대별(Tick)체결 조회

This module provides sync and async request helpers for the o3116 TR using
the block models defined in blocks.py.
"""

from typing import Callable, Optional, Dict, Any
import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3116InBlock,
    O3116OutBlock,
    O3116OutBlock1,
    O3116Request,
    O3116Response,
    O3116ResponseHeader,
)
from ....tr_base import TRRequestAbstract, OccursReqAbstract
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus

from programgarden_core.logs import pg_logger


class TrO3116(TRRequestAbstract, OccursReqAbstract):
    """o3116 TR helper class"""

    def __init__(
        self,
        request_data: O3116Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3116Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3116Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3116Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("o3116OutBlock", None)
        block1_data = resp_json.get("o3116OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3116ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[O3116OutBlock] = None
        parsed_block1: list[O3116OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = O3116OutBlock.model_validate(block_data)
            parsed_block1 = [O3116OutBlock1.model_validate(item) for item in block1_data]

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"o3116 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"o3116 request failed with status: {error_msg}")

        result = O3116Response(
            header=header,
            block=parsed_block,
            block1=parsed_block1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> O3116Response:
        return self._generic.req()

    async def req_async(self) -> O3116Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3116Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[O3116Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3116Response]:
        def _updater(req_data: O3116Request, resp: O3116Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            if resp.block is not None:
                req_data.body["o3116InBlock"].cts_seq = resp.block.cts_seq

        return self._generic.occurs_req(updater=_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[O3116Response], RequestStatus], None]] = None, delay: int = 1) -> list[O3116Response]:
        def _updater(req_data: O3116Request, resp: O3116Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            if resp.block is not None:
                req_data.body["o3116InBlock"].cts_seq = resp.block.cts_seq

        return await self._generic.occurs_req_async(_updater, callback, delay)


__all__ = [
    TrO3116,
    O3116InBlock,
    O3116OutBlock,
    O3116OutBlock1,
    O3116Request,
    O3116Response,
    O3116ResponseHeader,
]
