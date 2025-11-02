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
        resp_json = resp_json or {}
        blocks = resp_json.get("o3104OutBlock1", [])

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3104ResponseHeader.model_validate(resp_headers)

        parsed_blocks: list[O3104OutBlock1] = []
        if exc is None and not is_error_status:
            parsed_blocks = [O3104OutBlock1.model_validate(item) for item in blocks]

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"o3104 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"o3104 request failed with status: {error_msg}")

        result = O3104Response(
            header=header,
            block1=parsed_blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
            status_code=status,
            error_msg=error_msg,
        )
        if resp is not None:
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
