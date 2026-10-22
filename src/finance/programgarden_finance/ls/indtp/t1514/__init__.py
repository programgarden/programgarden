from typing import Callable, Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.indtp.t1514")
from .blocks import (
    T1514InBlock,
    T1514OutBlock,
    T1514OutBlock1,
    T1514Request,
    T1514Response,
    T1514ResponseHeader,
)
from ...tr_base import OccursReqAbstract, TRRequestAbstract
from ...tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrT1514(TRRequestAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI t1514 업종기간별추이 클래스입니다.

    업종코드로 해당 업종 지수의 기간별(일/주/월) 추이를 조회합니다. 각 기간 행은
    지수 OHLC(``jisu``/``openjisu``/``highjisu``/``lowjisu``), 전일대비/등락률,
    거래량/거래대금, 시장폭(상승/보합/하락/상한/하한 **종목수**), 외인·기관
    순매수, 거래비중, 업종배당수익률을 포함합니다.

    cts_date 기반 연속조회를 지원합니다.
    """

    def __init__(
        self,
        request_data: T1514Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, T1514Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[T1514Response] = GenericTR[T1514Response](self.request_data, self._build_response, url=URLS.KOREA_STOCK_INDTP_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> T1514Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("t1514OutBlock", None)
        block1_data = resp_json.get("t1514OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = T1514ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[T1514OutBlock] = None
        parsed_block1: list[T1514OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = T1514OutBlock.model_validate(block_data)
            parsed_block1 = [T1514OutBlock1.model_validate(item) for item in block1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"t1514 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"t1514 request failed with status: {error_msg}")

        result = T1514Response(
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

    def req(self) -> T1514Response:
        return self._generic.req()

    async def req_async(self) -> T1514Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> T1514Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def occurs_req(self, callback: Optional[Callable[[Optional[T1514Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1514Response]:
        """
        동기 방식으로 업종기간별추이 전체를 연속조회합니다.

        cts_date 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T1514Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T1514Response):
            if resp.header is None or resp.block is None:
                raise ValueError("t1514 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1514InBlock"].cts_date = resp.block.cts_date

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[T1514Response], RequestStatus], None]] = None, delay: int = 1) -> list[T1514Response]:
        """
        비동기 방식으로 업종기간별추이 전체를 연속조회합니다.

        cts_date 기반으로 자동 페이징하여 모든 페이지를 수집합니다.

        Args:
            callback: 각 페이지 조회 시 호출될 콜백 함수
            delay: 연속조회 간격 (초)

        Returns:
            list[T1514Response]: 조회된 모든 페이지 응답 리스트
        """
        def _updater(req_data, resp: T1514Response):
            if resp.header is None or resp.block is None:
                raise ValueError("t1514 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["t1514InBlock"].cts_date = resp.block.cts_date

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrT1514,
    T1514InBlock,
    T1514OutBlock,
    T1514OutBlock1,
    T1514Request,
    T1514Response,
    T1514ResponseHeader,
]
