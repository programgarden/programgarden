from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.chart.t8451")
from .blocks import (
    T8451InBlock,
    T8451OutBlock,
    T8451OutBlock1,
    T8451Request,
    T8451Response,
    T8451ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8451(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI의 t8451 주식차트(일주월년) API용 클래스입니다.
    """

    def __init__(
        self,
        request_data: T8451Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T8451Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T8451Response] = GenericTR[T8451Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8451Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t8451OutBlock", None)
        block1_data = resp_json.get("t8451OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8451ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[T8451OutBlock] = None
        parsed_block1: list[T8451OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = T8451OutBlock.model_validate(block_data)
            parsed_block1 = [T8451OutBlock1.model_validate(item) for item in block1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8451 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8451 request failed with status: {error_msg}")

        result = T8451Response(
            header=header,
            block=parsed_block,
            block1=parsed_block1,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8451Response:
        return self._generic.req()

    async def req_async(self) -> T8451Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8451Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T8451Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8451Response]:
        """
        동기 방식으로 연속 조회를 수행합니다.

        Args:
            callback: 상태 변경 시 호출될 콜백 함수
            delay: 연속 조회 간격 (초)

        Returns:
            list[T8451Response]: 조회된 모든 응답 리스트
        """
        def _updater(req_data, resp: T8451Response):
            if resp.header is None or resp.block is None:
                raise ValueError("t8451 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8451InBlock"].cts_date = resp.block.cts_date

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T8451Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8451Response]:
        """
        비동기 방식으로 연속 조회를 수행합니다.

        Args:
            callback: 상태 변경 시 호출될 콜백 함수
            delay: 연속 조회 간격 (초)

        Returns:
            list[T8451Response]: 조회된 모든 응답 리스트
        """
        def _updater(req_data, resp: T8451Response):
            if resp.header is None or resp.block is None:
                raise ValueError("t8451 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8451InBlock"].cts_date = resp.block.cts_date

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT8451,
    T8451InBlock,
    T8451OutBlock,
    T8451OutBlock1,
    T8451Request,
    T8451Response,
    T8451ResponseHeader,
]
