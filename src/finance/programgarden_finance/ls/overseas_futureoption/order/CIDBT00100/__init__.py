from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    CIDBT00100InBlock1,
    CIDBT00100OutBlock1,
    CIDBT00100OutBlock2,
    CIDBT00100Request,
    CIDBT00100Response,
    CIDBT00100ResponseHeader,
)
from ....tr_base import TROrderAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrCIDBT00100(TROrderAbstract):
    """
    LS증권 OpenAPI의 CIDBT00100 해외선물 신규주문을 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: CIDBT00100Request,
    ):
        """
        TrCIDBT00100 생성자

        Args:
            request_data (CIDBT00100Request): 해외선물 신규주문을 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBT00100Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[CIDBT00100Response] = GenericTR(
            self.request_data, self._build_response, url=URLS.FO_ORDER_URL
        )

    async def req_async(self) -> CIDBT00100Response:
        """
        비동기적으로 해외선물 신규주문을 요청합니다.

        Returns:
            CIDBT00100Response: 요청 결과를 포함하는 응답 객체
        """

        return await self._generic.req_async()

    def req(self) -> CIDBT00100Response:
        return self._generic.req()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBT00100Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBT00100Response:
        resp_json = resp_json or {}
        block1_data = resp_json.get("CIDBT00100OutBlock1")
        block2_data = resp_json.get("CIDBT00100OutBlock2")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = CIDBT00100ResponseHeader.model_validate(resp_headers)

        parsed_block1 = None
        parsed_block2 = None
        if exc is None and not is_error_status:
            if block1_data is not None:
                parsed_block1 = CIDBT00100OutBlock1.model_validate(block1_data)
            if block2_data is not None:
                parsed_block2 = CIDBT00100OutBlock2.model_validate(block2_data)

        error_msg: Optional[str] = None
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"CIDBT00100 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"CIDBT00100 request failed with status: {error_msg}")

        result = CIDBT00100Response(
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


__all__ = [
    TrCIDBT00100,
    CIDBT00100InBlock1,
    CIDBT00100OutBlock1,
    CIDBT00100OutBlock2,
    CIDBT00100Request,
    CIDBT00100Response,
    CIDBT00100ResponseHeader
]
