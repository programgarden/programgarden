import aiohttp

from typing import Dict, Any, Optional
from programgarden_core.exceptions import TrRequestDataNotFoundException
from ....tr_helpers import GenericTR
from .blocks import (
    O3121OutBlock,
    O3121Request,
    O3121Response,
    O3121InBlock,
    O3121ResponseHeader
)
from ....tr_base import TRRequestAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3121(TRRequestAbstract):
    """
    LS증권 OpenAPI의 o3121 해외선물옵션 마스터 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3121Request,
    ):
        """
        TrO3121 생성자

        Args:
            request_data (O3121Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3121Request):
            raise TrRequestDataNotFoundException()
        self._generic: GenericTR[O3121Response] = GenericTR(self.request_data, self._build_response, url=URLS.FO_MARKET_URL)

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3121Response:
        if exc is not None:
            pg_logger.error(f"o3121 request failed: {exc}")
            return O3121Response(header=None, block=[], rsp_cd="", rsp_msg="", error_msg=str(exc))

        header = O3121ResponseHeader.model_validate(resp_headers)
        blocks = [O3121OutBlock.model_validate(item) for item in resp_json.get("o3121OutBlock", [])]

        result = O3121Response(
            header=header,
            block=blocks,
            rsp_cd=resp_json.get("rsp_cd", ""),
            rsp_msg=resp_json.get("rsp_msg", ""),
        )
        result.raw_data = resp
        return result

    def req(self) -> O3121Response:
        return self._generic.req()

    async def req_async(self) -> O3121Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3121Response:

        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            result = O3121Response(
                header=O3121ResponseHeader.model_validate(resp_headers),
                block=[O3121OutBlock.model_validate(item) for item in resp_json.get("o3121OutBlock", [])],
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp

            return result

        except aiohttp.ClientError as e:
            pg_logger.error(f"o3121 비동기 요청 실패: {e}")

            return O3121Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3121 비동기 요청 중 예외 발생: {e}")

            return O3121Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )


__all__ = [
    TrO3121,
    O3121OutBlock,
    O3121Request,
    O3121Response,
    O3121InBlock,
    O3121ResponseHeader,
]
