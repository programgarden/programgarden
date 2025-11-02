from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    CIDBQ05300InBlock1,
    CIDBQ05300OutBlock1,
    CIDBQ05300OutBlock2,
    CIDBQ05300OutBlock3,
    CIDBQ05300Request,
    CIDBQ05300Response,
    CIDBQ05300ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCIDBQ05300(TRAccnoAbstract):
    def __init__(self, request_data: CIDBQ05300Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBQ05300Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CIDBQ05300Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBQ05300Response:
        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBQ05300OutBlock1", None)
        block2 = resp_json.get("CIDBQ05300OutBlock2", [])
        block3 = resp_json.get("CIDBQ05300OutBlock3", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CIDBQ05300ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = []
        parsed_block3 = None
        if exc is None and not is_error_status:
            if block1 is not None:
                parsed_block1 = CIDBQ05300OutBlock1.model_validate(block1)
            parsed_block2 = [CIDBQ05300OutBlock2.model_validate(item) for item in block2]
            if block3 is not None:
                parsed_block3 = CIDBQ05300OutBlock3.model_validate(block3)

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"

        result = CIDBQ05300Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            block3=parsed_block3,
            status_code=status,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            error_msg=error_msg,
        )
        result.raw_data = resp
        return result

    def req(self) -> CIDBQ05300Response:
        return self._generic.req()

    async def req_async(self) -> CIDBQ05300Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBQ05300Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[CIDBQ05300Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[CIDBQ05300Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> CIDBQ05300Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCIDBQ05300,
    CIDBQ05300InBlock1,
    CIDBQ05300OutBlock1,
    CIDBQ05300OutBlock2,
    CIDBQ05300OutBlock3,
    CIDBQ05300Request,
    CIDBQ05300Response,
    CIDBQ05300ResponseHeader,
]
