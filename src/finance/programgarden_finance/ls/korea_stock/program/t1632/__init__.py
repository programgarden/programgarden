from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1632")
from .blocks import (
    T1632InBlock,
    T1632OutBlock,
    T1632OutBlock1,
    T1632Request,
    T1632Response,
    T1632ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1632(TRRequestAbstract, OccursReqAbstract):
    """LS Securities OpenAPI t1632 — time-bucketed program-trading trend query.

    Returns time-bucketed KP200 index, BASIS, and program-trading flow
    (total / arbitrage / non-arbitrage buy, sell, and net-buy) for:

    - KOSPI exchange (``gubun='0'``) — **note**: t1631 uses ``'1'`` for the
      same market; encodings differ.
    - KOSDAQ market (``gubun='1'``).

    Supports ``tr_cont`` continuation paging via ``date`` + ``time`` CTS
    cursors (not idx — unlike t1452 which pages by idx). Use
    ``occurs_req()`` / ``occurs_req_async()`` to auto-page through all
    time buckets without managing cursors manually.

    Unlike t1631, this class **inherits** ``OccursReqAbstract`` because
    t1632 supports multi-page responses (tr_cont='Y').
    """

    def __init__(
        self,
        request_data: T1632Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T1632Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T1632Response] = GenericTR[T1632Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1632Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1632OutBlock", None)
        block_data = resp_json.get("t1632OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1632ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1632OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1632OutBlock.model_validate(cont_data)

        parsed_block: list[T1632OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1632OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1632 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1632 request failed with status: {error_msg}")

        result = T1632Response(
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

    def req(self) -> T1632Response:
        return self._generic.req()

    async def req_async(self) -> T1632Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1632Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[T1632Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1632Response]:
        """Auto-page through all time buckets using tr_cont + date/time CTS cursors.

        Advances the ``date`` and ``time`` fields in the InBlock (and the
        ``tr_cont`` / ``tr_cont_key`` header fields) from the continuation
        marker returned in each response, until ``tr_cont`` is no longer
        ``'Y'``.

        Note: t1632 pages by ``date`` + ``time`` CTS — not by ``idx`` as
        t1452 does.

        Args:
            callback: Optional callable invoked after each page. Receives the
                ``T1632Response`` for that page and a ``RequestStatus``.
            delay: Seconds to wait between pages (default 1).

        Returns:
            All collected ``T1632Response`` objects in page order.
        """
        def _updater(req_data, resp: T1632Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1632 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1632InBlock"].date = resp.cont_block.date
            req_data.body["t1632InBlock"].time = resp.cont_block.time

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[T1632Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1632Response]:
        """Async variant of ``occurs_req``.

        Auto-pages through all time buckets using tr_cont + date/time CTS
        cursors. See ``occurs_req`` for details.

        Args:
            callback: Optional callable invoked after each page.
            delay: Seconds to wait between pages (default 1).

        Returns:
            All collected ``T1632Response`` objects in page order.
        """
        def _updater(req_data, resp: T1632Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1632 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1632InBlock"].date = resp.cont_block.date
            req_data.body["t1632InBlock"].time = resp.cont_block.time

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1632,
    T1632InBlock,
    T1632OutBlock,
    T1632OutBlock1,
    T1632Request,
    T1632Response,
    T1632ResponseHeader,
]
