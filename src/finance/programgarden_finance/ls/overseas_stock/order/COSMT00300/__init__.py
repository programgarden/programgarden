from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from programgarden_core.logs import pg_logger
from .blocks import (
    COSMT00300InBlock1,
    COSMT00300OutBlock1,
    COSMT00300OutBlock2,
    COSMT00300Request,
    COSMT00300Response,
    COSMT00300ResponseHeader,
)
from ....tr_base import TROrderAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrCOSMT00300(TROrderAbstract):
    def __init__(self, request_data: COSMT00300Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSMT00300Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSMT00300Response] = GenericTR[COSMT00300Response](self.request_data, self._build_response, url=URLS.ORDER_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSMT00300Response:
        resp_json = resp_json or {}
        loan_code = resp_json.get("LoanDtlClssCode")
        block1_data = resp_json.get("COSMT00300OutBlock1")
        block2_data = resp_json.get("COSMT00300OutBlock2")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = COSMT00300ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        parsed_loan_code: Optional[str] = None
        if exc is None and not is_error_status:
            parsed_loan_code = loan_code
            if block1_data is not None:
                parsed_block1 = COSMT00300OutBlock1.model_validate(block1_data)
            if block2_data is not None:
                parsed_block2 = COSMT00300OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"COSMT00300 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"COSMT00300 request failed with status: {error_msg}")

        result = COSMT00300Response(
            header=header,
            LoanDtlClssCode=parsed_loan_code,
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

    def req(self) -> COSMT00300Response:
        return self._generic.req()

    async def req_async(self) -> COSMT00300Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> COSMT00300Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()


__all__ = [
    TrCOSMT00300,
    COSMT00300InBlock1,
    COSMT00300OutBlock1,
    COSMT00300OutBlock2,
    COSMT00300Request,
    COSMT00300Response,
    COSMT00300ResponseHeader,
]
