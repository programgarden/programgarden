from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1308")
from .blocks import (
    T1308InBlock,
    T1308OutBlock,
    T1308OutBlock1,
    T1308Request,
    T1308Response,
    T1308ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1308(TRRequestAbstract):
    """
    LS증권 OpenAPI t1308 주식시간대별체결조회챠트 클래스입니다.

    특정 종목의 시간대별 봉 데이터(체결시간, 현재가, 전일대비, 등락률,
    체결강도(거래량/건수), 거래량, 매도/매수 체결수량+건수, 시고저)를 조회합니다.
    LS spec 상 연속조회 cursor가 없는 단발성 TR이므로
    ``occurs_req`` 는 제공되지 않습니다.
    """

    def __init__(self, request_data: T1308Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1308Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1308Response] = GenericTR[T1308Response](
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
    ) -> T1308Response:
        resp_json = resp_json or {}
        out_data = resp_json.get("t1308OutBlock", None)
        block_data = resp_json.get("t1308OutBlock1", [])

        status = (
            getattr(resp, "status", getattr(resp, "status_code", None))
            if resp is not None
            else None
        )
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1308ResponseHeader.model_validate(resp_headers)

        parsed_out: Optional[T1308OutBlock] = None
        if exc is None and not is_error_status and out_data:
            parsed_out = T1308OutBlock.model_validate(out_data)

        parsed_block: list[T1308OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1308OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1308 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1308 request failed with status: {error_msg}")

        result = T1308Response(
            header=header,
            out_block=parsed_out,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1308Response:
        return self._generic.req()

    async def req_async(self) -> T1308Response:
        return await self._generic.req_async()

    async def _req_async_with_session(
        self, session: aiohttp.ClientSession
    ) -> T1308Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1308,
    T1308InBlock,
    T1308OutBlock,
    T1308OutBlock1,
    T1308Request,
    T1308Response,
    T1308ResponseHeader,
]
