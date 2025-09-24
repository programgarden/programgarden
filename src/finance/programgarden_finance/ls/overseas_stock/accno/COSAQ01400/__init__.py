
from typing import Optional, Callable, Dict, Any

import aiohttp

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSAQ01400InBlock1,
    COSAQ01400OutBlock1,
    COSAQ01400OutBlock2,
    COSAQ01400Request,
    COSAQ01400Response,
    COSAQ01400ResponseHeader
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCOSAQ01400(TRAccnoAbstract):
    """
    LS증권 OpenAPI의 COSAQ01400 계좌 주문 내역 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: COSAQ01400Request,
    ):
        """
        TrCOSAQ01400 생성자

        Args:
            request_data (COSAQ01400Request): 주문 내역 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSAQ01400Request):
            raise TrRequestDataNotFoundException()

        # annotate generic for better static typing / IDE help
        # use an instance method _build_response (defined below) so it's available
        # even if callers access helpers after construction
        self._generic: GenericTR[COSAQ01400Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSAQ01400Response:
        if exc is not None:
            return COSAQ01400Response(
                header=None,
                block1=None,
                block2=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(exc),
            )

        # resp_json may be None in error cases, guard accordingly
        resp_json = resp_json or {}
        block1 = resp_json.get("COSAQ01400OutBlock1", None)
        block2 = resp_json.get("COSAQ01400OutBlock2", [])
        result = COSAQ01400Response(
            header=COSAQ01400ResponseHeader.model_validate(resp_headers),
            block1=COSAQ01400OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=[COSAQ01400OutBlock2.model_validate(item) for item in block2],
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    async def req_async(self) -> COSAQ01400Response:
        """
        비동기적으로 해외주식 계좌 주문 내역을 요청합니다.

        Returns:
            COSAQ01400Response: 요청 결과를 포함하는 응답 객체
        """

        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> COSAQ01400Response:
        # kept for backward compatibility if other modules call this helper directly
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSAQ01400Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSAQ01400Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(
        self,
        callback: Callable[[Optional[COSAQ01400Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2
    ) -> COSAQ01400Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSAQ01400,
    COSAQ01400InBlock1,
    COSAQ01400OutBlock1,
    COSAQ01400OutBlock2,
    COSAQ01400Request,
    COSAQ01400Response,
    COSAQ01400ResponseHeader
]
