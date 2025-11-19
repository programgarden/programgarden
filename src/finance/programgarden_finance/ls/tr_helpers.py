import asyncio
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Generic

import aiohttp

from programgarden_core.exceptions import TokenNotFoundException
from programgarden_core.logs import pg_logger
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.token_manager import TokenManager
from .tr_base import TRAccnoAbstract


R = TypeVar("R")


ResponseBuilder = Callable[[Optional[object], Optional[dict], Optional[dict], Optional[Exception]], R]


class GenericTR(TRAccnoAbstract, Generic[R]):
    """
    범용 TR 핸들러입니다. 공통적인 동기/비동기 요청 처리, 예외 처리, 재시도 로직을 제공합니다.

    TR별로 "response_builder"만 구현하면 됩니다. response_builder는
    (resp, resp_json, resp_headers, exc) -> ResponseObject 를 반환해야 합니다.
    """

    _EXPIRED_TOKEN_KEYWORDS = (
        "기간이 만료된 token",
        "token expired",
        "token 만료",
    )

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
        options = getattr(request_data, "options", None)
        self._token_manager: Optional[TokenManager] = getattr(options, "token_manager", None)

    async def _execute_async_with_retry(self, session: aiohttp.ClientSession) -> Tuple[Optional[object], Optional[dict], Optional[dict]]:
        resp, resp_json, resp_headers = await self.execute_async_with_session(session, self._url, self.request_data, timeout=10)

        if self._should_retry_due_to_expired(resp, resp_json):
            retry_payload = await self._retry_after_refresh_async(session)
            if retry_payload is not None:
                resp, resp_json, resp_headers = retry_payload

        return resp, resp_json, resp_headers

    def _execute_sync_with_retry(self) -> Tuple[Optional[object], Optional[dict], Optional[dict]]:
        resp, resp_json, resp_headers = self.execute_sync(self._url, self.request_data, timeout=10)

        if self._should_retry_due_to_expired(resp, resp_json):
            retry_payload = self._retry_after_refresh_sync()
            if retry_payload is not None:
                resp, resp_json, resp_headers = retry_payload

        return resp, resp_json, resp_headers

    def _extract_status_code(self, resp: Optional[object]) -> Optional[int]:
        if resp is None:
            return None
        return getattr(resp, "status", getattr(resp, "status_code", None))

    def _should_retry_due_to_expired(self, resp: Optional[object], resp_json: Optional[Dict[str, Any]]) -> bool:
        if self._token_manager is None:
            return False

        status = self._extract_status_code(resp)
        if status is None or status < 400:
            return False

        # 401 Unauthorized or 403 Forbidden are strong indicators of token issues
        if status in (401, 403):
            return True

        message = ""
        if isinstance(resp_json, dict):
            message = str(resp_json.get("rsp_msg") or resp_json.get("error_msg") or "").lower()

        if not message:
            return False

        return any(keyword in message for keyword in self._EXPIRED_TOKEN_KEYWORDS)

    def _retry_after_refresh_sync(self) -> Optional[Tuple[Optional[object], Optional[dict], Optional[dict]]]:
        if self._token_manager is None:
            return None
        if not self._token_manager.ensure_fresh_token(force_refresh=True):
            return None
        self._update_authorization_header()
        try:
            return self.execute_sync(self._url, self.request_data, timeout=10)
        except Exception as exc:  # pragma: no cover - propagate error handling to caller
            pg_logger.error(f"토큰 재발급 후 동기 재시도 실패: {exc}")
            return None

    async def _retry_after_refresh_async(self, session: aiohttp.ClientSession) -> Optional[Tuple[Optional[object], Optional[dict], Optional[dict]]]:
        if self._token_manager is None:
            return None

        refreshed = await self._token_manager.ensure_fresh_token_async(force_refresh=True)
        if not refreshed:
            return None

        self._update_authorization_header()

        try:
            return await self.execute_async_with_session(session, self._url, self.request_data, timeout=10)
        except Exception as exc:  # pragma: no cover - propagate error handling to caller
            pg_logger.error(f"토큰 재발급 후 비동기 재시도 실패: {exc}")
            return None

    def _update_authorization_header(self) -> None:
        if self._token_manager is None or not hasattr(self.request_data, "header"):
            return

        try:
            self.request_data.header.authorization = self._token_manager.get_bearer_token()
        except TokenNotFoundException:
            pass

    async def req_async(self) -> R:
        try:
            async with aiohttp.ClientSession() as session:
                resp, resp_json, resp_headers = await self._execute_async_with_retry(session)
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
            resp, resp_json, resp_headers = await self._execute_async_with_retry(session)
            result: R = self._response_builder(resp, resp_json, resp_headers, None)
            if hasattr(result, "raw_data"):
                result.raw_data = resp
            return result

        except Exception as e:
            pg_logger.error(f"GenericTR._req_async_with_session 비동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    def req(self) -> R:
        try:
            resp, resp_json, resp_headers = self._execute_sync_with_retry()
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
