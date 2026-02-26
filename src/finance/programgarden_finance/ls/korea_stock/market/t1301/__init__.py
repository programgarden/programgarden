from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1301")
from .blocks import (
    T1301InBlock,
    T1301OutBlock,
    T1301OutBlock1,
    T1301Request,
    T1301Response,
    T1301ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1301(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1301 주식시간대별체결조회 클래스입니다.

    특정 종목의 시간대별 체결 내역을 조회합니다.
    cts_time 기반 연속조회를 지원합니다.
    """

    def __init__(self, request_data: T1301Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1301Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1301Response] = GenericTR[T1301Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1301Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1301OutBlock", None)
        block_data = resp_json.get("t1301OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1301ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1301OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1301OutBlock.model_validate(cont_data)

        parsed_block: list[T1301OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1301OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1301 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1301 request failed with status: {error_msg}")

        result = T1301Response(
            header=header,
            cont_block=parsed_cont,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1301Response:
        return self._generic.req()

    async def req_async(self) -> T1301Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1301Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1301Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1301Response]:
        """동기 방식으로 주식시간대별체결 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1301Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1301 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1301InBlock"].cts_time = resp.cont_block.cts_time
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1301Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1301Response]:
        """비동기 방식으로 주식시간대별체결 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1301Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1301 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1301InBlock"].cts_time = resp.cont_block.cts_time
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1301,
    T1301InBlock,
    T1301OutBlock,
    T1301OutBlock1,
    T1301Request,
    T1301Response,
    T1301ResponseHeader,
]
