from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.program.t1637")
from .blocks import (
    T1637InBlock,
    T1637OutBlock,
    T1637OutBlock1,
    T1637Request,
    T1637Response,
    T1637ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1637(TRRequestAbstract, OccursReqAbstract):
    """LS Securities OpenAPI t1637 — per-symbol program-trading time series.

    Returns the program-trading flow (price, change, percent change, volume,
    plus buy / sell / net-buy amount and quantity) for a single Korean stock.
    Two display modes are selected by ``T1637InBlock.gubun2``:

        - ``gubun2 == '0'`` — time-bucketed within a trading day.
        - ``gubun2 == '1'`` — daily across multiple trading days.

    Continuation paging:
        - ``tr_cont == 'Y'`` triggers paging.
        - The cursor field depends on ``gubun2``:
            * gubun2 == '0' (time mode): ``InBlock.time`` advances from the
              ``time`` value of the LAST row of the previous page.
            * gubun2 == '1' (daily mode): ``InBlock.date`` advances from the
              ``date`` value of the LAST row of the previous page.
        - ``cts_idx`` is described in the LS spec as a chart-query marker
          (``IDXCTS(9999:차트)`` — '차트 조회시에만 9999로 입력') and is
          fixed at 9999 by default. The LS spec defines the date / time
          fields as the continuation cursors; ``cts_idx`` is not used for
          paging by this SDK.

    Inherits ``OccursReqAbstract`` because t1637 supports multi-page
    responses (tr_cont='Y').
    """

    def __init__(self, request_data: T1637Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        if not isinstance(self.request_data, T1637Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[T1637Response] = GenericTR[T1637Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_PROGRAM_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T1637Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1637OutBlock", None)
        block_data = resp_json.get("t1637OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1637ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1637OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1637OutBlock.model_validate(cont_data)

        parsed_block: list[T1637OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1637OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1637 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1637 request failed with status: {error_msg}")

        result = T1637Response(
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

    def req(self) -> T1637Response:
        return self._generic.req()

    async def req_async(self) -> T1637Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1637Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[T1637Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1637Response]:
        """Auto-page through the entire time series using a gubun2-aware cursor.

        Cursor selection follows LS spec literally:
            - ``gubun2 == '0'`` (time mode): advances ``InBlock.time`` from the
              ``time`` value of the LAST row of the previous page.
            - ``gubun2 == '1'`` (daily mode): advances ``InBlock.date`` from the
              ``date`` value of the LAST row of the previous page.

        Always advances ``tr_cont`` / ``tr_cont_key`` headers from the response
        header. Stops when ``tr_cont`` is no longer ``'Y'``.

        Raises ``ValueError`` if the response is missing the header (cannot
        propagate tr_cont) or if ``T1637OutBlock1`` is empty (cannot extract
        the cursor seed).

        Args:
            callback: Optional callable invoked after each page. Receives the
                ``T1637Response`` for that page and a ``RequestStatus``.
            delay: Seconds to wait between pages (default 1).

        Returns:
            All collected ``T1637Response`` objects in page order.
        """
        def _updater(req_data, resp: T1637Response):
            if resp.header is None:
                raise ValueError("t1637 response missing continuation header")
            if not resp.block:
                raise ValueError("t1637 response missing OutBlock1 rows for continuation")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            last_row = resp.block[-1]
            in_block = req_data.body["t1637InBlock"]
            if in_block.gubun2 == "0":
                in_block.time = last_row.time
            else:
                in_block.date = last_row.date

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[T1637Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T1637Response]:
        """Async variant of ``occurs_req``.

        Auto-pages through the entire time series using a gubun2-aware cursor
        (time cursor in time mode, date cursor in daily mode). See ``occurs_req``
        for details.

        Args:
            callback: Optional callable invoked after each page.
            delay: Seconds to wait between pages (default 1).

        Returns:
            All collected ``T1637Response`` objects in page order.
        """
        def _updater(req_data, resp: T1637Response):
            if resp.header is None:
                raise ValueError("t1637 response missing continuation header")
            if not resp.block:
                raise ValueError("t1637 response missing OutBlock1 rows for continuation")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            last_row = resp.block[-1]
            in_block = req_data.body["t1637InBlock"]
            if in_block.gubun2 == "0":
                in_block.time = last_row.time
            else:
                in_block.date = last_row.date

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1637,
    T1637InBlock,
    T1637OutBlock,
    T1637OutBlock1,
    T1637Request,
    T1637Response,
    T1637ResponseHeader,
]
