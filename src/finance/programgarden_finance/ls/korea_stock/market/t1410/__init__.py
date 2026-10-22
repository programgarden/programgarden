from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1410")
from .blocks import (
    T1410InBlock,
    T1410OutBlock,
    T1410OutBlock1,
    T1410Request,
    T1410Response,
    T1410ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1410(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1410 초저유동성조회 클래스입니다.

    시장구분(전체/코스피/코스닥)별 초저유동성 종목(한글명, 현재가, 전일대비,
    등락률, 누적거래량, 종목코드)을 조회합니다.
    ``cts_shcode`` cursor 기반 연속조회를 지원합니다.
    """

    def __init__(self, request_data: T1410Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1410Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1410Response] = GenericTR[T1410Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1410Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1410OutBlock", None)
        block_data = resp_json.get("t1410OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1410ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1410OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1410OutBlock.model_validate(cont_data)

        parsed_block: list[T1410OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1410OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1410 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1410 request failed with status: {error_msg}")

        result = T1410Response(
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

    def req(self) -> T1410Response:
        return self._generic.req()

    async def req_async(self) -> T1410Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1410Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1410Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1410Response]:
        """동기 방식으로 초저유동성 종목 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1410Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1410 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1410InBlock"].cts_shcode = resp.cont_block.cts_shcode
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1410Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1410Response]:
        """비동기 방식으로 초저유동성 종목 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1410Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1410 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1410InBlock"].cts_shcode = resp.cont_block.cts_shcode
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1410,
    T1410InBlock,
    T1410OutBlock,
    T1410OutBlock1,
    T1410Request,
    T1410Response,
    T1410ResponseHeader,
]
