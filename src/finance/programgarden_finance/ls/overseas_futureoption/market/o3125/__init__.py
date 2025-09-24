import asyncio
import time
from typing import Optional, Callable

import aiohttp
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3125OutBlock,
    O3125Request,
    O3125Response,
    O3125InBlock,
    O3125ResponseHeader
)
from ....tr_base import TRRequestAbstract, RetryReqAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3125(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 o3125 해외선물옵션 현재가(종목정보) 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3125Request,
    ):
        """
        TrO3125 생성자

        Args:
            request_data (O3125Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3125Request):
            raise TrRequestDataNotFoundException()

    def req(self) -> O3125Response:

        try:
            resp, resp_json, resp_headers = self.execute_sync(
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            block = resp_json.get("o3125OutBlock", None)
            result = O3125Response(
                header=O3125ResponseHeader.model_validate(resp_headers),
                block=O3125OutBlock.model_validate(block) if block is not None else None,
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp

            return result

        except requests.RequestException as e:
            pg_logger.error(f"o3125 요청 실패: {e}")

            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3125 요청 중 예외 발생: {e}")

            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

    async def req_async(self) -> O3125Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3125Response:

        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            block = resp_json.get("o3125OutBlock", None)
            response_headers = dict(resp_headers)

            result = O3125Response(
                header=O3125ResponseHeader.model_validate(response_headers),
                block=O3125OutBlock.model_validate(block) if block is not None else None,
                rsp_cd=resp_json.get("rsp_cd", ""),
                rsp_msg=resp_json.get("rsp_msg", ""),
            )
            result.raw_data = resp
            return result

        except aiohttp.ClientError as e:
            pg_logger.error(f"o3125 비동기 요청 실패: {e}")

            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

        except Exception as e:
            pg_logger.error(f"o3125 비동기 요청 중 예외 발생: {e}")

            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )

    def retry_req(
        self,
        callback: Callable[[Optional[O3125Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2
    ) -> O3125Response:
        for attempt in range(max_retries):
            callback(None, RequestStatus.REQUEST)
            response = self.req()

            if response.error_msg is not None:
                callback(response, RequestStatus.FAIL)
            else:
                callback(response, RequestStatus.RESPONSE)

            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                callback(None, RequestStatus.COMPLETE)

        callback(None, RequestStatus.CLOSE)
        return response

    async def retry_req_async(self, callback: Callable[[Optional[O3125Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        try:
            async with aiohttp.ClientSession() as session:
                for attempt in range(max_retries):
                    callback(None, RequestStatus.REQUEST)
                    response = await self._req_async_with_session(session)

                    if response.error_msg is not None:
                        callback(response, RequestStatus.FAIL)
                    else:
                        callback(response, RequestStatus.RESPONSE)

                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        callback(None, RequestStatus.COMPLETE)

                # 최종적으로 모든 시도가 종료되었을 때
                await session.close()
                callback(None, RequestStatus.CLOSE)
                return response

        except aiohttp.ClientError as e:
            pg_logger.error(f"o3125 비동기 재시도 요청 실패: {e}")
            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )
        except Exception as e:
            pg_logger.error(f"o3125 비동기 재시도 요청 중 예외 발생: {e}")

            return O3125Response(
                header=None,
                block=[],
                rsp_cd="",
                rsp_msg="",
                error_msg=str(e),
            )


__all__ = [
    TrO3125,
    O3125OutBlock,
    O3125Request,
    O3125Response,
    O3125InBlock,
    O3125ResponseHeader,
]
