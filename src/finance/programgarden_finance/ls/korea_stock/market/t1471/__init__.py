from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1471")
from .blocks import (
    T1471InBlock,
    T1471OutBlock,
    T1471OutBlock1,
    T1471Request,
    T1471Response,
    T1471ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1471(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1471 시간대별호가잔량추이 클래스입니다.

    특정 종목의 시간대별 호가잔량 추이를 조회합니다.
    time 기반 연속조회를 지원합니다.
    """

    def __init__(self, request_data: T1471Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1471Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1471Response] = GenericTR[T1471Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1471Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1471OutBlock", None)
        block_data = resp_json.get("t1471OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1471ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1471OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1471OutBlock.model_validate(cont_data)

        parsed_block: list[T1471OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1471OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1471 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1471 request failed with status: {error_msg}")

        result = T1471Response(
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

    def req(self) -> T1471Response:
        return self._generic.req()

    async def req_async(self) -> T1471Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1471Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1471Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1471Response]:
        """동기 방식으로 시간대별호가잔량추이 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1471Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1471 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1471InBlock"].time = resp.cont_block.time
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1471Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1471Response]:
        """비동기 방식으로 시간대별호가잔량추이 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1471Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1471 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1471InBlock"].time = resp.cont_block.time
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1471,
    T1471InBlock,
    T1471OutBlock,
    T1471OutBlock1,
    T1471Request,
    T1471Response,
    T1471ResponseHeader,
]
