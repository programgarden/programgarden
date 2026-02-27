from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.investor.t1601")
from .blocks import (
    T1601InBlock,
    T1601InvestorBlock,
    T1601Request,
    T1601Response,
    T1601ResponseHeader,
)
from ....tr_base import RetryReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1601(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI t1601 투자자별종합 클래스입니다.

    코스피/코스닥/선물/콜옵션/풋옵션/ELW 시장별로
    12개 투자자 유형(개인, 외국인, 기관계 등)의 매수/매도/순매수 데이터를 조회합니다.
    """

    def __init__(self, request_data: T1601Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1601Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1601Response] = GenericTR[T1601Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_INVESTOR_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1601Response:
        resp_json = resp_json or {}

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1601ResponseHeader.model_validate(resp_headers)

        blocks = {}
        if exc is None and not is_error_status:
            for i in range(1, 7):
                key = f"t1601OutBlock{i}"
                data = resp_json.get(key, None)
                if data:
                    blocks[f"block{i}"] = T1601InvestorBlock.model_validate(data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1601 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1601 request failed with status: {error_msg}")

        result = T1601Response(
            header=header,
            **blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1601Response:
        return self._generic.req()

    async def req_async(self) -> T1601Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1601Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[T1601Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[T1601Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> T1601Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [TrT1601, T1601InBlock, T1601InvestorBlock, T1601Request, T1601Response, T1601ResponseHeader]
