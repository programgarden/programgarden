from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.etc.t1638")
from .blocks import (
    T1638InBlock,
    T1638OutBlock,
    T1638Request,
    T1638Response,
    T1638ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1638(TRRequestAbstract):
    """
    LS증권 OpenAPI t1638 종목별잔량/사전공시 클래스입니다.
    """

    def __init__(self, request_data: T1638Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1638Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1638Response] = GenericTR[T1638Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_ETC_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1638Response:
        resp_json = resp_json or {}
        t1638OutBlock_data = resp_json.get("t1638OutBlock", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1638ResponseHeader.model_validate(resp_headers)

        parsed_t1638OutBlock: list[T1638OutBlock] = []
        if exc is None and not is_error_status:
            parsed_t1638OutBlock = [T1638OutBlock.model_validate(item) for item in t1638OutBlock_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1638 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1638 request failed with status: {error_msg}")

        result = T1638Response(
            header=header,
            block=parsed_t1638OutBlock,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1638Response:
        return self._generic.req()

    async def req_async(self) -> T1638Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1638Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1638,
    T1638InBlock,
    T1638OutBlock,
    T1638Request,
    T1638Response,
    T1638ResponseHeader,
]
