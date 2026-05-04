from typing import Optional, Dict, Any
import logging

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1640")
from .blocks import (
    T1640InBlock,
    T1640OutBlock,
    T1640Request,
    T1640Response,
    T1640ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1640(TRRequestAbstract):
    """LS Securities OpenAPI t1640 — Korean stock program-trading mini snapshot.

    Returns a single ``t1640OutBlock`` object containing buy / sell /
    net-buy quantity, amount, and day-over-day changes for the selected
    market + arbitrage combination (``T1640InBlock.gubun``), plus the
    basis (KP200 future vs spot) ratio.

    Unlike t1636 / t1637, this TR has **no IDXCTS / cursor continuation**
    — a single response covers the entire query.
    """

    def __init__(self, request_data: T1640Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1640Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1640Response] = GenericTR[T1640Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1640Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t1640OutBlock", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1640ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[T1640OutBlock] = None
        if exc is None and not is_error_status and block_data:
            parsed_block = T1640OutBlock.model_validate(block_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1640 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1640 request failed with status: {error_msg}")

        result = T1640Response(
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

    def req(self) -> T1640Response:
        return self._generic.req()

    async def req_async(self) -> T1640Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1640Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1640,
    T1640InBlock,
    T1640OutBlock,
    T1640Request,
    T1640Response,
    T1640ResponseHeader,
]
