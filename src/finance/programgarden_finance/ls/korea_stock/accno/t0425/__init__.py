from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.t0425")

from .blocks import (
    T0425InBlock,
    T0425OutBlock,
    T0425OutBlock1,
    T0425Request,
    T0425Response,
    T0425ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT0425(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t0425 주식 체결/미체결 API용 클래스입니다.

    종목번호, 체결구분, 매매구분, 정렬순서 조건으로
    당일 주문별 체결수량, 미체결잔량, 주문상태, 추정수수료 등을 조회합니다.

    cts_ordno 기반 연속조회를 지원합니다.
    """

    def __init__(
        self,
        request_data: T0425Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T0425Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T0425Response] = GenericTR[T0425Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T0425Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t0425OutBlock", None)
        block_data = resp_json.get("t0425OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T0425ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T0425OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T0425OutBlock.model_validate(cont_data)

        parsed_block: list[T0425OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T0425OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t0425 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t0425 request failed with status: {error_msg}")

        result = T0425Response(
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

    def req(self) -> T0425Response:
        return self._generic.req()

    async def req_async(self) -> T0425Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T0425Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[T0425Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T0425Response]:
        """
        동기 방식으로 주식 체결/미체결 전체를 연속조회합니다.

        cts_ordno 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T0425Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T0425Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t0425 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t0425InBlock"].cts_ordno = resp.cont_block.cts_ordno

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[T0425Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T0425Response]:
        """
        비동기 방식으로 주식 체결/미체결 전체를 연속조회합니다.

        cts_ordno 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T0425Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T0425Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t0425 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t0425InBlock"].cts_ordno = resp.cont_block.cts_ordno

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT0425,
    T0425InBlock,
    T0425OutBlock,
    T0425OutBlock1,
    T0425Request,
    T0425Response,
    T0425ResponseHeader,
]
