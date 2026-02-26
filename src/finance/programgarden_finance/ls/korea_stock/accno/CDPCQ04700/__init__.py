from typing import Callable, Dict, Any, List, Optional

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.CDPCQ04700")

from .blocks import (
    CDPCQ04700InBlock1,
    CDPCQ04700OutBlock1,
    CDPCQ04700OutBlock2,
    CDPCQ04700OutBlock3,
    CDPCQ04700Request,
    CDPCQ04700Response,
    CDPCQ04700ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrCDPCQ04700(TRAccnoAbstract):
    """
    LS증권 OpenAPI CDPCQ04700 계좌 거래내역 API용 클래스입니다.

    계좌의 기간별 거래내역을 조회합니다.
    """

    def __init__(
        self,
        request_data: CDPCQ04700Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CDPCQ04700Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CDPCQ04700Response] = GenericTR[CDPCQ04700Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> CDPCQ04700Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CDPCQ04700OutBlock1", None)
        block2_data = resp_json.get("CDPCQ04700OutBlock2", None)
        block3_data = resp_json.get("CDPCQ04700OutBlock3", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CDPCQ04700ResponseHeader.model_validate(resp_headers)

        parsed_block1: Optional[CDPCQ04700OutBlock1] = None
        parsed_block2: Optional[CDPCQ04700OutBlock2] = None
        parsed_block3: List[CDPCQ04700OutBlock3] = []

        if exc is None and not is_error_status:
            if block1_data:
                parsed_block1 = CDPCQ04700OutBlock1.model_validate(block1_data)
            if block2_data:
                parsed_block2 = CDPCQ04700OutBlock2.model_validate(block2_data)
            if block3_data and isinstance(block3_data, list):
                parsed_block3 = [CDPCQ04700OutBlock3.model_validate(item) for item in block3_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"CDPCQ04700 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"CDPCQ04700 request failed with status: {error_msg}")

        result = CDPCQ04700Response(
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

    def req(self) -> CDPCQ04700Response:
        return self._generic.req()

    async def req_async(self) -> CDPCQ04700Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CDPCQ04700Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(
        self,
        callback: Callable[[Optional[CDPCQ04700Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(
        self,
        callback: Callable[[Optional[CDPCQ04700Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ) -> CDPCQ04700Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCDPCQ04700,
    CDPCQ04700InBlock1,
    CDPCQ04700OutBlock1,
    CDPCQ04700OutBlock2,
    CDPCQ04700OutBlock3,
    CDPCQ04700Request,
    CDPCQ04700Response,
    CDPCQ04700ResponseHeader,
]
