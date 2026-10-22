from typing import Callable, Dict, Any, List, Optional

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.CSPAQ13700")

from .blocks import (
    CSPAQ13700InBlock1,
    CSPAQ13700OutBlock1,
    CSPAQ13700OutBlock2,
    CSPAQ13700OutBlock3,
    CSPAQ13700Request,
    CSPAQ13700Response,
    CSPAQ13700ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRAccnoAbstract
from ....tr_helpers import DEFAULT_OCCURS_MAX_PAGES, GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrCSPAQ13700(TRAccnoAbstract, OccursReqAbstract):
    """
    LS증권 OpenAPI CSPAQ13700 현물계좌 주문체결내역 조회 API용 클래스입니다.

    계좌의 주문체결내역과 요약 정보를 조회합니다.
    """

    def __init__(
        self,
        request_data: CSPAQ13700Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CSPAQ13700Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CSPAQ13700Response] = GenericTR[CSPAQ13700Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> CSPAQ13700Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CSPAQ13700OutBlock1", None)
        block2_data = resp_json.get("CSPAQ13700OutBlock2", None)
        block3_data = resp_json.get("CSPAQ13700OutBlock3", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CSPAQ13700ResponseHeader.model_validate(resp_headers)

        parsed_block1: Optional[CSPAQ13700OutBlock1] = None
        parsed_block2: Optional[CSPAQ13700OutBlock2] = None
        parsed_block3: List[CSPAQ13700OutBlock3] = []

        if exc is None and not is_error_status:
            if block1_data:
                parsed_block1 = CSPAQ13700OutBlock1.model_validate(block1_data)
            if block2_data:
                parsed_block2 = CSPAQ13700OutBlock2.model_validate(block2_data)
            if block3_data and isinstance(block3_data, list):
                parsed_block3 = [CSPAQ13700OutBlock3.model_validate(item) for item in block3_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"CSPAQ13700 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"CSPAQ13700 request failed with status: {error_msg}")

        result = CSPAQ13700Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            block3=parsed_block3,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> CSPAQ13700Response:
        return self._generic.req()

    async def req_async(self) -> CSPAQ13700Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CSPAQ13700Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(
        self,
        callback: Callable[[Optional[CSPAQ13700Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(
        self,
        callback: Callable[[Optional[CSPAQ13700Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ) -> CSPAQ13700Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[CSPAQ13700Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[CSPAQ13700Response]:
        """현물계좌 주문체결내역 전체 페이지를 동기 방식으로 연속조회합니다.

        다음 페이지는 같은 본문에 요청 헤더 ``tr_cont="Y"`` 와 직전 응답의
        ``tr_cont_key`` 를 실어 다시 보냅니다(가이드 공통 헤더). ``SrtOrdNo2`` 는 가이드에
        시작값(역순 999999999 / 정순 000000000)만 정의돼 있어 페이지 사이에 바꾸지 않습니다. 페이지마다 이 TR 의
        rate limit 을 지키고, 페이지 사이에 ``delay`` 초를 쉽니다.

        Returns:
            List[CSPAQ13700Response]: 페이지별 응답(행을 합치지 않음). 실패한 페이지는 마지막
            원소로 남고, 키가 비었거나 반복되거나 ``max_pages`` 에 닿으면 마지막
            성공 페이지(여전히 ``tr_cont="Y"``)에서 멈춥니다. 전부 받았는지는
            ``programgarden_finance.ls.tr_helpers.occurs_complete(pages)`` 로 확인하세요.
        """
        return self._generic.header_occurs_req(callback=callback, delay=delay, max_pages=max_pages)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[CSPAQ13700Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[CSPAQ13700Response]:
        """현물계좌 주문체결내역 전체 페이지를 비동기 방식으로 연속조회합니다 (``occurs_req`` 와 같은 규칙)."""
        return await self._generic.header_occurs_req_async(callback=callback, delay=delay, max_pages=max_pages)


__all__ = [
    TrCSPAQ13700,
    CSPAQ13700InBlock1,
    CSPAQ13700OutBlock1,
    CSPAQ13700OutBlock2,
    CSPAQ13700OutBlock3,
    CSPAQ13700Request,
    CSPAQ13700Response,
    CSPAQ13700ResponseHeader,
]
