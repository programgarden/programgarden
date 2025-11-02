from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    CIDBT01000InBlock1,
    CIDBT01000OutBlock1,
    CIDBT01000OutBlock2,
    CIDBT01000Request,
    CIDBT01000Response,
    CIDBT01000ResponseHeader,
)
from ....tr_base import TROrderAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrCIDBT01000(TROrderAbstract):
    """
    LS증권 OpenAPI의 CIDBT01000 해외선물 취소주문을 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: CIDBT01000Request,
    ):
        """
        TrCIDBT01000 생성자

        Args:
            request_data (CIDBT01000Request): 해외선물 취소주문을 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBT01000Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[CIDBT01000Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_ORDER_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBT01000Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CIDBT01000OutBlock1")
        block2_data = resp_json.get("CIDBT01000OutBlock2")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CIDBT01000ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        if exc is None and not is_error_status:
            if block1_data is not None:
                parsed_block1 = CIDBT01000OutBlock1.model_validate(block1_data)
            if block2_data is not None:
                parsed_block2 = CIDBT01000OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"CIDBT01000 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"CIDBT01000 request failed with status: {error_msg}")

        result = CIDBT01000Response(
            header=header,
            block1=parsed_block1,
            block2=parsed_block2,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
            result.raw_data = resp
        return result

    def req(self) -> CIDBT01000Response:
        return self._generic.req()

    async def req_async(self) -> CIDBT01000Response:
        return await self._generic.req_async()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBT01000Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()


__all__ = [
    TrCIDBT01000,
    CIDBT01000InBlock1,
    CIDBT01000OutBlock1,
    CIDBT01000OutBlock2,
    CIDBT01000Request,
    CIDBT01000Response,
    CIDBT01000ResponseHeader
]
