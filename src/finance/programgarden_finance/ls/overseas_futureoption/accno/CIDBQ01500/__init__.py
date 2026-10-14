from typing import Callable, Optional, Dict, Any, List

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    CIDBQ01500InBlock1,
    CIDBQ01500OutBlock1,
    CIDBQ01500OutBlock2,
    CIDBQ01500Request,
    CIDBQ01500Response,
    CIDBQ01500ResponseHeader,
)
from ....tr_base import OccursReqAbstract, TRAccnoAbstract
from ....tr_helpers import DEFAULT_OCCURS_MAX_PAGES, GenericTR
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCIDBQ01500(TRAccnoAbstract, OccursReqAbstract):
    def __init__(self, request_data: CIDBQ01500Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBQ01500Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CIDBQ01500Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_ACCNO_URL)

    # TODO: tr_cd, tr_msg 여기서 추출해서 response에 넣기
    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBQ01500Response:
        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBQ01500OutBlock1", None)
        block2 = resp_json.get("CIDBQ01500OutBlock2", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CIDBQ01500ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = []
        if exc is None and not is_error_status:
            if block1 is not None:
                parsed_block1 = CIDBQ01500OutBlock1.model_validate(block1)
            parsed_block2 = [CIDBQ01500OutBlock2.model_validate(item) for item in block2]

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"

        result = CIDBQ01500Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        # A parser default is not an observed empty list. Preserve presence for
        # fail-closed account and duplicate-order guards.
        if "CIDBQ01500OutBlock2" not in resp_json or exc is not None or is_error_status:
            result.model_fields_set.discard("block2")
        result.raw_data = resp

        return result

    def req(self) -> CIDBQ01500Response:
        return self._generic.req()

    async def req_async(self) -> CIDBQ01500Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBQ01500Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    async def retry_req_async(self, callback: Callable[[Optional[CIDBQ01500Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[CIDBQ01500Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> CIDBQ01500Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)

    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[CIDBQ01500Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[CIDBQ01500Response]:
        """해외선물 미결제잔고내역 전체 페이지를 동기 방식으로 연속조회합니다.

        다음 페이지는 같은 본문에 요청 헤더 ``tr_cont="Y"`` 와 직전 응답의
        ``tr_cont_key`` 를 실어 다시 보냅니다(가이드 공통 헤더). 이 TR 의 blocks 에는
        본문 연속조회 필드가 없어 본문은 바꾸지 않습니다. 페이지마다 이 TR 의
        rate limit 을 지키고, 페이지 사이에 ``delay`` 초를 쉽니다.

        Returns:
            List[CIDBQ01500Response]: 페이지별 응답(행을 합치지 않음). 실패한 페이지는 마지막
            원소로 남고, 키가 비었거나 반복되거나 ``max_pages`` 에 닿으면 마지막
            성공 페이지(여전히 ``tr_cont="Y"``)에서 멈춥니다. 전부 받았는지는
            ``programgarden_finance.ls.tr_helpers.occurs_complete(pages)`` 로 확인하세요.
        """
        return self._generic.header_occurs_req(callback=callback, delay=delay, max_pages=max_pages)

    async def occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[CIDBQ01500Response], RequestStatus], None]] = None,
        delay: int = 1,
        *,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> List[CIDBQ01500Response]:
        """해외선물 미결제잔고내역 전체 페이지를 비동기 방식으로 연속조회합니다 (``occurs_req`` 와 같은 규칙)."""
        return await self._generic.header_occurs_req_async(callback=callback, delay=delay, max_pages=max_pages)


__all__ = [
    TrCIDBQ01500,
    CIDBQ01500InBlock1,
    CIDBQ01500OutBlock1,
    CIDBQ01500OutBlock2,
    CIDBQ01500Request,
    CIDBQ01500Response,
    CIDBQ01500ResponseHeader,
]
