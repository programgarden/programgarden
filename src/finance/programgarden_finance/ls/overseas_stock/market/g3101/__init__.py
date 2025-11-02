from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from programgarden_core.logs import pg_logger
from .blocks import (
    G3101InBlock,
    G3101OutBlock,
    G3101Request,
    G3101Response,
    G3101ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrG3101(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 g3101 시세 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: G3101Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3101Request):
            raise TrRequestDataNotFoundException()

        # generic helper delegates HTTP/serialization
        self._generic: GenericTR[G3101Response] = GenericTR[G3101Response](self.request_data, self._build_response, url=URLS.MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3101Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("g3101OutBlock")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = G3101ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        if exc is None and not is_error_status and block_data is not None:
            parsed_block = G3101OutBlock.model_validate(block_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"g3101 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"g3101 request failed with status: {error_msg}")

        result = G3101Response(
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

    def req(self) -> G3101Response:
        return self._generic.req()

    async def req_async(self) -> G3101Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3101Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[G3101Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[G3101Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> G3101Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrG3101,
    G3101InBlock,
    G3101OutBlock,
    G3101Request,
    G3101Response,
    G3101ResponseHeader,
]
