
from typing import Optional, Callable, Dict, Any

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSOQ00201InBlock1,
    COSOQ00201OutBlock1,
    COSOQ00201OutBlock2,
    COSOQ00201Request,
    COSOQ00201Response,
    COSOQ00201ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS


class TrCOSOQ00201(TRAccnoAbstract):
    """LS openAPI의 COSOQ00201 해외주식 종합잔고평가를 조회하는 클래스입니다.

    Uses GenericTR to standardize request/response flow.
    """

    def __init__(self, request_data: COSOQ00201Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSOQ00201Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSOQ00201Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSOQ00201Response:
        if exc is not None:
            return COSOQ00201Response(
                header=None,
                block1=None,
                block2=None,
                block3=[],
                block4=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(exc),
            )

        resp_json = resp_json or {}
        block1 = resp_json.get("COSOQ00201OutBlock1", None)
        block2 = resp_json.get("COSOQ00201OutBlock2", None)

        result = COSOQ00201Response(
            header=COSOQ00201ResponseHeader.model_validate(resp_headers),
            block1=COSOQ00201OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=COSOQ00201OutBlock2.model_validate(block2) if block2 is not None else None,
            block3=[item for item in resp_json.get("COSOQ00201OutBlock3", [])],
            block4=[item for item in resp_json.get("COSOQ00201OutBlock4", [])],
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    async def req_async(self) -> COSOQ00201Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSOQ00201Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSOQ00201Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSOQ00201Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSOQ00201Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSOQ00201Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSOQ00201,
    COSOQ00201InBlock1,
    COSOQ00201OutBlock1,
    COSOQ00201OutBlock2,
    COSOQ00201Request,
    COSOQ00201Response,
    COSOQ00201ResponseHeader
]
