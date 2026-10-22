from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1631")
from .blocks import (
    T1631InBlock,
    T1631OutBlock,
    T1631OutBlock1,
    T1631Request,
    T1631Response,
    T1631ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1631(TRRequestAbstract):
    """LS Securities OpenAPI t1631 — Korean stock program trading comprehensive query.

    Returns Korean stock program trading data:

    - ``T1631Response.summary_block`` — eight scalar aggregates from the
      (sell vs buy) × (arbitrage vs non-arbitrage) × (unfilled-remaining
      vs ordered) breakdown documented in the LS spec.
    - ``T1631Response.block`` — Object Array of buy / sell / net quantity
      and amount per row as reported by LS. Row meaning and array
      ordering are not documented in the LS public spec.

    Unlike t1636, this TR has **no IDXCTS continuation** — a single response
    covers either the same-day query (``dgubun='1'``) or the period query
    (``dgubun='2'``) over ``[sdate, edate]``. Therefore this class
    intentionally does **not** inherit ``OccursReqAbstract``.
    """

    def __init__(self, request_data: T1631Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1631Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1631Response] = GenericTR[T1631Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1631Response:
        resp_json = resp_json or {}
        summary_data = resp_json.get("t1631OutBlock", None)
        block_data = resp_json.get("t1631OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1631ResponseHeader.model_validate(resp_headers)

        parsed_summary: Optional[T1631OutBlock] = None
        if exc is None and not is_error_status and summary_data:
            parsed_summary = T1631OutBlock.model_validate(summary_data)

        parsed_block: list[T1631OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1631OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1631 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1631 request failed with status: {error_msg}")

        result = T1631Response(
            header=header,
            summary_block=parsed_summary,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1631Response:
        return self._generic.req()

    async def req_async(self) -> T1631Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1631Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1631,
    T1631InBlock,
    T1631OutBlock,
    T1631OutBlock1,
    T1631Request,
    T1631Response,
    T1631ResponseHeader,
]
