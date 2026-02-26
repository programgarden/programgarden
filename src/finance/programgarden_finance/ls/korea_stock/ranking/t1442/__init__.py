from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.ranking.t1442")
from .blocks import (
    T1442InBlock,
    T1442OutBlock,
    T1442OutBlock1,
    T1442Request,
    T1442Response,
    T1442ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1442(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1442 신고/신저가 클래스입니다.

    기간별 신고가/신저가 종목을 조회합니다.
    idx 기반 연속조회를 지원합니다.
    """

    def __init__(self, request_data: T1442Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1442Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1442Response] = GenericTR[T1442Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_HIGH_ITEM_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1442Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1442OutBlock", None)
        block_data = resp_json.get("t1442OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1442ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1442OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1442OutBlock.model_validate(cont_data)

        parsed_block: list[T1442OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1442OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1442 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1442 request failed with status: {error_msg}")

        result = T1442Response(
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

    def req(self) -> T1442Response:
        return self._generic.req()

    async def req_async(self) -> T1442Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1442Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1442Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1442Response]:
        """동기 방식으로 신고/신저가 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1442Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1442 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1442InBlock"].idx = resp.cont_block.idx
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1442Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1442Response]:
        """비동기 방식으로 신고/신저가 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1442Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1442 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1442InBlock"].idx = resp.cont_block.idx
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1442,
    T1442InBlock,
    T1442OutBlock,
    T1442OutBlock1,
    T1442Request,
    T1442Response,
    T1442ResponseHeader,
]
