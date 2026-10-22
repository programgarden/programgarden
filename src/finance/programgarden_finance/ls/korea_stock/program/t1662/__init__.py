from typing import Optional, Dict, Any, List
import logging

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1662")
from .blocks import (
    T1662InBlock,
    T1662OutBlock,
    T1662Request,
    T1662Response,
    T1662ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1662(TRRequestAbstract):
    """LS Securities OpenAPI t1662 — time-chart program-trading query.

    Returns an Object Array of time-bucketed KP200 / BASIS / sign / change /
    program-trading flow rows for KOSPI (``gubun='0'``) or KOSDAQ
    (``gubun='1'``).

    Despite the LS REST header declaring ``tr_cont`` / ``tr_cont_key``, the
    LS body has no cursor field — a single response covers the entire chart.
    Inherits ``TRRequestAbstract`` only (no ``OccursReqAbstract``); ``occurs_req``
    is intentionally not provided.
    """

    def __init__(self, request_data: T1662Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1662Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1662Response] = GenericTR[T1662Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1662Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t1662OutBlock", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1662ResponseHeader.model_validate(resp_headers)

        parsed_block: List[T1662OutBlock] = []
        if exc is None and not is_error_status and block_data:
            parsed_block = [T1662OutBlock.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1662 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1662 request failed with status: {error_msg}")

        result = T1662Response(
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

    def req(self) -> T1662Response:
        return self._generic.req()

    async def req_async(self) -> T1662Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1662Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1662,
    T1662InBlock,
    T1662OutBlock,
    T1662Request,
    T1662Response,
    T1662ResponseHeader,
]
