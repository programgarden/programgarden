from typing import Dict, Any, Optional

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3101OutBlock,
    O3101Request,
    O3101Response,
    O3101InBlock,
    O3101ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3101(TRRequestAbstract):
    """
    LS증권 OpenAPI의 o3101 종목 마스터 내역 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3101Request,
    ):
        """
        TrO3101 생성자

        Args:
            request_data (O3101Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3101Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3101Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3101Response:
        if exc is not None:
            pg_logger.error(f"o3101 request failed: {exc}")
            return O3101Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(exc),
            )

        resp_json = resp_json or {}
        blocks = resp_json.get("o3101OutBlock", [])
        header = O3101ResponseHeader.model_validate(resp_headers)
        blocks = [O3101OutBlock.model_validate(item) for item in blocks]

        result = O3101Response(
            header=header,
            block=blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3101Response:
        return self._generic.req()

    async def req_async(self) -> O3101Response:
        return await self._generic.req_async()


__all__ = [
    TrO3101,
    O3101OutBlock,
    O3101Request,
    O3101Response,
    O3101InBlock,
    O3101ResponseHeader,
]
