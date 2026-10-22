from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.sector.t1537")
from .blocks import (
    T1537InBlock,
    T1537OutBlock,
    T1537OutBlock1,
    T1537Request,
    T1537Response,
    T1537ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1537(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI t1537 테마종목별시세조회 클래스입니다.

    테마코드로 해당 테마에 속한 종목들의 시세(현재가, 등락률, 거래량, 시가총액 등)를 조회합니다.
    """

    def __init__(self, request_data: T1537Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1537Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1537Response] = GenericTR[T1537Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_SECTOR_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1537Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1537OutBlock", None)
        block_data = resp_json.get("t1537OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1537ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1537OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1537OutBlock.model_validate(cont_data)

        parsed_block: list[T1537OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1537OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1537 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1537 request failed with status: {error_msg}")

        result = T1537Response(
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

    def req(self) -> T1537Response:
        return self._generic.req()

    async def req_async(self) -> T1537Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1537Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[T1537Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[T1537Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> T1537Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [TrT1537, T1537InBlock, T1537OutBlock, T1537OutBlock1, T1537Request, T1537Response, T1537ResponseHeader]
