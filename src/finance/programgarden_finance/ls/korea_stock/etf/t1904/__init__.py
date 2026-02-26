from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.etf.t1904")
from .blocks import (
    T1904InBlock,
    T1904OutBlock,
    T1904OutBlock1,
    T1904Request,
    T1904Response,
    T1904ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1904(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1904 ETF구성종목조회 클래스입니다.
    """

    def __init__(self, request_data: T1904Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1904Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1904Response] = GenericTR[T1904Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_ETF_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1904Response:
        resp_json = resp_json or {}
        t1904OutBlock_data = resp_json.get("t1904OutBlock", None)
        t1904OutBlock1_data = resp_json.get("t1904OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1904ResponseHeader.model_validate(resp_headers)

        parsed_t1904OutBlock: Optional[T1904OutBlock] = None
        if exc is None and not is_error_status and t1904OutBlock_data:
            parsed_t1904OutBlock = T1904OutBlock.model_validate(t1904OutBlock_data)

        parsed_t1904OutBlock1: list[T1904OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_t1904OutBlock1 = [T1904OutBlock1.model_validate(item) for item in t1904OutBlock1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1904 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1904 request failed with status: {error_msg}")

        result = T1904Response(
            header=header,
            cont_block=parsed_t1904OutBlock,
            block=parsed_t1904OutBlock1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T1904Response:
        return self._generic.req()

    async def req_async(self) -> T1904Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1904Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1904Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1904Response]:
        """동기 방식으로 ETF구성종목조회 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1904Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1904 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1904InBlock"].chk_tday = resp.cont_block.chk_tday
            req_data.body["t1904InBlock"].date = resp.cont_block.date
            req_data.body["t1904InBlock"].price = resp.cont_block.price
            req_data.body["t1904InBlock"].sign = resp.cont_block.sign
            req_data.body["t1904InBlock"].change = resp.cont_block.change
            req_data.body["t1904InBlock"].diff = resp.cont_block.diff
            req_data.body["t1904InBlock"].volume = resp.cont_block.volume
            req_data.body["t1904InBlock"].nav = resp.cont_block.nav
            req_data.body["t1904InBlock"].navsign = resp.cont_block.navsign
            req_data.body["t1904InBlock"].navchange = resp.cont_block.navchange
            req_data.body["t1904InBlock"].navdiff = resp.cont_block.navdiff
            req_data.body["t1904InBlock"].jnilnav = resp.cont_block.jnilnav
            req_data.body["t1904InBlock"].jnilnavsign = resp.cont_block.jnilnavsign
            req_data.body["t1904InBlock"].jnilnavchange = resp.cont_block.jnilnavchange
            req_data.body["t1904InBlock"].jnilnavdiff = resp.cont_block.jnilnavdiff
            req_data.body["t1904InBlock"].upname = resp.cont_block.upname
            req_data.body["t1904InBlock"].upcode = resp.cont_block.upcode
            req_data.body["t1904InBlock"].upprice = resp.cont_block.upprice
            req_data.body["t1904InBlock"].upsign = resp.cont_block.upsign
            req_data.body["t1904InBlock"].upchange = resp.cont_block.upchange
            req_data.body["t1904InBlock"].updiff = resp.cont_block.updiff
            req_data.body["t1904InBlock"].futname = resp.cont_block.futname
            req_data.body["t1904InBlock"].futcode = resp.cont_block.futcode
            req_data.body["t1904InBlock"].futprice = resp.cont_block.futprice
            req_data.body["t1904InBlock"].futsign = resp.cont_block.futsign
            req_data.body["t1904InBlock"].futchange = resp.cont_block.futchange
            req_data.body["t1904InBlock"].futdiff = resp.cont_block.futdiff
            req_data.body["t1904InBlock"].upname2 = resp.cont_block.upname2
            req_data.body["t1904InBlock"].upcode2 = resp.cont_block.upcode2
            req_data.body["t1904InBlock"].upprice2 = resp.cont_block.upprice2
            req_data.body["t1904InBlock"].etftotcap = resp.cont_block.etftotcap
            req_data.body["t1904InBlock"].etfnum = resp.cont_block.etfnum
            req_data.body["t1904InBlock"].etfcunum = resp.cont_block.etfcunum
            req_data.body["t1904InBlock"].cash = resp.cont_block.cash
            req_data.body["t1904InBlock"].opcom_nmk = resp.cont_block.opcom_nmk
            req_data.body["t1904InBlock"].tot_pval = resp.cont_block.tot_pval
            req_data.body["t1904InBlock"].tot_sigatval = resp.cont_block.tot_sigatval
        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1904Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1904Response]:
        """비동기 방식으로 ETF구성종목조회 전체를 연속조회합니다."""
        def _updater(req_data, resp: T1904Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1904 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1904InBlock"].chk_tday = resp.cont_block.chk_tday
            req_data.body["t1904InBlock"].date = resp.cont_block.date
            req_data.body["t1904InBlock"].price = resp.cont_block.price
            req_data.body["t1904InBlock"].sign = resp.cont_block.sign
            req_data.body["t1904InBlock"].change = resp.cont_block.change
            req_data.body["t1904InBlock"].diff = resp.cont_block.diff
            req_data.body["t1904InBlock"].volume = resp.cont_block.volume
            req_data.body["t1904InBlock"].nav = resp.cont_block.nav
            req_data.body["t1904InBlock"].navsign = resp.cont_block.navsign
            req_data.body["t1904InBlock"].navchange = resp.cont_block.navchange
            req_data.body["t1904InBlock"].navdiff = resp.cont_block.navdiff
            req_data.body["t1904InBlock"].jnilnav = resp.cont_block.jnilnav
            req_data.body["t1904InBlock"].jnilnavsign = resp.cont_block.jnilnavsign
            req_data.body["t1904InBlock"].jnilnavchange = resp.cont_block.jnilnavchange
            req_data.body["t1904InBlock"].jnilnavdiff = resp.cont_block.jnilnavdiff
            req_data.body["t1904InBlock"].upname = resp.cont_block.upname
            req_data.body["t1904InBlock"].upcode = resp.cont_block.upcode
            req_data.body["t1904InBlock"].upprice = resp.cont_block.upprice
            req_data.body["t1904InBlock"].upsign = resp.cont_block.upsign
            req_data.body["t1904InBlock"].upchange = resp.cont_block.upchange
            req_data.body["t1904InBlock"].updiff = resp.cont_block.updiff
            req_data.body["t1904InBlock"].futname = resp.cont_block.futname
            req_data.body["t1904InBlock"].futcode = resp.cont_block.futcode
            req_data.body["t1904InBlock"].futprice = resp.cont_block.futprice
            req_data.body["t1904InBlock"].futsign = resp.cont_block.futsign
            req_data.body["t1904InBlock"].futchange = resp.cont_block.futchange
            req_data.body["t1904InBlock"].futdiff = resp.cont_block.futdiff
            req_data.body["t1904InBlock"].upname2 = resp.cont_block.upname2
            req_data.body["t1904InBlock"].upcode2 = resp.cont_block.upcode2
            req_data.body["t1904InBlock"].upprice2 = resp.cont_block.upprice2
            req_data.body["t1904InBlock"].etftotcap = resp.cont_block.etftotcap
            req_data.body["t1904InBlock"].etfnum = resp.cont_block.etfnum
            req_data.body["t1904InBlock"].etfcunum = resp.cont_block.etfcunum
            req_data.body["t1904InBlock"].cash = resp.cont_block.cash
            req_data.body["t1904InBlock"].opcom_nmk = resp.cont_block.opcom_nmk
            req_data.body["t1904InBlock"].tot_pval = resp.cont_block.tot_pval
            req_data.body["t1904InBlock"].tot_sigatval = resp.cont_block.tot_sigatval
        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1904,
    T1904InBlock,
    T1904OutBlock,
    T1904OutBlock1,
    T1904Request,
    T1904Response,
    T1904ResponseHeader,
]
