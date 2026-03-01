from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t8454")
from .blocks import (
    T8454InBlock,
    T8454OutBlock,
    T8454OutBlock1,
    T8454Request,
    T8454Response,
    T8454ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8454(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t8454 (통합)주식시간대별체결2 API용 클래스입니다.
    """

    def __init__(self, request_data: T8454Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T8454Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T8454Response] = GenericTR[T8454Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8454Response:
        resp_json = resp_json or {}
        t8454OutBlock_data = resp_json.get("t8454OutBlock", None)
        t8454OutBlock1_data = resp_json.get("t8454OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8454ResponseHeader.model_validate(resp_headers)

        parsed_t8454OutBlock: Optional[T8454OutBlock] = None
        if exc is None and not is_error_status and t8454OutBlock_data:
            parsed_t8454OutBlock = T8454OutBlock.model_validate(t8454OutBlock_data)

        parsed_t8454OutBlock1: list[T8454OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t8454OutBlock1 = [T8454OutBlock1.model_validate(item) for item in t8454OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8454 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8454 request failed with status: {error_msg}")

        result = T8454Response(
            header=header,
            cont_block=parsed_t8454OutBlock,
            block=parsed_t8454OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8454Response:
        return self._generic.req()

    async def req_async(self) -> T8454Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8454Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T8454Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8454Response]:
        """동기 방식으로 (통합)주식시간대별체결2 API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8454Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8454 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8454InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8454InBlock"].ex_shcode = resp.cont_block.ex_shcode
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T8454Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8454Response]:
        """비동기 방식으로 (통합)주식시간대별체결2 API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8454Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8454 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8454InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8454InBlock"].ex_shcode = resp.cont_block.ex_shcode
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT8454,
    T8454InBlock,
    T8454OutBlock,
    T8454OutBlock1,
    T8454Request,
    T8454Response,
    T8454ResponseHeader,
]
