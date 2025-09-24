import aiohttp
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3127OutBlock,
    O3127Request,
    O3127Response,
    O3127InBlock,
    O3127InBlock1,
    O3127ResponseHeader,
)
from ....tr_base import TRRequestAbstract
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3127(TRRequestAbstract):
    """
    LS증권 OpenAPI의 o3127 해외선물 관심종목 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3127Request,
    ):
        """
        TrO3127 생성자

        Args:
            request_data (O3127Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3127Request):
            raise TrRequestDataNotFoundException()

    def req(self) -> O3127Response:

        try:
            resp, resp_json, resp_headers = self.execute_sync(
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            result = O3127Response(
                header=O3127ResponseHeader.model_validate(resp_headers),
                block=[O3127OutBlock.model_validate(item) for item in resp_json.get("o3127OutBlock", [])],
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp

            return result

        except requests.RequestException as e:
            pg_logger.error(f"o3127 요청 실패: {e}")

            return O3127Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3127 요청 중 예외 발생: {e}")

            return O3127Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

    async def req_async(self) -> O3127Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3127Response:

        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            result = O3127Response(
                header=O3127ResponseHeader.model_validate(resp_headers),
                block=[O3127OutBlock.model_validate(item) for item in resp_json.get("o3127OutBlock", [])],
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp

            return result

        except aiohttp.ClientError as e:
            pg_logger.error(f"o3127 비동기 요청 실패: {e}")

            return O3127Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3127 비동기 요청 중 예외 발생: {e}")

            return O3127Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )


__all__ = [
    TrO3127,
    O3127OutBlock,
    O3127Request,
    O3127Response,
    O3127InBlock,
    O3127InBlock1,
    O3127ResponseHeader,
]
