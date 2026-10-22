from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1636")
from .blocks import (
    T1636InBlock,
    T1636OutBlock,
    T1636OutBlock1,
    T1636Request,
    T1636Response,
    T1636ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1636(TRRequestAbstract, OccursReqAbstract):
    """LS Securities OpenAPI t1636 — Korean stock program trading by symbol.

    Returns per-symbol program trading flow on KOSPI / KOSDAQ:
    program buy/sell quantity and amount, net-buy quantity and amount,
    sort-key weight, market capitalization, and the net-buy ratio versus
    market cap (``mkcap_cmpr_val``) added by LS on 2026-01-08.

    Supports IDXCTS-based continuation paging via ``cts_idx``.
    """

    def __init__(self, request_data: T1636Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1636Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1636Response] = GenericTR[T1636Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1636Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1636OutBlock", None)
        block_data = resp_json.get("t1636OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1636ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1636OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1636OutBlock.model_validate(cont_data)

        parsed_block: list[T1636OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1636OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1636 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1636 request failed with status: {error_msg}")

        result = T1636Response(
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

    def req(self) -> T1636Response:
        return self._generic.req()

    async def req_async(self) -> T1636Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1636Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[T1636Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1636Response]:
        """
        동기 방식으로 종목별 프로그램 매매동향 전체를 연속조회합니다.

        cts_idx 기반으로 자동 페이징하여 모든 페이지를 수집합니다.
        """
        def _updater(req_data, resp: T1636Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1636 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1636InBlock"].cts_idx = resp.cont_block.cts_idx

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[T1636Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1636Response]:
        """
        비동기 방식으로 종목별 프로그램 매매동향 전체를 연속조회합니다.

        cts_idx 기반으로 자동 페이징하여 모든 페이지를 수집합니다.
        """
        def _updater(req_data, resp: T1636Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1636 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1636InBlock"].cts_idx = resp.cont_block.cts_idx

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1636,
    T1636InBlock,
    T1636OutBlock,
    T1636OutBlock1,
    T1636Request,
    T1636Response,
    T1636ResponseHeader,
]
