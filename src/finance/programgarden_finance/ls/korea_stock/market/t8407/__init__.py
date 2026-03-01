from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t8407")
from .blocks import (
    T8407InBlock,
    T8407OutBlock1,
    T8407Request,
    T8407Response,
    T8407ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT8407(TRRequestAbstract):
    """
    LS증권 OpenAPI t8407 API용주식멀티현재가조회 클래스입니다.
    """

    def __init__(self, request_data: T8407Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T8407Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T8407Response] = GenericTR[T8407Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8407Response:
        resp_json = resp_json or {}
        t8407OutBlock1_data = resp_json.get("t8407OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8407ResponseHeader.model_validate(resp_headers)

        parsed_t8407OutBlock1: list[T8407OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t8407OutBlock1 = [T8407OutBlock1.model_validate(item) for item in t8407OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8407 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8407 request failed with status: {error_msg}")

        result = T8407Response(
            header=header,
            block=parsed_t8407OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8407Response:
        return self._generic.req()

    async def req_async(self) -> T8407Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8407Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT8407,
    T8407InBlock,
    T8407OutBlock1,
    T8407Request,
    T8407Response,
    T8407ResponseHeader,
]
