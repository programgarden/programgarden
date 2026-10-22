from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1449")
from .blocks import (
    T1449InBlock,
    T1449OutBlock,
    T1449OutBlock1,
    T1449Request,
    T1449Response,
    T1449ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS


class TrT1449(TRRequestAbstract):
    """
    LS증권 OpenAPI t1449 가격대별매매비중조회 클래스입니다.

    특정 종목의 가격대별 매매비중(현재가 요약 + 가격대별 체결가/비중/매수비율)을
    조회합니다. LS spec 상 연속조회 cursor가 없는 단발성 TR이므로
    ``occurs_req`` 는 제공되지 않습니다.
    """

    def __init__(self, request_data: T1449Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1449Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1449Response] = GenericTR[T1449Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1449Response:
        resp_json = resp_json or {}
        out_data = resp_json.get("t1449OutBlock", None)
        block_data = resp_json.get("t1449OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1449ResponseHeader.model_validate(resp_headers)

        parsed_out: Optional[T1449OutBlock] = None
        if exc is None and not is_error_status and out_data:
            parsed_out = T1449OutBlock.model_validate(out_data)

        parsed_block: list[T1449OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1449OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1449 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1449 request failed with status: {error_msg}")

        result = T1449Response(
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

    def req(self) -> T1449Response:
        return self._generic.req()

    async def req_async(self) -> T1449Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1449Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()


__all__ = [
    TrT1449,
    T1449InBlock,
    T1449OutBlock,
    T1449OutBlock1,
    T1449Request,
    T1449Response,
    T1449ResponseHeader,
]
