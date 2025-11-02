"""
LS증권 OpenAPI의 g3202 TR을 통한 해외주식 차트 TICK 데이터 조회 모듈

이 모듈은 LS증권의 OpenAPI를 사용하여 해외주식의 TICK 차트 데이터를 조회하는 기능을 제공합니다.

주요 기능:
- 해외주식의 TICK 차트 데이터 조회
- 실시간 TICK 데이터 조회
- 분봉, 초봉 데이터 제공
"""

from typing import Callable, Optional, Dict, Any
import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    G3202InBlock,
    G3202OutBlock,
    G3202OutBlock1,
    G3202Request,
    G3202Response,
    G3202ResponseHeader
)
from ....tr_base import OccursReqAbstract, TRRequestAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus
from programgarden_core.logs import pg_logger

# ...existing code... (pg_logger intentionally unused after refactor)


class TrG3202(TRRequestAbstract, OccursReqAbstract):
    """
    차트 TICK 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: G3202Request,
    ):
        """
        TrG3202 생성자

        Args:
            request_data (G3202Request): 차트 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, G3202Request):
            raise TrRequestDataNotFoundException()

        self._generic = GenericTR[G3202Response](self.request_data, self._build_response, url=URLS.CHART_URL)

    def req(self) -> G3202Response:
        return self._generic.req()

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> G3202Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("g3202OutBlock")
        block1_data = resp_json.get("g3202OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = G3202ResponseHeader.model_validate(resp_headers)

        parsed_block = None
        parsed_block1: list[G3202OutBlock1] = []
        if exc is None and not is_error_status:
            if block_data is not None:
                parsed_block = G3202OutBlock.model_validate(block_data)
            parsed_block1 = [G3202OutBlock1.model_validate(item) for item in block1_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"g3202 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"g3202 request failed with status: {error_msg}")

        result = G3202Response(
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

    def occurs_req(self, callback: Optional[Callable[[Optional[G3202Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3202Response]:
        """
        동기 방식으로 연속 조회를 수행합니다.

        Args:
            callback: 상태 변경 시 호출될 콜백 함수
            delay: 연속 조회 간격 (초)

        Returns:
            list[G3202Response]: 조회된 모든 응답 리스트
        """
        # continuation updater specific to G3202
        def _updater(req_data, resp: G3202Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3202 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3202InBlock"].cts_seq = resp.block.cts_seq

        return self._generic.occurs_req(_updater, callback=callback, delay=delay)

    async def req_async(self) -> G3202Response:
        """
        세션을 재사용하여 비동기 HTTP 요청을 수행합니다.

        Returns:
            G3202Response: 응답 데이터
        """
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> G3202Response:

        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def occurs_req_async(self, callback: Optional[Callable[[Optional[G3202Response], RequestStatus], None]] = None, delay: int = 1) -> list[G3202Response]:
        """
        비동기 방식으로 연속 조회를 수행합니다.

        Args:
            callback: 상태 변경 시 호출될 콜백 함수
            delay: 연속 조회 간격 (초)

        Returns:
            list[G3202Response]: 조회된 모든 응답 리스트
        """
        def _updater(req_data, resp: G3202Response):
            if resp.header is None or resp.block is None:
                raise ValueError("g3202 response missing continuation data")
            req_data.header.tr_cont_key = resp.header.tr_cont_key
            req_data.header.tr_cont = resp.header.tr_cont
            req_data.body["g3202InBlock"].cts_seq = resp.block.cts_seq

        return await self._generic.occurs_req_async(_updater, callback=callback, delay=delay)


__all__ = [
    TrG3202,
    G3202InBlock,
    G3202OutBlock,
    G3202OutBlock1,
    G3202Request,
    G3202Response,
    G3202ResponseHeader
]
