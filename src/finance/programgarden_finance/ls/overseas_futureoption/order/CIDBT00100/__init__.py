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
        if exc is not None:
            return CIDBT00100Response(header=None, block1=None, block2=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBT00100OutBlock1", None)
        block2 = resp_json.get("CIDBT00100OutBlock2", None)
        result = CIDBT00100Response(
            header=CIDBT00100ResponseHeader.model_validate(resp_headers),
            block1=CIDBT00100OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=CIDBT00100OutBlock2.model_validate(block2) if block2 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
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
