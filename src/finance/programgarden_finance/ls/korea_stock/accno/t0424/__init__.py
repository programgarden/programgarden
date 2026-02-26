from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.t0424")

from .blocks import (
    T0424InBlock,
    T0424OutBlock,
    T0424OutBlock1,
    T0424Request,
    T0424Response,
    T0424ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT0424(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t0424 주식잔고2 API용 클래스입니다.

    단가구분, 체결구분, 단일가구분, 제비용포함 여부 조건으로
    계좌 내 보유 종목별 잔고수량, 평가금액, 손익 등을 조회합니다.

    cts_expcode 기반 연속조회를 지원합니다.
    """

    def __init__(
        self,
        request_data: T0424Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T0424Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T0424Response] = GenericTR[T0424Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> T0424Response:
        resp_json = resp_json or {}
        cont_data = resp_json.get("t0424OutBlock", None)
        block_data = resp_json.get("t0424OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T0424ResponseHeader.model_validate(resp_headers)

        parsed_cont: Optional[T0424OutBlock] = None
        if exc is None and not is_error_status and cont_data:
            parsed_cont = T0424OutBlock.model_validate(cont_data)

        parsed_block: list[T0424OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_block = [T0424OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t0424 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t0424 request failed with status: {error_msg}")

        result = T0424Response(
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

    def req(self) -> T0424Response:
        return self._generic.req()

    async def req_async(self) -> T0424Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T0424Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[T0424Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T0424Response]:
        """
        동기 방식으로 주식잔고2 전체를 연속조회합니다.

        cts_expcode 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T0424Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T0424Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t0424 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t0424InBlock"].cts_expcode = resp.cont_block.cts_expcode

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[T0424Response], RequestStatus], None]] = None,
        delay: int = 1,
    ) -> list[T0424Response]:
        """
        비동기 방식으로 주식잔고2 전체를 연속조회합니다.

        cts_expcode 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T0424Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T0424Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t0424 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t0424InBlock"].cts_expcode = resp.cont_block.cts_expcode

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT0424,
    T0424InBlock,
    T0424OutBlock,
    T0424OutBlock1,
    T0424Request,
    T0424Response,
    T0424ResponseHeader,
]
