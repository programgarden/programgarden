from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.chart.t8452")
from .blocks import (
    T8452InBlock,
    T8452OutBlock,
    T8452OutBlock1,
    T8452Request,
    T8452Response,
    T8452ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8452(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t8452 (통합)주식챠트(N분) API용 클래스입니다.
    """

    def __init__(self, request_data: T8452Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T8452Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T8452Response] = GenericTR[T8452Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8452Response:
        resp_json = resp_json or {}
        t8452OutBlock_data = resp_json.get("t8452OutBlock", None)
        t8452OutBlock1_data = resp_json.get("t8452OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8452ResponseHeader.model_validate(resp_headers)

        parsed_t8452OutBlock: Optional[T8452OutBlock] = None
        if exc is None and not is_error_status and t8452OutBlock_data:
            parsed_t8452OutBlock = T8452OutBlock.model_validate(t8452OutBlock_data)

        parsed_t8452OutBlock1: list[T8452OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t8452OutBlock1 = [T8452OutBlock1.model_validate(item) for item in t8452OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8452 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8452 request failed with status: {error_msg}")

        result = T8452Response(
            header=header,
            cont_block=parsed_t8452OutBlock,
            block=parsed_t8452OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8452Response:
        return self._generic.req()

    async def req_async(self) -> T8452Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8452Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T8452Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8452Response]:
        """동기 방식으로 (통합)주식챠트(N분) API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8452Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8452 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8452InBlock"].shcode = resp.cont_block.shcode
            req_data.body["t8452InBlock"].jisiga = resp.cont_block.jisiga
            req_data.body["t8452InBlock"].jihigh = resp.cont_block.jihigh
            req_data.body["t8452InBlock"].jilow = resp.cont_block.jilow
            req_data.body["t8452InBlock"].jiclosev = resp.cont_block.jiclosev
            req_data.body["t8452InBlock"].jivolume = resp.cont_block.jivolume
            req_data.body["t8452InBlock"].disiga = resp.cont_block.disiga
            req_data.body["t8452InBlock"].dihigh = resp.cont_block.dihigh
            req_data.body["t8452InBlock"].dilow = resp.cont_block.dilow
            req_data.body["t8452InBlock"].diclose = resp.cont_block.diclose
            req_data.body["t8452InBlock"].highend = resp.cont_block.highend
            req_data.body["t8452InBlock"].lowend = resp.cont_block.lowend
            req_data.body["t8452InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8452InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8452InBlock"].s_time = resp.cont_block.s_time
            req_data.body["t8452InBlock"].e_time = resp.cont_block.e_time
            req_data.body["t8452InBlock"].dshmin = resp.cont_block.dshmin
            req_data.body["t8452InBlock"].rec_count = resp.cont_block.rec_count
            req_data.body["t8452InBlock"].nxt_fm_s_time = resp.cont_block.nxt_fm_s_time
            req_data.body["t8452InBlock"].nxt_fm_e_time = resp.cont_block.nxt_fm_e_time
            req_data.body["t8452InBlock"].nxt_fm_dshmin = resp.cont_block.nxt_fm_dshmin
            req_data.body["t8452InBlock"].nxt_am_s_time = resp.cont_block.nxt_am_s_time
            req_data.body["t8452InBlock"].nxt_am_e_time = resp.cont_block.nxt_am_e_time
            req_data.body["t8452InBlock"].nxt_am_dshmin = resp.cont_block.nxt_am_dshmin
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T8452Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8452Response]:
        """비동기 방식으로 (통합)주식챠트(N분) API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8452Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8452 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8452InBlock"].shcode = resp.cont_block.shcode
            req_data.body["t8452InBlock"].jisiga = resp.cont_block.jisiga
            req_data.body["t8452InBlock"].jihigh = resp.cont_block.jihigh
            req_data.body["t8452InBlock"].jilow = resp.cont_block.jilow
            req_data.body["t8452InBlock"].jiclosev = resp.cont_block.jiclosev
            req_data.body["t8452InBlock"].jivolume = resp.cont_block.jivolume
            req_data.body["t8452InBlock"].disiga = resp.cont_block.disiga
            req_data.body["t8452InBlock"].dihigh = resp.cont_block.dihigh
            req_data.body["t8452InBlock"].dilow = resp.cont_block.dilow
            req_data.body["t8452InBlock"].diclose = resp.cont_block.diclose
            req_data.body["t8452InBlock"].highend = resp.cont_block.highend
            req_data.body["t8452InBlock"].lowend = resp.cont_block.lowend
            req_data.body["t8452InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8452InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8452InBlock"].s_time = resp.cont_block.s_time
            req_data.body["t8452InBlock"].e_time = resp.cont_block.e_time
            req_data.body["t8452InBlock"].dshmin = resp.cont_block.dshmin
            req_data.body["t8452InBlock"].rec_count = resp.cont_block.rec_count
            req_data.body["t8452InBlock"].nxt_fm_s_time = resp.cont_block.nxt_fm_s_time
            req_data.body["t8452InBlock"].nxt_fm_e_time = resp.cont_block.nxt_fm_e_time
            req_data.body["t8452InBlock"].nxt_fm_dshmin = resp.cont_block.nxt_fm_dshmin
            req_data.body["t8452InBlock"].nxt_am_s_time = resp.cont_block.nxt_am_s_time
            req_data.body["t8452InBlock"].nxt_am_e_time = resp.cont_block.nxt_am_e_time
            req_data.body["t8452InBlock"].nxt_am_dshmin = resp.cont_block.nxt_am_dshmin
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT8452,
    T8452InBlock,
    T8452OutBlock,
    T8452OutBlock1,
    T8452Request,
    T8452Response,
    T8452ResponseHeader,
]
