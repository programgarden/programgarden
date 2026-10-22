from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1488")
from .blocks import (
    T1488InBlock,
    T1488OutBlock,
    T1488OutBlock1,
    T1488Request,
    T1488Response,
    T1488ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1488(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1488 예상체결가등락율상위조회 클래스입니다.

    예상체결가 기준 상승/하락 등락률 상위 종목을 조회합니다.
    ``idx`` cursor 기반 연속조회를 지원합니다.
    """

    def __init__(self, request_data: T1488Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1488Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1488Response] = GenericTR[T1488Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1488Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1488OutBlock", None)
        block_data = resp_json.get("t1488OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1488ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1488OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1488OutBlock.model_validate(cont_data)

        parsed_block: list[T1488OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1488OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1488 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1488 request failed with status: {error_msg}")

        result = T1488Response(
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

    def req(self) -> T1488Response:
        return self._generic.req()

    async def req_async(self) -> T1488Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1488Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1488Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1488Response]:
        """동기 방식으로 예상체결가등락율상위 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1488Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1488 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1488InBlock"].idx = resp.cont_block.idx
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1488Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1488Response]:
        """비동기 방식으로 예상체결가등락율상위 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1488Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1488 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1488InBlock"].idx = resp.cont_block.idx
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1488,
    T1488InBlock,
    T1488OutBlock,
    T1488OutBlock1,
    T1488Request,
    T1488Response,
    T1488ResponseHeader,
]
