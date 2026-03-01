from typing import Callable, Dict, Any, List, Optional

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.CSPAQ12300")

from .blocks import (
    CSPAQ12300InBlock1,
    CSPAQ12300OutBlock1,
    CSPAQ12300OutBlock2,
    CSPAQ12300OutBlock3,
    CSPAQ12300Request,
    CSPAQ12300Response,
    CSPAQ12300ResponseHeader,
)
from ....tr_base import TRAccnoAbstract
from ....tr_helpers import GenericTR
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus


class TrCSPAQ12300(TRAccnoAbstract):
    """
    LS증권 OpenAPI CSPAQ12300 BEP단가조회/현물계좌잔고내역 API용 클래스입니다.

    계좌의 종목별 잔고 내역, BEP 단가, 평가손익 등을 조회합니다.
    """

    def __init__(
        self,
        request_data: CSPAQ12300Request,
    ):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CSPAQ12300Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CSPAQ12300Response] = GenericTR[CSPAQ12300Response](
            self.request_data, self._build_response, url=URLS.KOREA_STOCK_ACCNO_URL
        )

    def _build_response(
        self,
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        resp_headers: Optional[Dict[str, Any]],
        exc: Optional[Exception],
    ) -> CSPAQ12300Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CSPAQ12300OutBlock1", None)
        block2_data = resp_json.get("CSPAQ12300OutBlock2", None)
        block3_data = resp_json.get("CSPAQ12300OutBlock3", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CSPAQ12300ResponseHeader.model_validate(resp_headers)

        parsed_block1: Optional[CSPAQ12300OutBlock1] = None
        parsed_block2: Optional[CSPAQ12300OutBlock2] = None
        parsed_block3: List[CSPAQ12300OutBlock3] = []

        if exc is None and not is_error_status:
            if block1_data:
                parsed_block1 = CSPAQ12300OutBlock1.model_validate(block1_data)
            if block2_data:
                parsed_block2 = CSPAQ12300OutBlock2.model_validate(block2_data)
            if block3_data and isinstance(block3_data, list):
                parsed_block3 = [CSPAQ12300OutBlock3.model_validate(item) for item in block3_data]

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            logger.error(f"CSPAQ12300 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            logger.error(f"CSPAQ12300 request failed with status: {error_msg}")

        result = CSPAQ12300Response(
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

    def req(self) -> CSPAQ12300Response:
        return self._generic.req()

    async def req_async(self) -> CSPAQ12300Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CSPAQ12300Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)
        return await self._generic.req_async()

    async def retry_req_async(
        self,
        callback: Callable[[Optional[CSPAQ12300Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ):
        return await self._generic.retry_req_async(callback, max_retries=max_retries, delay=delay)

    def retry_req(
        self,
        callback: Callable[[Optional[CSPAQ12300Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2,
    ) -> CSPAQ12300Response:
        return self._generic.retry_req(callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrCSPAQ12300,
    CSPAQ12300InBlock1,
    CSPAQ12300OutBlock1,
    CSPAQ12300OutBlock2,
    CSPAQ12300OutBlock3,
    CSPAQ12300Request,
    CSPAQ12300Response,
    CSPAQ12300ResponseHeader,
]
