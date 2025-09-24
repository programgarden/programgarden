from typing import Dict, Any, Optional

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3104OutBlock1,
    O3104Request,
    O3104Response,
    O3104InBlock,
    O3104ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3104(TRRequestAbstract):
    """
    LS증권 OpenAPI의 o3104 해외선물 일별체결 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3104Request,
    ):
        """
        TrO3104 생성자

        Args:
            request_data (O3104Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3104Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3104Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3104Response:
        if exc is not None:
            pg_logger.error(f"o3104 request failed: {exc}")
            return O3104Response(header=None, block1=[], rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        header = O3104ResponseHeader.model_validate(resp_headers)
        blocks = [O3104OutBlock1.model_validate(item) for item in resp_json.get("o3104OutBlock1", [])]

        result = O3104Response(
            header=header,
            block1=blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3104Response:
        return self._generic.req()

    async def req_async(self) -> O3104Response:
        return await self._generic.req_async()


__all__ = [
    TrO3104,
    O3104OutBlock1,
    O3104Request,
    O3104Response,
    O3104InBlock,
    O3104ResponseHeader,
]
