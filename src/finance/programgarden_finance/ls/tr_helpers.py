import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Sequence, Set, Tuple, TypeVar, Generic

import aiohttp

from programgarden_core.exceptions import TokenNotFoundException
from programgarden_finance.ls.config import URLS

logger = logging.getLogger("programgarden.ls.tr_helpers")
from programgarden_finance.ls.status import RequestStatus
from programgarden_finance.ls.token_manager import TokenManager
from programgarden_finance.ls.token_errors import (
    TokenFailureKind,
    TokenReissueLimitExceeded,
    classify_token_failure,
)
from .tr_base import TRAccnoAbstract
from . import replay_transport as _replay


R = TypeVar("R")


ResponseBuilder = Callable[[Optional[object], Optional[dict], Optional[dict], Optional[Exception]], R]


# --- 사용 중 실패 대응 정책 -------------------------------------------------------
# 토큰이 죽었다고 응답이 **말해 주면** 기다릴 이유가 없으므로 즉시 재발급한다.
# 토큰인지 알 수 없는 일시 실패만 간격을 두고 재시도하고, 끝까지 안 되면 마지막으로
# 재발급을 한 번 시도한다. 두 경로 모두 상한이 있다(무한 재시도·재발급 금지).
TRANSIENT_RETRY_DELAYS: Tuple[float, ...] = (0.5, 1.5, 3.0)
TOKEN_REISSUE_RETRY_MAX = 2  # 한 요청 안에서 허용하는 강제 재발급 횟수

# Header-only continuation walks (``header_occurs_req``) stop after this many
# pages even when LS still answers ``tr_cont="Y"``. A walk that stops early is
# reported as incomplete (see :func:`occurs_complete`), never as a full list.
DEFAULT_OCCURS_MAX_PAGES = 100


def transient_retry_delays(retries: Optional[int]) -> Tuple[float, ...]:
    """Return the spaced retry ladder for ``SetupOptions.transient_retries``.

    ``None`` keeps the default ladder (0.5/1.5/3.0 s). ``0`` disables spaced
    retries; ``n`` keeps the first ``n`` delays of the default ladder.
    """
    if retries is None:
        return TRANSIENT_RETRY_DELAYS
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ValueError("transient_retries must be None or a non-negative integer")
    if retries > len(TRANSIENT_RETRY_DELAYS):
        raise ValueError(
            f"transient_retries must not exceed {len(TRANSIENT_RETRY_DELAYS)}"
        )
    return TRANSIENT_RETRY_DELAYS[:retries]


def _page_failed(response: object) -> bool:
    """A page failed when its response carries an error message.

    Some TR builders use ``""`` (not ``None``) for success, so truthiness is the
    only reliable test across TRs.
    """
    return bool(getattr(response, "error_msg", None))


def _continuation_key(response: object) -> Optional[str]:
    """Return the next-page key when LS announced another page, else ``None``."""
    header = getattr(response, "header", None)
    if header is None or getattr(header, "tr_cont", None) != "Y":
        return None
    return getattr(header, "tr_cont_key", "") or ""


def occurs_complete(pages: Sequence[object]) -> bool:
    """Tell whether a continuation walk returned the complete result.

    True only when at least one page was returned, no page carries an error and
    the last page did not announce another page (``tr_cont`` is not ``"Y"``).
    A walk that stopped on a failed page, a missing or repeated continuation key
    or the page limit is incomplete; callers must not present it as a full list.
    """
    if not pages:
        return False
    if any(_page_failed(page) for page in pages):
        return False
    header = getattr(pages[-1], "header", None)
    return header is not None and getattr(header, "tr_cont", None) != "Y"


# 주문/정정/취소 엔드포인트. 5xx·타임아웃은 **주문이 접수됐는지 알 수 없으므로**
# 절대 자동 재시도하지 않는다(중복 주문). 반대로 '토큰 무효' 는 인증 단계에서 거부된
# 것이라 주문이 나가지 않았음이 보장되므로 재발급 후 재시도해도 안전하다.
_MUTATING_URL_SUFFIX = "/order"


class ResponseParseException(Exception):
    """response_builder 가 이미 수신한 HTTP 응답 위에서 실패한 경우 — 파싱/검증
    실패이지 전송 실패가 아니다. error_msg 에 'response parse error:' 접두어가
    실려 하류에서 네트워크 장애와 구분된다 (전에는 둘이 똑같이 보였다)."""

    def __init__(self, original: Exception):
        self.original = original
        super().__init__(f"response parse error: {original}")


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
            account_rate_limit_count=getattr(request_data.options, "account_rate_limit_count", None),
            account_rate_limit_seconds=getattr(request_data.options, "account_rate_limit_seconds", None),
            account_rate_limit_key=getattr(request_data.options, "account_rate_limit_key", None),
        )
        self.request_data = request_data
        self._response_builder = response_builder
        self._url = url
        options = getattr(request_data, "options", None)
        self._token_manager: Optional[TokenManager] = getattr(options, "token_manager", None)

    @property
    def _is_mutating(self) -> bool:
        """주문/정정/취소 엔드포인트인지 여부 (일시 실패 재시도 금지 대상)."""
        return self._url.rstrip("/").endswith(_MUTATING_URL_SUFFIX)

    def _transient_delays(self) -> Tuple[float, ...]:
        """Spaced retry ladder for this request (``SetupOptions.transient_retries``).

        Read at request time so options assigned after construction still apply.
        """
        if _replay.active_transport() is not None:
            return ()  # a recorded answer does not change on retry
        options = getattr(self.request_data, "options", None)
        return transient_retry_delays(getattr(options, "transient_retries", None))

    async def _execute_async_with_retry(self, session: aiohttp.ClientSession) -> Tuple[Optional[object], Optional[dict], Optional[dict]]:
        transient_attempts = 0
        reissues = 0
        delays = self._transient_delays()

        while True:
            # 재발급 single-flight 판정을 위해 **요청을 보내기 직전**의 토큰 세대를 남긴다.
            generation = self._token_generation()
            exc: Optional[BaseException] = None
            resp = resp_json = resp_headers = None
            try:
                resp, resp_json, resp_headers = await self.execute_async_with_session(
                    session, self._url, self.request_data, timeout=10
                )
            except Exception as e:
                exc = e

            kind = classify_token_failure(resp, resp_json, exc)
            detail = self._failure_detail(resp, resp_json, exc)

            if kind is TokenFailureKind.TOKEN_INVALID and reissues < TOKEN_REISSUE_RETRY_MAX:
                if await self._force_reissue_async(generation, kind, detail):
                    reissues += 1
                    continue

            elif kind is TokenFailureKind.TRANSIENT and not self._is_mutating:
                if transient_attempts < len(delays):
                    delay = delays[transient_attempts]
                    transient_attempts += 1
                    logger.warning(
                        "%s 일시 실패 — %.1f초 후 재시도 (%d/%d): %s",
                        self._url, delay, transient_attempts, len(delays),
                        detail,
                    )
                    await asyncio.sleep(delay)
                    continue
                # 간격 재시도를 다 썼는데도 안 되면, 겉으로 안 드러난 토큰 문제일 수 있다.
                # 단, **서버에 닿지도 못한 실패**(네트워크 예외)는 제외한다 — 토큰을 바꿀
                # 이유가 없고, 회선 장애가 재발급 예산을 태워 나중의 진짜 토큰 사고를
                # 막지 못하게 만든다.
                # transient_retries=0 means the caller paces and retries itself;
                # an untried ladder is not evidence of a hidden token problem.
                if (
                    exc is None
                    and transient_attempts > 0
                    and reissues < TOKEN_REISSUE_RETRY_MAX
                    and self._token_manager is not None
                ):
                    if await self._force_reissue_async(generation, kind, detail):
                        # transient_attempts 는 일부러 초기화하지 않는다 — 초기화하면
                        # 재발급마다 지연 사다리가 처음부터 다시 돌아 총 대기가 불어난다.
                        reissues += 1
                        continue

            if exc is not None:
                raise exc
            return resp, resp_json, resp_headers

    def _execute_sync_with_retry(self) -> Tuple[Optional[object], Optional[dict], Optional[dict]]:
        transient_attempts = 0
        reissues = 0
        delays = self._transient_delays()

        while True:
            generation = self._token_generation()
            exc: Optional[BaseException] = None
            resp = resp_json = resp_headers = None
            try:
                resp, resp_json, resp_headers = self.execute_sync(
                    self._url, self.request_data, timeout=10
                )
            except Exception as e:
                exc = e

            kind = classify_token_failure(resp, resp_json, exc)
            detail = self._failure_detail(resp, resp_json, exc)

            if kind is TokenFailureKind.TOKEN_INVALID and reissues < TOKEN_REISSUE_RETRY_MAX:
                if self._force_reissue_sync(generation, kind, detail):
                    reissues += 1
                    continue

            elif kind is TokenFailureKind.TRANSIENT and not self._is_mutating:
                if transient_attempts < len(delays):
                    delay = delays[transient_attempts]
                    transient_attempts += 1
                    logger.warning(
                        "%s 일시 실패 — %.1f초 후 재시도 (%d/%d): %s",
                        self._url, delay, transient_attempts, len(delays),
                        detail,
                    )
                    time.sleep(delay)
                    continue
                # 비동기 경로와 같은 이유로 네트워크 예외는 재발급으로 승격하지 않는다.
                if (
                    exc is None
                    and transient_attempts > 0
                    and reissues < TOKEN_REISSUE_RETRY_MAX
                    and self._token_manager is not None
                ):
                    if self._force_reissue_sync(generation, kind, detail):
                        reissues += 1
                        continue

            if exc is not None:
                raise exc
            return resp, resp_json, resp_headers

    # ------------------------------------------------------------------
    # 강제 재발급
    # ------------------------------------------------------------------
    def _token_generation(self) -> Optional[int]:
        if self._token_manager is None:
            return None
        return getattr(self._token_manager, "token_generation", None)

    def _log_reissue_reason(self, kind: TokenFailureKind, detail: str) -> None:
        if kind is TokenFailureKind.TOKEN_INVALID:
            logger.warning(
                "%s — 응답이 토큰 무효를 알렸다. 재시도 없이 즉시 재발급한다: %s",
                self._url, detail,
            )
        else:
            logger.warning(
                "%s — 간격 재시도를 모두 소진했다. 마지막으로 토큰을 재발급해 본다: %s",
                self._url, detail,
            )

    def _force_reissue_sync(
        self, generation: Optional[int], kind: TokenFailureKind, detail: str
    ) -> bool:
        if self._token_manager is None:
            return False
        if _replay.active_transport() is not None:
            _replay.notify_refused("token_reissue", self._url)
            return False
        self._log_reissue_reason(kind, detail)
        try:
            refreshed = self._token_manager.force_reissue(observed_generation=generation)
        except TokenReissueLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"토큰 강제 재발급 실패(sync): {e}")
            return False
        if not refreshed:
            logger.error("토큰 강제 재발급이 새 토큰을 만들지 못했다(sync).")
            return False
        self._update_authorization_header()
        return True

    async def _force_reissue_async(
        self, generation: Optional[int], kind: TokenFailureKind, detail: str
    ) -> bool:
        if self._token_manager is None:
            return False
        if _replay.active_transport() is not None:
            _replay.notify_refused("token_reissue", self._url)
            return False
        self._log_reissue_reason(kind, detail)
        try:
            refreshed = await self._token_manager.force_reissue_async(
                observed_generation=generation
            )
        except TokenReissueLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"토큰 강제 재발급 실패(async): {e}")
            return False
        if not refreshed:
            logger.error("토큰 강제 재발급이 새 토큰을 만들지 못했다(async).")
            return False
        self._update_authorization_header()
        return True

    @staticmethod
    def _failure_detail(
        resp: Optional[object],
        resp_json: Optional[Dict[str, Any]],
        exc: Optional[BaseException] = None,
    ) -> str:
        """로그·진단용 실패 요약. rsp_cd 만 채우는 경로가 있어 셋을 모두 싣는다."""
        if exc is not None:
            return f"{type(exc).__name__}: {exc}"
        status = getattr(resp, "status", getattr(resp, "status_code", None)) if resp is not None else None
        rsp_cd = rsp_msg = ""
        if isinstance(resp_json, dict):
            rsp_cd = str(resp_json.get("rsp_cd") or "")
            rsp_msg = str(resp_json.get("rsp_msg") or resp_json.get("error_msg") or "")
        return f"HTTP {status} rsp_cd={rsp_cd or '-'} rsp_msg={rsp_msg or '-'}"

    def _update_authorization_header(self) -> None:
        if self._token_manager is None or not hasattr(self.request_data, "header"):
            return

        try:
            self.request_data.header.authorization = self._token_manager.get_bearer_token()
        except TokenNotFoundException:
            pass

    def _build_result(self, resp, resp_json, resp_headers) -> R:
        """수신 완료한 응답을 파싱한다 — 여기서 나는 예외는 전송 실패가 아니라
        파싱 실패이므로 ResponseParseException 으로 감싸 구분한다."""
        try:
            result: R = self._response_builder(resp, resp_json, resp_headers, None)
        except Exception as e:
            raise ResponseParseException(e) from e
        if hasattr(result, "raw_data"):
            result.raw_data = resp
        return result

    async def req_async(self) -> R:
        try:
            async with aiohttp.ClientSession() as session:
                resp, resp_json, resp_headers = await self._execute_async_with_retry(session)
                return self._build_result(resp, resp_json, resp_headers)

        except ResponseParseException as e:
            logger.error(f"GenericTR 응답 파싱 중 예외: {e.original}")
            return self._response_builder(None, None, None, e)
        except Exception as e:
            logger.error(f"GenericTR 비동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    async def _req_async_with_session(self, session: aiohttp.ClientSession) -> R:
        """
        Perform the async request using an existing aiohttp session. This mirrors the
        behavior of the original TR-specific `_req_async_with_session` helpers so
        callers that pass a session (for retries or connection reuse) keep working.
        """
        try:
            resp, resp_json, resp_headers = await self._execute_async_with_retry(session)
            return self._build_result(resp, resp_json, resp_headers)

        except ResponseParseException as e:
            logger.error(f"GenericTR._req_async_with_session 응답 파싱 중 예외: {e.original}")
            return self._response_builder(None, None, None, e)
        except Exception as e:
            logger.error(f"GenericTR._req_async_with_session 비동기 요청 중 예외: {e}")
            return self._response_builder(None, None, None, e)

    def req(self) -> R:
        try:
            resp, resp_json, resp_headers = self._execute_sync_with_retry()
            return self._build_result(resp, resp_json, resp_headers)

        except ResponseParseException as e:
            logger.error(f"GenericTR 응답 파싱 중 예외: {e.original}")
            return self._response_builder(None, None, None, e)
        except Exception as e:
            logger.error(f"GenericTR 동기 요청 중 예외: {e}")
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
                logger.error(f"occurs continuation_updater failed: {e}")
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
                    logger.error(f"occurs continuation_updater failed: {e}")
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

    # ------------------------------------------------------------------
    # Header-only continuation (account TRs without a body cursor)
    # ------------------------------------------------------------------
    @staticmethod
    def _continuation_stop_reason(
        key: str, seen_keys: Set[str], pages: int, max_pages: int
    ) -> Optional[str]:
        """Why a walk must stop although LS announced another page, if it must."""
        if not key.strip():
            return "continuation requested without tr_cont_key"
        if key in seen_keys:
            return "continuation key repeated"
        if pages >= max_pages:
            return f"page limit {max_pages} reached"
        return None

    def _log_continuation_stop(self, reason: str, pages: int) -> None:
        tr_cd = getattr(getattr(self.request_data, "header", None), "tr_cd", "?")
        logger.error(
            "%s continuation stopped after %d page(s): %s — result is incomplete",
            tr_cd, pages, reason,
        )

    def header_occurs_req(
        self,
        callback: Optional[Callable[[Optional[R], RequestStatus], None]] = None,
        delay: float = 1,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> list[R]:
        """Read every page of a TR whose continuation is carried by headers only.

        Each next page re-sends the same body with request header
        ``tr_cont="Y"`` and ``tr_cont_key`` = the previous response's key.
        Every request passes this TR's own rate limiter, and ``delay`` seconds
        are slept between pages.

        Returns the page responses in order; rows are never merged. A failed
        page is kept as the last element. The walk also stops, keeping the last
        successful page (which still says ``tr_cont="Y"``), when the key is
        blank or repeats or ``max_pages`` is reached. Use
        :func:`occurs_complete` to tell a complete result from a partial one.
        The request header's continuation fields are restored afterwards.
        """
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        header = self.request_data.header
        initial = (header.tr_cont, header.tr_cont_key)
        results: list[R] = []
        seen_keys: Set[str] = set()
        try:
            callback and callback(None, RequestStatus.REQUEST)
            response = self.req()
            results.append(response)
            while True:
                if _page_failed(response):
                    callback and callback(response, RequestStatus.FAIL)
                    break
                callback and callback(response, RequestStatus.RESPONSE)
                key = _continuation_key(response)
                if key is None:
                    break
                reason = self._continuation_stop_reason(key, seen_keys, len(results), max_pages)
                if reason is not None:
                    self._log_continuation_stop(reason, len(results))
                    callback and callback(response, RequestStatus.FAIL)
                    break
                seen_keys.add(key)
                callback and callback(response, RequestStatus.OCCURS_REQUEST)
                time.sleep(delay)
                header.tr_cont = "Y"
                header.tr_cont_key = key
                response = self.req()
                results.append(response)
        finally:
            header.tr_cont, header.tr_cont_key = initial

        callback and callback(None, RequestStatus.COMPLETE)
        callback and callback(None, RequestStatus.CLOSE)
        return results

    async def header_occurs_req_async(
        self,
        callback: Optional[Callable[[Optional[R], RequestStatus], None]] = None,
        delay: float = 1,
        max_pages: int = DEFAULT_OCCURS_MAX_PAGES,
    ) -> list[R]:
        """Async form of :meth:`header_occurs_req` sharing one HTTP session."""
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")
        header = self.request_data.header
        initial = (header.tr_cont, header.tr_cont_key)
        results: list[R] = []
        seen_keys: Set[str] = set()
        try:
            async with aiohttp.ClientSession() as session:
                callback and callback(None, RequestStatus.REQUEST)
                response = await self._req_async_with_session(session)
                results.append(response)
                while True:
                    if _page_failed(response):
                        callback and callback(response, RequestStatus.FAIL)
                        break
                    callback and callback(response, RequestStatus.RESPONSE)
                    key = _continuation_key(response)
                    if key is None:
                        break
                    reason = self._continuation_stop_reason(key, seen_keys, len(results), max_pages)
                    if reason is not None:
                        self._log_continuation_stop(reason, len(results))
                        callback and callback(response, RequestStatus.FAIL)
                        break
                    seen_keys.add(key)
                    callback and callback(response, RequestStatus.OCCURS_REQUEST)
                    await asyncio.sleep(delay)
                    header.tr_cont = "Y"
                    header.tr_cont_key = key
                    response = await self._req_async_with_session(session)
                    results.append(response)
        finally:
            header.tr_cont, header.tr_cont_key = initial

        callback and callback(None, RequestStatus.COMPLETE)
        callback and callback(None, RequestStatus.CLOSE)
        return results
