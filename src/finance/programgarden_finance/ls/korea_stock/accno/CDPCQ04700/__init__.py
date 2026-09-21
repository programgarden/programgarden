from typing import Callable, Dict, Any, List, Optional
from copy import deepcopy

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
import logging

logger = logging.getLogger("programgarden.ls.korea_stock.accno.CDPCQ04700")

from .blocks import (
    CDPCQ04700InBlock1,
    CDPCQ04700OutBlock1,
    CDPCQ04700OutBlock2,
    CDPCQ04700OutBlock3,
    CDPCQ04700OutBlock4,
    CDPCQ04700OutBlock5,
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

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        parse_error = None
        if exc is None and resp_headers and not is_error_status:
            try:
                header = CDPCQ04700ResponseHeader.model_validate(resp_headers)
            except (ValueError, TypeError):
                parse_error = "Malformed CDPCQ04700 response header"

        parsed_blocks: Dict[str, Any] = {}
        if exc is None and not is_error_status and parse_error is None:
            for index, model in enumerate((CDPCQ04700OutBlock1, CDPCQ04700OutBlock2,
                                           CDPCQ04700OutBlock3, CDPCQ04700OutBlock4,
                                           CDPCQ04700OutBlock5), start=1):
                key = f"CDPCQ04700OutBlock{index}"
                if key not in resp_json:
                    continue  # A model default is not an explicitly returned block.
                raw = resp_json[key]
                try:
                    if index == 3:
                        if not isinstance(raw, list):
                            raise ValueError("Expected a detail array")
                        parsed = [model.model_validate(item) for item in raw]
                    else:
                        if raw is not None and not isinstance(raw, dict):
                            raise ValueError("Expected a summary object")
                        parsed = model.model_validate(raw) if raw is not None else None
                    parsed_blocks[f"block{index}"] = parsed
                except (ValueError, TypeError):
                    # Never include raw account fields from a ValidationError.
                    parse_error = f"Malformed {key} response"
                    parsed_blocks = {}
                    break

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = f"Request failed: {type(exc).__name__}"
            logger.error("CDPCQ04700 request failed: %s", type(exc).__name__)
        elif is_error_status:
            error_msg = f"HTTP {status}"
            # The original message remains available on the private response.
            logger.error("CDPCQ04700 request failed with HTTP %s", status)
        elif parse_error:
            error_msg = parse_error

        result = CDPCQ04700Response(
            header=header,
            **parsed_blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        result._raw_payload = deepcopy(resp_json)
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
    CDPCQ04700OutBlock4,
    CDPCQ04700OutBlock5,
    CDPCQ04700Request,
    CDPCQ04700Response,
    CDPCQ04700ResponseHeader,
]
