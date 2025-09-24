import asyncio
from typing import Callable, Optional, TypeVar, Generic

import aiohttp

from programgarden_core.logs import pg_logger
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus
from .tr_base import TRAccnoAbstract


R = TypeVar("R")


ResponseBuilder = Callable[[Optional[object], Optional[dict], Optional[dict], Optional[Exception]], R]


class GenericTR(TRAccnoAbstract, Generic[R]):
    """
    범용 TR 핸들러입니다. 공통적인 동기/비동기 요청 처리, 예외 처리, 재시도 로직을 제공합니다.

    TR별로 "response_builder"만 구현하면 됩니다. response_builder는
    (resp, resp_json, resp_headers, exc) -> ResponseObject 를 반환해야 합니다.
    """

    def __init__(self, request_data: object, response_builder: ResponseBuilder, url: str = URLS.ACCNO_URL):
        super().__init__(
            rate_limit_count=request_data.options.rate_limit_count,
            rate_limit_seconds=request_data.options.rate_limit_seconds,
            on_rate_limit=request_data.options.on_rate_limit,
            rate_limit_key=request_data.options.rate_limit_key,
        )
        self.request_data = request_data
        self._response_builder = response_builder
        self._url = url

    async def req_async(self) -> R:
        try:
            async with aiohttp.ClientSession() as session:
                resp, resp_json, resp_headers = await self.execute_async_with_session(session, self._url, self.request_data, timeout=10)
                result: R = self._response_builder(resp, resp_json, resp_headers, None)
                if hasattr(result, "raw_data"):
                    result.raw_data = resp
                return result

        except Exception as e:
            pg_logger.error(f"GenericTR 비동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> R:
        """
        Perform the async request using an existing aiohttp session. This mirrors the
        behavior of the original TR-specific `_req_async_with_session` helpers so
        callers that pass a session (for retries or connection reuse) keep working.
        """
        try:
            resp, resp_json, resp_headers = await self.execute_async_with_session(session, self._url, self.request_data, timeout=10)
            result: R = self._response_builder(resp, resp_json, resp_headers, None)
            if hasattr(result, "raw_data"):
                result.raw_data = resp
            return result

        except Exception as e:
            pg_logger.error(f"GenericTR._req_async_with_session 비동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    def req(self) -> R:
        try:
            resp, resp_json, resp_headers = self.execute_sync(self._url, self.request_data, timeout=10)
            result: R = self._response_builder(resp, resp_json, resp_headers, None)
            if hasattr(result, "raw_data"):
                result.raw_data = resp
            return result

        except Exception as e:
            pg_logger.error(f"GenericTR 동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    async def retry_req_async(self, callback: Callable[[Optional[R], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        response: Optional[R] = None
        for attempt in range(max_retries):
            callback(None, RequestStatus.REQUEST)
            response = await self.req_async()

            if getattr(response, "error_msg", None) is not None:
                callback(response, RequestStatus.FAIL)
            else:
                callback(response, RequestStatus.RESPONSE)

            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
            else:
                callback(None, RequestStatus.COMPLETE)

        callback(None, RequestStatus.CLOSE)
        return response

    def retry_req(self, callback: Callable[[Optional[R], RequestStatus], None], max_retries: int = 3, delay: int = 2):
        response: Optional[R] = None
        for attempt in range(max_retries):
            callback(None, RequestStatus.REQUEST)
            response = self.req()

            if getattr(response, "error_msg", None) is not None:
                callback(response, RequestStatus.FAIL)
            else:
                callback(response, RequestStatus.RESPONSE)

            if attempt < max_retries - 1:
                import time

                time.sleep(delay)
            else:
                callback(None, RequestStatus.COMPLETE)

        callback(None, RequestStatus.CLOSE)
        return response

    def occurs_req(self, continuation_updater: Callable[[object, R], None], callback: Optional[Callable[[Optional[R], RequestStatus], None]] = None, delay: int = 1) -> list[R]:
        """
        Synchronous recurring request loop. The caller provides a small
        continuation_updater(request_data, last_response) that mutates
        request_data to prepare the next request (e.g. set tr_cont_key and
        continuation fields).
        """
        results: list[R] = []

        callback and callback(None, RequestStatus.REQUEST)
        response = self.req()
        callback and callback(response, RequestStatus.RESPONSE)
        results.append(response)

        while getattr(response.header, "tr_cont", "N") == "Y":
            callback and callback(response, RequestStatus.OCCURS_REQUEST)

            import time

            time.sleep(delay)

            # allow caller to mutate request_data for next call
            try:
                continuation_updater(self.request_data, response)
            except Exception as e:
                pg_logger.error(f"occurs continuation_updater failed: {e}")
                callback and callback(None, RequestStatus.FAIL)
                break

            response = self.req()

            if getattr(response, "error_msg", None) is not None:
                callback and callback(response, RequestStatus.FAIL)
                break

            results.append(response)
            callback and callback(response, RequestStatus.RESPONSE)

        callback and callback(None, RequestStatus.COMPLETE)
        callback and callback(None, RequestStatus.CLOSE)
        return results

    async def occurs_req_async(self, continuation_updater: Callable[[object, R], None], callback: Optional[Callable[[Optional[R], RequestStatus], None]] = None, delay: int = 1) -> list[R]:
        """
        Async recurring request loop using an aiohttp session. continuation_updater
        runs synchronously (it should be fast and non-blocking) and mutates
        request_data for the next call.
        """
        results: list[R] = []

        async with aiohttp.ClientSession() as session:
            callback and callback(None, RequestStatus.REQUEST)
            response = await self._req_async_with_session(session)
            callback and callback(response, RequestStatus.RESPONSE)
            results.append(response)

            while getattr(response.header, "tr_cont", "N") == "Y":
                callback and callback(response, RequestStatus.OCCURS_REQUEST)

                await asyncio.sleep(delay)

                try:
                    continuation_updater(self.request_data, response)
                except Exception as e:
                    pg_logger.error(f"occurs continuation_updater failed: {e}")
                    callback and callback(None, RequestStatus.FAIL)
                    break

                response = await self._req_async_with_session(session)

                if getattr(response, "error_msg", None) is not None:
                    callback and callback(response, RequestStatus.FAIL)
                    break

                results.append(response)
                callback and callback(response, RequestStatus.RESPONSE)

            callback and callback(None, RequestStatus.COMPLETE)
            await session.close()
            callback and callback(None, RequestStatus.CLOSE)
            return results
