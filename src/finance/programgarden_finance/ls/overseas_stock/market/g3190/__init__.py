"""
LS증권 OpenAPI의 g3190 TR을 통한 해외주식 종목 정보 조회 모듈

이 모듈은 LS증권의 OpenAPI를 사용하여 해외주식의 종목 정보를 조회하는 기능을 제공합니다.

주요 기능:
- 해외주식 상장 종목들의 정보 조회
- 지정된 조건의 종목 데이터 조회
- 실시간 종목 정보 등의 데이터 제공
"""

from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    G3190InBlock,
    G3190OutBlock,
    G3190OutBlock1,
    G3190Request,
    G3190Response,
    G3190ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrG3190(TRRequestAbstract, OccursReqAbstract):
    def __init__(self, request_data: G3190Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3190Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[G3190Response] = GenericTR(self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3190Response:
        if exc is not None:
            return G3190Response(header=None, block=None, block1=[], rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block = resp_json.get("g3190OutBlock", None)
        result = G3190Response(
            header=G3190ResponseHeader.model_validate(resp_headers),
            block=G3190OutBlock.model_validate(block) if block is not None else None,
            block1=[G3190OutBlock1.model_validate(item) for item in resp_json.get("g3190OutBlock1", [])],
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> G3190Response:
        return self._generic.req()

    def occurs_req(self, callback: Optional[Callable[[Optional[G3190Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3190Response]:
        def _updater(req_data, resp: G3190Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3190InBlock"].cts_value = resp.block.cts_value

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> G3190Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3190Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[G3190Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3190Response]:
        def _updater(req_data, resp: G3190Response):
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3190InBlock"].cts_value = resp.block.cts_value

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrG3190,
    G3190InBlock,
    G3190OutBlock,
    G3190OutBlock1,
    G3190Request,
    G3190Response,
    G3190ResponseHeader,
]
