from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.investor.t1621")
from .blocks import (
    T1621InBlock,
    T1621OutBlock,
    T1621OutBlock1,
    T1621Request,
    T1621Response,
    T1621ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1621(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI t1621 업종별분별투자자매매동향 클래스입니다.

    업종코드 기준으로 12개 투자자 유형의 분별/일별 순매수 거래량 및 거래대금을 조회합니다.
    기준지수 정보도 함께 제공됩니다.
    """

    def __init__(self, request_data: T1621Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1621Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1621Response] = GenericTR[T1621Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_INVESTOR_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1621Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1621OutBlock", None)
        block_data = resp_json.get("t1621OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1621ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1621OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1621OutBlock.model_validate(cont_data)

        parsed_block: list[T1621OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1621OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1621 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1621 request failed with status: {error_msg}")

        result = T1621Response(
            header=header,
            cont_block=parsed_cont,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1621Response:
        return self._generic.req()

    async def req_async(self) -> T1621Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1621Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[T1621Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[T1621Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> T1621Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [TrT1621, T1621InBlock, T1621OutBlock, T1621OutBlock1, T1621Request, T1621Response, T1621ResponseHeader]
