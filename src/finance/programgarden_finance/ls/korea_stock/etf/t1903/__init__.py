from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.etf.t1903")
from .blocks import (
    T1903InBlock,
    T1903OutBlock,
    T1903OutBlock1,
    T1903Request,
    T1903Response,
    T1903ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1903(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1903 ETF일별추이 클래스입니다.
    """

    def __init__(self, request_data: T1903Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1903Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1903Response] = GenericTR[T1903Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_ETF_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1903Response:
        resp_json = resp_json or {}
        t1903OutBlock_data = resp_json.get("t1903OutBlock", None)
        t1903OutBlock1_data = resp_json.get("t1903OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1903ResponseHeader.model_validate(resp_headers)

        parsed_t1903OutBlock: Optional[T1903OutBlock] = None
        if exc is None and not is_error_status and t1903OutBlock_data:
            parsed_t1903OutBlock = T1903OutBlock.model_validate(t1903OutBlock_data)

        parsed_t1903OutBlock1: list[T1903OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t1903OutBlock1 = [T1903OutBlock1.model_validate(item) for item in t1903OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1903 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1903 request failed with status: {error_msg}")

        result = T1903Response(
            header=header,
            cont_block=parsed_t1903OutBlock,
            block=parsed_t1903OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1903Response:
        return self._generic.req()

    async def req_async(self) -> T1903Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1903Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1903Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1903Response]:
        """동기 방식으로 ETF일별추이 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1903Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1903 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1903InBlock"].date = resp.cont_block.date
            req_data.body["t1903InBlock"].hname = resp.cont_block.hname
            req_data.body["t1903InBlock"].upname = resp.cont_block.upname
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1903Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1903Response]:
        """비동기 방식으로 ETF일별추이 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1903Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1903 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1903InBlock"].date = resp.cont_block.date
            req_data.body["t1903InBlock"].hname = resp.cont_block.hname
            req_data.body["t1903InBlock"].upname = resp.cont_block.upname
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1903,
    T1903InBlock,
    T1903OutBlock,
    T1903OutBlock1,
    T1903Request,
    T1903Response,
    T1903ResponseHeader,
]
