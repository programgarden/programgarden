import asyncio
import time
from typing import Optional, Callable, Dict, Any

import aiohttp
import requests

from programgarden_core.exceptions import TrRequestDataNotFoundException
from .blocks import (
    O3126OutBlock,
    O3126Request,
    O3126Response,
    O3126InBlock,
    O3126ResponseHeader
)
from ....tr_base import TRRequestAbstract, RetryReqAbstract
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.config import URLS
from programgarden_core.logs import pg_logger


class TrO3126(TRRequestAbstract, RetryReqAbstract):
    """
    LS증권 OpenAPI의 o3126 해외선물 현재가(호가) 조회를 위한 클래스입니다.
    """

    def __init__(
        self,
        request_data: O3126Request,
    ):
        """
        TrO3126 생성자

        Args:
            request_data (O3126Request): 조회를 위한 입력 데이터
        """
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data

        if not isinstance(self.request_data, O3126Request):
            raise TrRequestDataNotFoundException()

    def _build_response(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]], resp_headers: Optional[Dict[str, Any]], exc: Optional[Exception]) -> O3126Response:
        resp_json = resp_json or {}
        block_data = resp_json.get("o3126OutBlock")

        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        is_error_status = status is not None and status >= 400

        header = None
        if exc is None and resp_headers and not is_error_status:
            header = O3126ResponseHeader.model_validate(dict(resp_headers))

        parsed_block = None
        if exc is None and not is_error_status and block_data is not None:
            parsed_block = O3126OutBlock.model_validate(block_data)

        error_msg = ""
        if exc is not None:
            error_msg = str(exc)
            pg_logger.error(f"o3126 request failed: {exc}")
        elif is_error_status:
            error_msg = f"HTTP {status}"
            if resp_json.get("rsp_msg"):
                error_msg = f"{error_msg}: {resp_json['rsp_msg']}"
            pg_logger.error(f"o3126 request failed with status: {error_msg}")

        result = O3126Response(
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

    def req(self) -> O3126Response:

        try:
            resp, resp_json, resp_headers = self.execute_sync(
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            return self._build_response(resp, resp_json, resp_headers, None)

        except requests.RequestException as e:
            return self._build_response(None, None, None, e)

        except Exception as e:
            return self._build_response(None, None, None, e)

    async def req_async(self) -> O3126Response:
        async with aiohttp.ClientSession() as session:
            return await self._req_async_with_session(session)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> O3126Response:

        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(
                session=session,
                url=URLS.FO_MARKET_URL,
                request_data=self.request_data,
                timeout=10
            )

            return self._build_response(resp, resp_json, resp_headers, None)

        except aiohttp.ClientError as e:
            return self._build_response(None, None, None, e)

        except Exception as e:
            return self._build_response(None, None, None, e)

    def retry_req(
        self,
        callback: Callable[[Optional[O3126Response], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 2
    ) -> O3126Response:
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

    async def retry_req_async(self, callback: Callable[[Optional[O3126Response], RequestStatus], None], max_retries: int = 3, delay: int = 2):
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
            pg_logger.error(f"o3126 비동기 재시도 요청 실패: {e}")
            return self._build_response(None, None, None, e)
        except Exception as e:
            pg_logger.error(f"o3126 비동기 재시도 요청 중 예외 발생: {e}")
            return self._build_response(None, None, None, e)


__all__ = [
    TrO3126,
    O3126OutBlock,
    O3126Request,
    O3126Response,
    O3126InBlock,
    O3126ResponseHeader,
]
