from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from programgarden_core.logs import pg_logger
from .blocks import (
    COSAT00311InBlock1,
    COSAT00311OutBlock1,
    COSAT00311OutBlock2,
    COSAT00311Request,
    COSAT00311Response,
    COSAT00311ResponseHeader,
)
from ....tr_base import TROrderAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrCOSAT00311(TROrderAbstract):
    def __init__(self, request_data: COSAT00311Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSAT00311Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSAT00311Response] = GenericTR[COSAT00311Response](self.request_data, self._build_response, url=URLS.ORDER_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSAT00311Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("COSAT00311OutBlock1")
        block2_data = resp_json.get("COSAT00311OutBlock2")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = COSAT00311ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        if exc is None and not is_error_status:
            if block1_data is not None:
                parsed_block1 = COSAT00311OutBlock1.model_validate(block1_data)
            if block2_data is not None:
                parsed_block2 = COSAT00311OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"COSAT00311 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"COSAT00311 request failed with status: {error_msg}")

        result = COSAT00311Response(
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

    def req(self) -> COSAT00311Response:
        return self._generic.req()

    async def req_async(self) -> COSAT00311Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> COSAT00311Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()


__all__ = [
    TrCOSAT00311,
    COSAT00311InBlock1,
    COSAT00311OutBlock1,
    COSAT00311OutBlock2,
    COSAT00311Request,
    COSAT00311Response,
    COSAT00311ResponseHeader,
]
