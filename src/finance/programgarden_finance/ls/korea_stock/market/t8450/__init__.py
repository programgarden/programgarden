from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t8450")
from .blocks import (
    T8450InBlock,
    T8450OutBlock,
    T8450Request,
    T8450Response,
    T8450ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8450(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 t8450 주식현재가호가조회2 API용 클래스입니다.
    """

    def __init__(
        self,
        request_data: T8450Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T8450Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T8450Response] = GenericTR[T8450Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8450Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t8450OutBlock", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8450ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[T8450OutBlock] = None
        if exc is None and not is_error_status and block_data:
            parsed_block = T8450OutBlock.model_validate(block_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8450 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8450 request failed with status: {error_msg}")

        result = T8450Response(
            header=header,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8450Response:
        return self._generic.req()

    async def req_async(self) -> T8450Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8450Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[T8450Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[T8450Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> T8450Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrT8450,
    T8450InBlock,
    T8450OutBlock,
    T8450Request,
    T8450Response,
    T8450ResponseHeader,
]
