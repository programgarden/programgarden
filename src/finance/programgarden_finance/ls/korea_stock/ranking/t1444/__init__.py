from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.market.t1444")
from .blocks import (
    T1444InBlock,
    T1444OutBlock,
    T1444OutBlock1,
    T1444Request,
    T1444Response,
    T1444ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1444(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1444 시가총액상위 클래스입니다.

    업종코드별 시가총액 상위 종목의 현재가, 등락률, 거래량,
    시가총액, 업종 내 비중, 외국인 보유비중을 조회합니다.

    idx 기반 연속조회를 지원합니다 (한 번에 약 20건).
    """

    def __init__(
        self,
        request_data: T1444Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T1444Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T1444Response] = GenericTR[T1444Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_HIGH_ITEM_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1444Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t1444OutBlock", None)
        block_data = resp_json.get("t1444OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1444ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T1444OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T1444OutBlock.model_validate(cont_data)

        parsed_block: list[T1444OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T1444OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1444 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1444 request failed with status: {error_msg}")

        result = T1444Response(
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

    def req(self) -> T1444Response:
        return self._generic.req()

    async def req_async(self) -> T1444Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1444Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1444Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1444Response]:
        """
        동기 방식으로 시가총액상위 전체를 연속조회합니다.

        idx 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T1444Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T1444Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1444 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1444InBlock"].idx = resp.cont_block.idx

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1444Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1444Response]:
        """
        비동기 방식으로 시가총액상위 전체를 연속조회합니다.

        idx 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T1444Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T1444Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t1444 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1444InBlock"].idx = resp.cont_block.idx

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1444,
    T1444InBlock,
    T1444OutBlock,
    T1444OutBlock1,
    T1444Request,
    T1444Response,
    T1444ResponseHeader,
]
