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
        if exc is not None:
            return CIDBT01000Response(header=None, block1=None, block2=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        block1 = resp_json.get("CIDBT01000OutBlock1", None)
        block2 = resp_json.get("CIDBT01000OutBlock2", None)
        result = CIDBT01000Response(
            header=CIDBT01000ResponseHeader.model_validate(resp_headers),
            block1=CIDBT01000OutBlock1.model_validate(block1) if block1 is not None else None,
            block2=CIDBT01000OutBlock2.model_validate(block2) if block2 is not None else None,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
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
