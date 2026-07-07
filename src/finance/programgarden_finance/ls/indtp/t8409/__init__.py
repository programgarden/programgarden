from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.indtp.t8409")
from .blocks import (
    T8409InBlock,
    T8409OutBlock,
    T8409OutBlock1,
    T8409Request,
    T8409Response,
    T8409RequestHeader,
    T8409ResponseHeader,
)
from ...tr_base import OccursReqAbstract, TRRequestAbstract
from ...tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT8409(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t8409 업종차트(N분) 클래스입니다.

    업종코드로 해당 업종 지수의 N분(0=30초) 차트를 조회합니다. 응답은 메타/커서
    블록(``cont_block`` = 전일·당일 지수 OHLC, 전일거래량, 당일거래대금, 연속커서,
    업종 시작/종료 시간, 레코드카운트)과 분봉 행 리스트(``block`` = 각 봉의
    날짜/시간/지수 OHLC/거래량/거래대금)로 구성됩니다.

    주의: 모든 OHLC 값은 업종 **지수(index points)** 이며 KRW 가격이 아닙니다.
    거래대금(disvalue/value)은 백만원, 거래량(jivolume/jdiff_vol)은 천주 단위이며,
    이 단위는 LS 명세에 공식 선언되지 않아 샘플 응답으로 교차검증된 값입니다.

    cts_date/cts_time 기반 연속조회를 지원합니다.
    """

    def __init__(
        self,
        request_data: T8409Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T8409Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T8409Response] = GenericTR[T8409Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_INDTP_CHART_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T8409Response:
        resp_json = resp_json or {}
        cont_block_data = resp_json.get("t8409OutBlock", None)
        block_data = resp_json.get("t8409OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T8409ResponseHeader.model_validate(resp_headers)

        parsed_cont_block: Optional[T8409OutBlock] = None
        parsed_block: list[T8409OutBlock1] = []
        if exc is None and not is_error_status:
            if cont_block_data is not None:
                parsed_cont_block = T8409OutBlock.model_validate(cont_block_data)
            parsed_block = [T8409OutBlock1.model_validate(item) for item in block_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t8409 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t8409 request failed with status: {error_msg}")

        result = T8409Response(
            header=header,
            cont_block=parsed_cont_block,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> T8409Response:
        return self._generic.req()

    async def req_async(self) -> T8409Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T8409Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T8409Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8409Response]:
        """
        동기 방식으로 업종차트(N분) 전체를 연속조회합니다.

        cts_date/cts_time 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T8409Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T8409Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8409 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8409InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8409InBlock"].cts_time = resp.cont_block.cts_time

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T8409Response], RequestStatus], None]] = None, delay: int = 1) -> list[T8409Response]:
        """
        비동기 방식으로 업종차트(N분) 전체를 연속조회합니다.

        cts_date/cts_time 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T8409Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T8409Response):
            if resp.header is None or resp.cont_block is None:
                raise ValueError("t8409 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t8409InBlock"].cts_date = resp.cont_block.cts_date
            req_data.body["t8409InBlock"].cts_time = resp.cont_block.cts_time

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT8409,
    T8409InBlock,
    T8409OutBlock,
    T8409OutBlock1,
    T8409Request,
    T8409Response,
    T8409RequestHeader,
    T8409ResponseHeader,
]
