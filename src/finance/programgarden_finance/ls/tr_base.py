"""
This file defines abstract classes for handling TR requests and responses.
These classes perform TR requests, manage request state, and provide functionality
for retrying requests asynchronously and for processing continuous (repeated) requests.
"""

from abc import ABC, abstractmethod
import asyncio
import math
import threading
import time
from typing import Any, Callable, Dict, Literal, Optional, TypeVar

import aiohttp
import requests

from programgarden_finance.ls.models import SetupOptions
from programgarden_finance.ls.token_manager import TokenManager

from .status import RequestStatus
from programgarden_core.logs import pg_logger


TRresponse = TypeVar("TRresponse")


class TRRequestAbstract(ABC):
    """TR 코드 추상 클래스 (in_block 타입을 제너릭으로)"""

    # registry for shared rate-limit data keyed by TR code or custom key
    _shared_rate_data: Dict[str, dict] = {}

    def __init__(
        self,
        rate_limit_count: int,
        rate_limit_seconds: int,
        on_rate_limit: Literal["stop", "wait"] = "wait",
        rate_limit_key: Optional[str] = None,
    ):
        """
        TR 요청을 초기화합니다.

        Args:
            rate_limit_count (int): 요청 속도 제한 횟수
            rate_limit_seconds (int): 요청 속도 제한 시간 (초)
            on_rate_limit (Literal["stop", "wait"]): 속도 제한 초과 시 동작 방식, stop은 요청 안함, wait는 대기 후 재시도
            rate_limit_key (Optional[str]): 속도 제한 상태를 공유할 키 (기본: None, 인스턴스별로 별도 관리)
        """
        super().__init__()

        # allow sharing rate-limit state across instances by explicit key only
        if rate_limit_key:
            # create or reuse shared storage for this key
            shared = TRRequestAbstract._shared_rate_data.get(rate_limit_key)
            if shared is None:
                shared = {
                    "lock": threading.RLock(),
                    "cond": None,
                    "timestamps": []
                }
                # ensure the condition uses the same lock
                shared["cond"] = threading.Condition(shared["lock"])
                TRRequestAbstract._shared_rate_data[rate_limit_key] = shared

            self._lock = shared["lock"]
            self._sync_cond = shared["cond"]
            # share the same list object so mutations are visible across instances
            self.request_timestamps = shared["timestamps"]
        else:
            self._lock = threading.RLock()  # 변경: sync/async 혼합 안전
            self._sync_cond = threading.Condition(self._lock)
            self.request_timestamps: list[float] = []

        self.rate_limit_count = rate_limit_count
        self.rate_limit_seconds = rate_limit_seconds

        # 동작 모드: "stop" (기본) -> 초과 시 에러, "wait" -> 대기 후 재시도
        if on_rate_limit not in ("stop", "wait"):
            raise ValueError("on_rate_limit must be 'stop' or 'wait'")
        self.on_rate_limit = on_rate_limit

    def _build_json_body(self, request_data):
        """
        Build a JSON-serializable body from request_data.body.

        Handles values that may be:
        - None -> serialized as None (JSON null)
        - objects with `model_dump()` (pydantic v2) -> use model_dump()
        - lists/tuples -> recursively serialize each element
        - dicts -> recursively serialize values
        - primitives -> left as-is
        """

        def _serialize(value):
            # None -> null in JSON
            if value is None:
                return None

            # pydantic v2 models expose model_dump
            if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
                return value.model_dump()

            # lists/tuples -> recursively serialize
            if isinstance(value, (list, tuple)):
                return [
                    _serialize(v) for v in value
                ]

            # dicts -> recursively serialize values
            if isinstance(value, dict):
                return {k: _serialize(v) for k, v in value.items()}

            # fallback: assume JSON-serializable primitive
            return value

        body = {}
        for code, data in getattr(request_data, "body", {}).items():
            body[code] = _serialize(data)

        return body

    async def execute_async_with_session(self, session: aiohttp.ClientSession, url: str, request_data, timeout: int = 10):
        """
        비동기 TR 요청을 실행합니다.
        """
        try:
            if self.on_rate_limit == "stop":
                if self.is_rate_limited():
                    raise ValueError("Rate limit exceeded")
                await self.record_request_async()
            else:
                await self.wait_until_available_async()

            headers = request_data.header.model_dump(by_alias=True)
            jsons = self._build_json_body(request_data)

            async with session.post(
                url=url,
                headers=headers,
                json=jsons,
            ) as response:

                try:
                    response_json = await response.json()
                except aiohttp.ContentTypeError:
                    response_json = None

                headers = dict(response.headers)

                if response.status >= 400:
                    return response, response_json or {}, headers

                response.raise_for_status()
                return response, response_json, headers

        except aiohttp.ClientError as e:
            raise e

    def execute_sync(self, url: str, request_data, timeout: int = 10):
        """
        동기 TR 요청을 실행합니다.
        """
        try:
            if self.on_rate_limit == "stop":
                if self.is_rate_limited():
                    raise ValueError("Rate limit exceeded")
                self.record_request()
            else:
                self.wait_until_available()

            resp = requests.post(
                url=url,
                headers=request_data.header.model_dump(by_alias=True),
                json=self._build_json_body(request_data),
                timeout=timeout,
            )

            try:
                response_json = resp.json()
            except ValueError:
                response_json = None

            headers = dict(resp.headers)

            if resp.status_code >= 400:
                return resp, response_json or {}, headers

            resp.raise_for_status()
            return resp, response_json, headers

        except requests.RequestException as e:
            pg_logger.error(f"동기 요청 실패: {e}")
            raise

    def is_rate_limited(self) -> bool:
        """
        현재 요청이 속도 제한을 초과하는지 확인합니다.
        Returns:
            bool: 제한 초과 시 True
        """
        # 락으로 보호
        with self._lock:
            # 오래된 타임스탬프 정리
            self.cleanup_timestamps()
            return len(self.request_timestamps) >= self.rate_limit_count

    def cleanup_timestamps(self) -> None:
        """
        현재 rate_limit_seconds 보다 오래된 요청 타임스탬프를 제거합니다.
        주기적으로 호출하거나 is_rate_limited / record_request에서 호출합니다.
        """

        # remove timestamps older than rate_limit_seconds
        now = time.time()
        with self._lock:
            # mutate list in-place so shared lists reflect changes across instances
            new_list = [
                ts for ts in self.request_timestamps
                if math.ceil((now - ts) * 100) / 100 < self.rate_limit_seconds
            ]
            self.request_timestamps[:] = new_list

            # 오래된 항목이 제거되면 대기중인 스레드가 깨워서 다시 시도하도록 알림
            try:
                self._sync_cond.notify_all()
            except Exception:
                pass

    def record_request(self):
        """
        요청 시각을 기록합니다. 기록 전에 오래된 항목을 정리하여 리스트가 불필요하게 커지지 않도록 합니다.
        """
        # 락으로 보호
        with self._lock:
            # 오래된 타임스탬프 정리 후 기록
            self.cleanup_timestamps()
            self.request_timestamps.append(time.time())

            # 새 요청을 기록했으므로 대기중인 스레드에 알림(append로 인해 더 블록될 수도 있으나 notify는 안전)
            try:
                self._sync_cond.notify_all()
            except Exception:
                pass

    async def record_request_async(self) -> None:
        """
        비동기 환경에서 호출해도 이벤트 루프를 블로킹하지 않도록
        record_request를 스레드에서 실행하는 래퍼입니다.
        """

        await asyncio.to_thread(self.record_request)

    def wait_until_available(self) -> None:
        """
        sync 환경에서 rate limit 슬롯이 확보될 때까지 대기하고,
        확보되면 즉시 요청 시각을 기록합니다.
        동작 모드가 'wait'일 때 사용됩니다.
        """

        with self._sync_cond:
            while True:
                # cleanup & check
                self.cleanup_timestamps()
                if len(self.request_timestamps) < self.rate_limit_count:
                    # 슬롯 확보 -> 기록하고 리턴
                    self.request_timestamps.append(time.time())
                    # notify others that we've mutated timestamps
                    try:
                        self._sync_cond.notify_all()
                    except Exception:
                        pass
                    return

                # 슬롯 없음 -> 대기해야 함
                now = time.time()
                oldest = min(self.request_timestamps)
                wait_time = self.rate_limit_seconds - (now - oldest)
                if wait_time <= 0:
                    # 타임스탬프가 만료되었을 가능성 있으므로 바로 재시도
                    continue
                # 조건 변수로 기다리되, 최대 wait_time 만큼 기다림 -> 깰 때 재검사
                self._sync_cond.wait(wait_time)

    async def wait_until_available_async(self) -> None:
        """
        async 환경에서 rate limit 슬롯이 확보될 때까지 대기하고,
        확보되면 즉시 요청 시각을 기록합니다.
        동작 모드가 'wait'일 때 사용됩니다.
        (간단한 폴링 기반으로 구현하여 이벤트 루프를 블로킹하지 않음)
        """
        while True:
            # cleanup in thread to avoid blocking loop
            await asyncio.to_thread(self.cleanup_timestamps)
            with self._lock:

                # 2개 제한이면, timestamps가 그보다 적으면 요청 가능
                if len(self.request_timestamps) < self.rate_limit_count:

                    # 슬롯 확보 -> 기록하고 리턴
                    self.request_timestamps.append(time.time())

                    try:
                        self._sync_cond.notify_all()
                    except Exception:
                        pass
                    return

                # 갯수가 넘어가버리면, 기다리는 시간 계산
                now = time.time()
                oldest = min(self.request_timestamps)
                wait_time = self.rate_limit_seconds - (now - oldest)

                # 기다린 시간 넘겼으면 다시 진행
                if wait_time <= 0:
                    # loop to recheck immediately
                    continue

            # 다음 요청까지 남은 시간까지 대기
            await asyncio.sleep(wait_time)

    @abstractmethod
    async def req_async(self, **kwargs) -> TRresponse:
        """
        비동기 방식으로 TR 요청을 수행하는 메서드
        """
        pass

    @abstractmethod
    def req(self, **kwargs) -> TRresponse:
        """
        TR 요청을 수행하는 메서드
        """
        pass


class RetryReqAbstract(ABC):
    """ 요청을 반복적으로 시도하는 추상 클래스 """

    @abstractmethod
    def retry_req(
        self,
        callback: Callable[[Optional[TRresponse], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 5
    ) -> TRresponse:
        """
        요청을 최대 지정된 횟수만큼 반복하여 시도하는 메서드입니다.

        Args:
            callback (callable): 응답을 처리할 콜백 함수
            max_retries (int): 최대 반복 횟수
            delay (int): 반복 간격 (초 단위)

        Returns:
            TRresponse: 최종 응답 객체
        """
        pass

    @abstractmethod
    async def retry_req_async(
        self,
        callback: Callable[[Optional[TRresponse], RequestStatus], None],
        max_retries: int = 3,
        delay: int = 5
    ) -> TRresponse:
        """
        동시성 요청을 최대 지정된 횟수만큼 반복하여 시도하는 메서드입니다.

        Args:
            callback (callable): 응답을 처리할 콜백 함수
            max_retries (int): 최대 반복 횟수
            delay (int): 반복 간격 (초 단위)

        Returns:
            TRresponse: 최종 응답 객체
        """
        pass


class OccursReqAbstract(ABC):
    """ 연속 요청을 처리하는 추상 클래스 """

    @abstractmethod
    def occurs_req(
        self,
        callback: Optional[Callable[[Optional[TRresponse], RequestStatus], None]] = None,
        delay: int = 1
    ):
        """
        연속 요청을 처리하는 동기성 메서드입니다.
        Args:
            callback (Callable[[Optional[TRresponse], RequestStatus], None]): 응답을 처리할 콜백 함수
            delay (int): 요청 간의 지연 시간 (초 단위)
        """
        pass

    @abstractmethod
    async def occurs_req_async(self, callback: Optional[Callable[[Optional[TRresponse], RequestStatus], None]] = None, delay: int = 1):
        """
        연속 요청을 처리하는 동시성 메서드입니다.
        Args:
            callback (Callable[[Optional[TRresponse], RequestStatus], None]): 응답을 처리할 콜백 함수
            delay (int): 요청 간의 지연 시간 (초 단위)
        """
        pass


class TRAccnoAbstract(TRRequestAbstract, RetryReqAbstract):
    """ 계좌 요청 추상 클래스 """


class TROrderAbstract(TRRequestAbstract):
    """ 주문 요청 추상 클래스 """


def set_tr_header_options(
    token_manager: TokenManager,
    header: Optional[Any],
    options: Optional[SetupOptions],
    request_data: Any,
) -> None:
    """
    Sets the header and options for the request data.
    """

    if header:
        request_data.header = header

    # ensure authorization is present on the request header
    req_header = getattr(request_data, "header", None)
    if not getattr(req_header, "authorization", None):
        request_data.header.authorization = token_manager.get_bearer_token()

    if options:
        request_data.options = options

    req_options = getattr(request_data, "options", None)
    if req_options is None:
        request_data.options = SetupOptions()
        req_options = request_data.options

    req_options.token_manager = token_manager
