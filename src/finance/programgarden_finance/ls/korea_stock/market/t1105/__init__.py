from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1105")
from .blocks import (
    T1105InBlock,
    T1105OutBlock,
    T1105Request,
    T1105Response,
    T1105ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1105(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI t1105 주식피봇/디마크조회 API용 클래스입니다.

    특정 종목의 피봇(pbot), 1/2차 저항/지지(offer1/2, supp1/2), 기준가격(stdprc),
    Demark 저항/지지(offerd, suppd)를 단발 조회합니다. LS spec 상 연속조회
    cursor 가 없는 단발성 TR 이므로 ``occurs_req`` 는 제공되지 않습니다.
    """

    def __init__(
        self,
        request_data: T1105Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T1105Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T1105Response] = GenericTR[T1105Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1105Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t1105OutBlock", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1105ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[T1105OutBlock] = None
        if exc is None and not is_error_status and block_data:
            parsed_block = T1105OutBlock.model_validate(block_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1105 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1105 request failed with status: {error_msg}")

        result = T1105Response(
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

    def req(self) -> T1105Response:
        return self._generic.req()

    async def req_async(self) -> T1105Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1105Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[T1105Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[T1105Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> T1105Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrT1105,
    T1105InBlock,
    T1105OutBlock,
    T1105Request,
    T1105Response,
    T1105ResponseHeader,
]
