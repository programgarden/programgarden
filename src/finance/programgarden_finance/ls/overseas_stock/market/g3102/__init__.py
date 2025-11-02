"""
LS증권 OpenAPI의 g3102 TR을 통한 해외주식 시간대별 데이터 조회 모듈

이 모듈은 LS증권의 OpenAPI를 사용하여 해외주식의 시간대별 데이터를 조회하는 기능을 제공합니다.

주요 기능:
- 해외주식의 시간대별 체결 데이터 조회
- 지정된 시간 범위의 체결 데이터 조회
- 실시간 체결가, 거래량 등의 데이터 제공
"""

from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from programgarden_core.logs import pg_logger
from .blocks import (
    G3102InBlock,
    G3102OutBlock,
    G3102OutBlock1,
    G3102Request,
    G3102Response,
    G3102ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrG3102(TRRequestAbstract, OccursReqAbstract):
    def __init__(self, request_data: G3102Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3102Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[G3102Response] = GenericTR[G3102Response](self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3102Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("g3102OutBlock")
        block1_data = resp_json.get("g3102OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = G3102ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        parsed_block1: list[G3102OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = G3102OutBlock.model_validate(block_data)
            parsed_block1 = [G3102OutBlock1.model_validate(item) for item in block1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"g3102 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"g3102 request failed with status: {error_msg}")

        result = G3102Response(
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

    def req(self) -> G3102Response:
        return self._generic.req()

    def occurs_req(self, callback: Optional[Callable[[Optional[G3102Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3102Response]:
        def _updater(req_data, resp: G3102Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3102 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3102InBlock"].cts_seq = resp.block.cts_seq

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> G3102Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3102Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[G3102Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3102Response]:
        def _updater(req_data, resp: G3102Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3102 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3102InBlock"].cts_seq = resp.block.cts_seq

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrG3102,
    G3102InBlock,
    G3102OutBlock,
    G3102OutBlock1,
    G3102Request,
    G3102Response,
    G3102ResponseHeader,
]
