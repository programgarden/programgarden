from typing import Optional, Dict, Any

import aiohttp

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    CIDBT00900InBlock1,
    CIDBT00900OutBlock1,
    CIDBT00900OutBlock2,
    CIDBT00900Request,
    CIDBT00900Response,
    CIDBT00900ResponseHeader,
)
from ....tr_base import TROrderAbstract
from programgarden_finance.ls.config import URLS


class TrCIDBT00900(TROrderAbstract):
    """
    LS증권 OpenAPI의 CIDBT00900 해외선물 정정주문을 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: CIDBT00900Request,
    ):
        """
        TrCIDBT00900 생성자

        Args:
            request_data (CIDBT00900Request): 해외선물 정정주문을 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, CIDBT00900Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[CIDBT00900Response] = GenericTR(
            self.request_data, self._build_response, url=URLS.FO_ORDER_URL
        )

    async def req_async(self) -> CIDBT00900Response:
        """
        비동기적으로 해외선물 정정주문을 요청합니다.

        Returns:
            CIDBT00900Response: 요청 결과를 포함하는 응답 객체
        """

        return await self._generic.req_async()

    def req(self) -> CIDBT00900Response:
        return self._generic.req()

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> CIDBT00900Response:
        if hasattr(self._generic, "_req_async_with_session"):
            return await self._generic._req_async_with_session(session)

        return await self._generic.req_async()

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> CIDBT00900Response:
        if exc is not None:
            return CIDBT00900Response(header=None, block1=None, block2=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBT00900OutBlock1", None)
        block2 = resp_json.get("CIDBT00900OutBlock2", None)
        result = CIDBT00900Response(
            header=CIDBT00900ResponseHeader.model_validate(resp_headers),
            block1=CIDBT00900OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=CIDBT00900OutBlock2.model_validate(block2) if block2 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result


__all__ = [
    TrCIDBT00900,
    CIDBT00900InBlock1,
    CIDBT00900OutBlock1,
    CIDBT00900OutBlock2,
    CIDBT00900Request,
    CIDBT00900Response,
    CIDBT00900ResponseHeader
]
