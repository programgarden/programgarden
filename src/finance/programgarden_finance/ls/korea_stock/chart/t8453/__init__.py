from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.chart.t8453")
from .blocks import (
    T8453InBlock,
    T8453OutBlock,
    T8453OutBlock1,
    T8453Request,
    T8453Response,
    T8453ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8453(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t8453 (통합)주식챠트(틱/N틱) API용 클래스입니다.
    """

    def __init__(self, request_data: T8453Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T8453Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T8453Response] = GenericTR[T8453Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8453Response:
        resp_json = resp_json or {}
        t8453OutBlock_data = resp_json.get("t8453OutBlock", None)
        t8453OutBlock1_data = resp_json.get("t8453OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8453ResponseHeader.model_validate(resp_headers)

        parsed_t8453OutBlock: Optional[T8453OutBlock] = None
        if exc is None and not is_error_status and t8453OutBlock_data:
            parsed_t8453OutBlock = T8453OutBlock.model_validate(t8453OutBlock_data)

        parsed_t8453OutBlock1: list[T8453OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t8453OutBlock1 = [T8453OutBlock1.model_validate(item) for item in t8453OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8453 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8453 request failed with status: {error_msg}")

        result = T8453Response(
            header=header,
            cont_block=parsed_t8453OutBlock,
            block=parsed_t8453OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8453Response:
        return self._generic.req()

    async def req_async(self) -> T8453Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8453Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T8453Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8453Response]:
        """동기 방식으로 (통합)주식챠트(틱/N틱) API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8453Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8453 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8453InBlock"].shcode = resp.cont_block.shcode
            req_data.body["t8453InBlock"].jisiga = resp.cont_block.jisiga
            req_data.body["t8453InBlock"].jihigh = resp.cont_block.jihigh
            req_data.body["t8453InBlock"].jilow = resp.cont_block.jilow
            req_data.body["t8453InBlock"].jicloseㅍ = resp.cont_block.jicloseㅍ
            req_data.body["t8453InBlock"].jivolume = resp.cont_block.jivolume
            req_data.body["t8453InBlock"].disiga = resp.cont_block.disiga
            req_data.body["t8453InBlock"].dihigh = resp.cont_block.dihigh
            req_data.body["t8453InBlock"].dilow = resp.cont_block.dilow
            req_data.body["t8453InBlock"].diclose = resp.cont_block.diclose
            req_data.body["t8453InBlock"].highend = resp.cont_block.highend
            req_data.body["t8453InBlock"].lowend = resp.cont_block.lowend
            req_data.body["t8453InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8453InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8453InBlock"].s_time = resp.cont_block.s_time
            req_data.body["t8453InBlock"].e_time = resp.cont_block.e_time
            req_data.body["t8453InBlock"].dshmin = resp.cont_block.dshmin
            req_data.body["t8453InBlock"].rec_count = resp.cont_block.rec_count
            req_data.body["t8453InBlock"].nxt_fm_s_time = resp.cont_block.nxt_fm_s_time
            req_data.body["t8453InBlock"].nxt_fm_e_time = resp.cont_block.nxt_fm_e_time
            req_data.body["t8453InBlock"].nxt_fm_dshmin = resp.cont_block.nxt_fm_dshmin
            req_data.body["t8453InBlock"].nxt_am_s_time = resp.cont_block.nxt_am_s_time
            req_data.body["t8453InBlock"].nxt_am_e_time = resp.cont_block.nxt_am_e_time
            req_data.body["t8453InBlock"].nxt_am_dshmin = resp.cont_block.nxt_am_dshmin
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T8453Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8453Response]:
        """비동기 방식으로 (통합)주식챠트(틱/N틱) API용 전체를 연속조회합니다."""
        def _updater(req_data, resp: T8453Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8453 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8453InBlock"].shcode = resp.cont_block.shcode
            req_data.body["t8453InBlock"].jisiga = resp.cont_block.jisiga
            req_data.body["t8453InBlock"].jihigh = resp.cont_block.jihigh
            req_data.body["t8453InBlock"].jilow = resp.cont_block.jilow
            req_data.body["t8453InBlock"].jicloseㅍ = resp.cont_block.jicloseㅍ
            req_data.body["t8453InBlock"].jivolume = resp.cont_block.jivolume
            req_data.body["t8453InBlock"].disiga = resp.cont_block.disiga
            req_data.body["t8453InBlock"].dihigh = resp.cont_block.dihigh
            req_data.body["t8453InBlock"].dilow = resp.cont_block.dilow
            req_data.body["t8453InBlock"].diclose = resp.cont_block.diclose
            req_data.body["t8453InBlock"].highend = resp.cont_block.highend
            req_data.body["t8453InBlock"].lowend = resp.cont_block.lowend
            req_data.body["t8453InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8453InBlock"].cts_time = resp.cont_block.cts_time
            req_data.body["t8453InBlock"].s_time = resp.cont_block.s_time
            req_data.body["t8453InBlock"].e_time = resp.cont_block.e_time
            req_data.body["t8453InBlock"].dshmin = resp.cont_block.dshmin
            req_data.body["t8453InBlock"].rec_count = resp.cont_block.rec_count
            req_data.body["t8453InBlock"].nxt_fm_s_time = resp.cont_block.nxt_fm_s_time
            req_data.body["t8453InBlock"].nxt_fm_e_time = resp.cont_block.nxt_fm_e_time
            req_data.body["t8453InBlock"].nxt_fm_dshmin = resp.cont_block.nxt_fm_dshmin
            req_data.body["t8453InBlock"].nxt_am_s_time = resp.cont_block.nxt_am_s_time
            req_data.body["t8453InBlock"].nxt_am_e_time = resp.cont_block.nxt_am_e_time
            req_data.body["t8453InBlock"].nxt_am_dshmin = resp.cont_block.nxt_am_dshmin
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT8453,
    T8453InBlock,
    T8453OutBlock,
    T8453OutBlock1,
    T8453Request,
    T8453Response,
    T8453ResponseHeader,
]
