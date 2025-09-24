from typing import Optional, Callable, Dict, Any

from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3105OutBlock,
    O3105Request,
    O3105Response,
    O3105InBlock,
    O3105ResponseHeader,
)
from ....tr_base import TRRequestAbstract, RetryReqAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3105(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 o3105 해외선물 현재가(종목정보) 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3105Request,
    ):
        """
        TrO3105 생성자

        Args:
            request_data (O3105Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3105Request):
            raise TrRequestDataNotFoundException()

        self._generic: GenericTR[O3105Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3105Response:
        if exc is not None:
            pg_logger.error(f"o3105 request failed: {exc}")
            return O3105Response(header=None, block=None, rsp_cd="", rsp_msg="", error_msg=str(exc))

        resp_json = resp_json or {}
        header = O3105ResponseHeader.model_validate(resp_headers)
        block_data = resp_json.get("o3105OutBlock", None)
        block = O3105OutBlock.model_validate(block_data) if block_data is not None else None

        result = O3105Response(
            header=header,
            block=block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3105Response:
        return self._generic.req()

    async def req_async(self) -> O3105Response:
        return await self._generic.req_async()

    def retry_req(self, callback: Callable[[Optional[O3105Response], RequestStatus], None], max_retries: int = 3, delay: int = 2) -> O3105Response:
        return self._generic.retry_req(callback=callback, max_retries=max_retries, delay=delay)

    async def retry_req_async(self, callback: Callable[[Optional[O3105Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        return await self._generic.retry_req_async(callback=callback, max_retries=max_retries, delay=delay)


__all__ = [
    TrO3105,
    O3105OutBlock,
    O3105Request,
    O3105Response,
    O3105InBlock,
    O3105ResponseHeader,
]
