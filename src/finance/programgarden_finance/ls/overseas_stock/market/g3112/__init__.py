"""
LS증권 OpenAPI g3112 해외주식API시세순위 (overseas stock quote ranking) module.

Ranks overseas stock issues by one quote metric (change rate, volume,
trading value, turnover, market capitalisation, 52-week high/low, limit
prices) for one country and exchange segment. Pages continue with
``cts_value``. The LS guide allows 1 transaction per second.
"""

from typing import Callable, Optional, Dict, Any

import aiohttp

import logging

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    G3112InBlock,
    G3112OutBlock,
    G3112OutBlock1,
    G3112Request,
    G3112Response,
    G3112ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus

logger = logging.getLogger("programgarden.ls.overseas_stock.market.g3112")


class TrG3112(TRRequestAbstract, OccursReqAbstract):
    def __init__(self, request_data: G3112Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3112Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[G3112Response] = GenericTR[G3112Response](self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3112Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("g3112OutBlock")
        block1_data = resp_json.get("g3112OutBlock1") or []

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = G3112ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        parsed_block1: list[G3112OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = G3112OutBlock.model_validate(block_data)
            parsed_block1 = [G3112OutBlock1.model_validate(item) for item in block1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"g3112 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"g3112 request failed with status: {error_msg}")

        result = G3112Response(
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

    def req(self) -> G3112Response:
        return self._generic.req()

    def occurs_req(self, callback: Optional[Callable[[Optional[G3112Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3112Response]:
        def _updater(req_data, resp: G3112Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3112 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3112InBlock"].cts_value = resp.block.cts_value

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> G3112Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3112Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[G3112Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3112Response]:
        def _updater(req_data, resp: G3112Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3112 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3112InBlock"].cts_value = resp.block.cts_value

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrG3112,
    G3112InBlock,
    G3112OutBlock,
    G3112OutBlock1,
    G3112Request,
    G3112Response,
    G3112ResponseHeader,
]
