from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.order.CSPAT00601")
from .blocks import (
    CSPAT00601InBlock1,
    CSPAT00601OutBlock1,
    CSPAT00601OutBlock2,
    CSPAT00601Request,
    CSPAT00601Response,
    CSPAT00601ResponseHeader,
)
from ....tr_base import TROrderAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrCSPAT00601(TROrderAbstract):
    """
    LS증권 OpenAPI CSPAT00601 현물주문 API용 클래스입니다.

    국내주식 현물 매수/매도 주문을 요청합니다.
    정정주문은 TrCSPAT00701을 사용하세요.
    """

    def __init__(
        self,
        request_data: CSPAT00601Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CSPAT00601Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CSPAT00601Response] = GenericTR[CSPAT00601Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_ORDER_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CSPAT00601Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CSPAT00601OutBlock1", None)
        block2_data = resp_json.get("CSPAT00601OutBlock2", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CSPAT00601ResponseHeader.model_validate(resp_headers)

        parsed_block1: Optional[CSPAT00601OutBlock1] = None
        parsed_block2: Optional[CSPAT00601OutBlock2] = None
        if exc is None and not is_error_status:
            if block1_data:
                parsed_block1 = CSPAT00601OutBlock1.model_validate(block1_data)
            if block2_data:
                parsed_block2 = CSPAT00601OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"CSPAT00601 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"CSPAT00601 request failed with status: {error_msg}")

        result = CSPAT00601Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> CSPAT00601Response:
        return self._generic.req()

    async def req_async(self) -> CSPAT00601Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CSPAT00601Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()


__all__ = [
    TrCSPAT00601,
    CSPAT00601InBlock1,
    CSPAT00601OutBlock1,
    CSPAT00601OutBlock2,
    CSPAT00601Request,
    CSPAT00601Response,
    CSPAT00601ResponseHeader,
]
