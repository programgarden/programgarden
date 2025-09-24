from typing import Dict, Any, Optional

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3107OutBlock,
    O3107Request,
    O3107Response,
    O3107InBlock,
    O3107ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3107(TRRequestAbstract):
    """
    LS증권 OpenAPI의 o3107 해외선물 관심종목 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3107Request,
    ):
        """
        TrO3107 생성자

        Args:
            request_data (O3107Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3107Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[O3107Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3107Response:
        if exc is not None:
            pg_logger.error(f"o3107 request failed: {exc}")
            return O3107Response(header=None, block=[], rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        header = O3107ResponseHeader.model_validate(resp_headers)
        blocks = [O3107OutBlock.model_validate(item) for item in resp_json.get("o3107OutBlock", [])]

        result = O3107Response(
            header=header,
            block=blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3107Response:
        return self._generic.req()

    async def req_async(self) -> O3107Response:
        return await self._generic.req_async()


__all__ = [
    TrO3107,
    O3107OutBlock,
    O3107Request,
    O3107Response,
    O3107InBlock,
    O3107ResponseHeader,
]
