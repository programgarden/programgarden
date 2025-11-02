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
        resp_json = resp_json or {}
        block_data = resp_json.get("o3105OutBlock", None)

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3105ResponseHeader.model_validate(resp_headers)

        parsed_block: Optional[O3105OutBlock] = None
        if exc is None and not is_error_status and block_data is not None:
            parsed_block = O3105OutBlock.model_validate(block_data)

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"o3105 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"o3105 request failed with status: {error_msg}")

        result = O3105Response(
            header=header,
            block=parsed_block,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
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
