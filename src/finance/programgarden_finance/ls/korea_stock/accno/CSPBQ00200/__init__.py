from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.CSPBQ00200")
from .blocks import (
    CSPBQ00200InBlock1,
    CSPBQ00200OutBlock1,
    CSPBQ00200OutBlock2,
    CSPBQ00200Request,
    CSPBQ00200Response,
    CSPBQ00200ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrCSPBQ00200(TRAccnoAbstract):
    """
    LS증권 OpenAPI CSPBQ00200 현물계좌 증거금률별 주문가능수량 조회 API용 클래스입니다.

    증거금률별 주문가능수량 및 주문가능금액을 조회합니다.
    """

    def __init__(
        self,
        request_data: CSPBQ00200Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CSPBQ00200Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CSPBQ00200Response] = GenericTR[CSPBQ00200Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CSPBQ00200Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CSPBQ00200OutBlock1", None)
        block2_data = resp_json.get("CSPBQ00200OutBlock2", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CSPBQ00200ResponseHeader.model_validate(resp_headers)

        parsed_block1: Optional[CSPBQ00200OutBlock1] = None
        parsed_block2: Optional[CSPBQ00200OutBlock2] = None
        if exc is None and not is_error_status:
            if block1_data:
                parsed_block1 = CSPBQ00200OutBlock1.model_validate(block1_data)
            if block2_data:
                parsed_block2 = CSPBQ00200OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"CSPBQ00200 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"CSPBQ00200 request failed with status: {error_msg}")

        result = CSPBQ00200Response(
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

    def req(self) -> CSPBQ00200Response:
        return self._generic.req()

    async def req_async(self) -> CSPBQ00200Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CSPBQ00200Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[CSPBQ00200Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[CSPBQ00200Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> CSPBQ00200Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCSPBQ00200,
    CSPBQ00200InBlock1,
    CSPBQ00200OutBlock1,
    CSPBQ00200OutBlock2,
    CSPBQ00200Request,
    CSPBQ00200Response,
    CSPBQ00200ResponseHeader,
]
