from typing import Optional, Callable, Dict, Any

from ....tr_helpers import GenericTR

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    COSOQ02701InBlock1,
    COSOQ02701OutBlock1,
    COSOQ02701OutBlock2,
    COSOQ02701OutBlock3,
    COSOQ02701OutBlock4,
    COSOQ02701OutBlock5,
    COSOQ02701Request,
    COSOQ02701Response,
    COSOQ02701ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrCOSOQ02701(TRAccnoAbstract):
    """LS OpenAPI의 COSOQ02701 외화 예수금 및 주문 가능 금액을 조회하는 클래스입니다.

    Uses GenericTR for consistent behavior and error propagation.
    """

    def __init__(self, request_data: COSOQ02701Request):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, COSOQ02701Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[COSOQ02701Response] = GenericTR(self.request_data, self._build_response, url=URLS.ACCNO_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> COSOQ02701Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("COSOQ02701OutBlock1")
        block2_data = resp_json.get("COSOQ02701OutBlock2", [])
        block3_data = resp_json.get("COSOQ02701OutBlock3", [])
        block4_data = resp_json.get("COSOQ02701OutBlock4")
        block5_data = resp_json.get("COSOQ02701OutBlock5")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = COSOQ02701ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2: list[COSOQ02701OutBlock2] = []
        parsed_block3: list[COSOQ02701OutBlock3] = []
        parsed_block4 = None
        parsed_block5 = None
        if exc is None and not is_error_status:
            if block1_data is not None:
                parsed_block1 = COSOQ02701OutBlock1.model_validate(block1_data)
            parsed_block2 = [COSOQ02701OutBlock2.model_validate(item) for item in block2_data]
            parsed_block3 = [COSOQ02701OutBlock3.model_validate(item) for item in block3_data]
            if block4_data is not None:
                parsed_block4 = COSOQ02701OutBlock4.model_validate(block4_data)
            if block5_data is not None:
                parsed_block5 = COSOQ02701OutBlock5.model_validate(block5_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"COSOQ02701 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"COSOQ02701 request failed with status: {error_msg}")

        result = COSOQ02701Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            block3=parsed_block3,
            block4=parsed_block4,
            block5=parsed_block5,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )

        if resp is not None:
            result.raw_data = resp
        return result

    async def req_async(self) -> COSOQ02701Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session) -> COSOQ02701Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def req(self) -> COSOQ02701Response:
        return self._generic.req()

    async def retry_req_async(self, callback: Callable[[Optional[COSOQ02701Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(self, callback: Callable[[Optional[COSOQ02701Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> COSOQ02701Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCOSOQ02701,
    COSOQ02701InBlock1,
    COSOQ02701OutBlock1,
    COSOQ02701OutBlock2,
    COSOQ02701OutBlock3,
    COSOQ02701OutBlock4,
    COSOQ02701OutBlock5,
    COSOQ02701Request,
    COSOQ02701Response,
    COSOQ02701ResponseHeader
]
