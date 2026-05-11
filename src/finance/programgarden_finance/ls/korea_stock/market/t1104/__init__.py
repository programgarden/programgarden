from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1104")
from .blocks import (
    T1104InBlock,
    T1104InBlock1,
    T1104OutBlock,
    T1104OutBlock1,
    T1104Request,
    T1104Response,
    T1104ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1104(TRRequestAbstract):
    """
    LS증권 OpenAPI t1104 주식현재가시세메모 클래스입니다.

    특정 종목에 대해 시세/최고저가/Pivot/이동평균선 메모를 항목별로 조회합니다.
    요청 시 ``t1104InBlock1`` (Object Array) 로 조회 디렉티브를 함께 전달하며,
    페이지네이션은 지원하지 않습니다.
    """

    def __init__(self, request_data: T1104Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1104Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1104Response] = GenericTR[T1104Response](
            self.request_data,
            self._build_response,
            url=URLS.KOREA_STOCK_MARKET_URL,
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1104Response:
        resp_json = resp_json or {}
        summary_data = resp_json.get("t1104OutBlock", None)
        block_data = resp_json.get("t1104OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1104ResponseHeader.model_validate(resp_headers)

        parsed_summary: Optional[T1104OutBlock] = None
        if exc is None and not is_error_status and summary_data:
            parsed_summary = T1104OutBlock.model_validate(summary_data)

        parsed_block: list[T1104OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1104OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1104 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1104 request failed with status: {error_msg}")

        result = T1104Response(
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

    def req(self) -> T1104Response:
        return self._generic.req()

    async def req_async(self) -> T1104Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1104Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1104,
    T1104InBlock,
    T1104InBlock1,
    T1104OutBlock,
    T1104OutBlock1,
    T1104Request,
    T1104Response,
    T1104ResponseHeader,
]
