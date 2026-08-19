from programgarden_core.exceptions import TokenNotFoundException
from dataclasses import dataclass, field
import asyncio
import inspect
import threading
import time
from typing import Awaitable, Callable, Optional, Tuple

from .config import URLS
from .token_errors import TokenReissueLimitExceeded
import logging

logger = logging.getLogger("programgarden.ls.token_manager")

# 토큰 재발급 임계 시간(초): 만료 5분 전부터 재발급 시도
TOKEN_REFRESH_SKEW_SECONDS = 300

# --- 강제 재발급(사용 중 토큰 실패로 촉발) 안전장치 -------------------------------
# 만료 전이라도 죽은 토큰을 만나면 재발급하므로, 폭주 방지 장치가 필수다.
# 상한 초과는 조용히 실패시키지 않고 TokenReissueLimitExceeded 로 사유를 알린다.
FORCED_REISSUE_MAX = 3                 # 롤링 창 안에서 허용하는 강제 재발급 횟수
FORCED_REISSUE_WINDOW_SECONDS = 600    # 상한을 세는 롤링 창(초)
FORCED_REISSUE_MIN_INTERVAL_SECONDS = 2.0  # 연속 강제 재발급 사이 최소 간격(초)


def provider_accepts_kwarg(fn: Callable, name: str) -> bool:
    """``fn`` 이 ``name`` 키워드 인자를 받는지 검사한다.

    토큰 provider 는 외부(트레이앱·서버)가 주입하는 콜백이라 시그니처가 판마다 다르다.
    구판 provider 에 없는 인자를 넘기면 ``TypeError`` 로 죽으므로, 넘기기 전에 확인한다.
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):  # 내장/C 콜러블 등
        return False
    for param in sig.parameters.values():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if param.name == name and param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            return True
    return False


@dataclass
class TokenManager:
    appkey: Optional[str] = None
    appsecretkey: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_in: Optional[int] = None  # 초 단위
    acquired_at: Optional[float] = None  # epoch seconds
    paper_trading: bool = False
    wss_url: Optional[str] = None
    # Opt-in token provider callbacks (Verified League §3.2.3). When set, the
    # token is fetched from this callback (a server endpoint) instead of being
    # self-issued via GenerateToken — making a remote server the single token
    # issuer and this client a pure consumer (no appsecret required). Each
    # callback returns (access_token, expires_at_epoch_seconds). Left as None for
    # standalone/public usage, which keeps the original self-issue behaviour.
    #
    # 강제 재발급을 지원하는 provider 는 ``force_reissue: bool`` 과 (선택)
    # ``stale_token: str | None`` 키워드를 받는다. 서버가 단일 발급자이므로, 이 인자를
    # 못 받는 provider 는 죽은 토큰을 그대로 다시 돌려줄 수밖에 없다 — 그 경우 경고를
    # 남긴다(조용히 성공한 척하지 않는다).
    token_provider: Optional[Callable[..., Tuple[str, float]]] = field(
        default=None, compare=False, repr=False
    )
    async_token_provider: Optional[Callable[..., Awaitable[Tuple[str, float]]]] = field(
        default=None, compare=False, repr=False
    )

    def __post_init__(self):
        # 동시 갱신 방지 Lock
        self._refresh_lock = threading.Lock()
        self._async_refresh_lock: Optional[asyncio.Lock] = None
        # 토큰이 새로 적용될 때마다 증가한다. 실패를 관측한 호출자가 관측 시점의 값을
        # 함께 넘기면, 그 사이 다른 호출자가 이미 재발급했는지 정확히 알 수 있다
        # (single-flight 합류 — 시간 heuristic 이 필요 없다).
        self._token_generation: int = 0
        # 강제 재발급 시각들(롤링 창 상한 계산용)
        self._forced_reissue_times: list[float] = []
        # 토큰이 새로 적용될 때 호출되는 선택적 훅. 자체 발급(self-issue) 경로를 쓰는
        # 소비자(pg-ai 등)가 새 토큰을 공유 저장소에 되쓰기(write-through)해,
        # 저장소가 죽은 토큰을 계속 내주는 일을 막는 데 쓴다.
        self._on_token_refreshed: Optional[Callable[[str, float], None]] = None

    # ------------------------------------------------------------------
    # 상태 조회
    # ------------------------------------------------------------------
    @property
    def expires_at(self) -> Optional[float]:
        if self.acquired_at is None or self.expires_in is None:
            return None
        return self.acquired_at + self.expires_in

    @property
    def token_generation(self) -> int:
        """현재 토큰의 세대 번호. 토큰이 새로 적용될 때마다 1씩 증가한다."""
        return self._token_generation

    def is_expired(self, skew_seconds: int = TOKEN_REFRESH_SKEW_SECONDS) -> bool:
        if self.expires_at is None:
            return True
        return time.time() >= (self.expires_at - skew_seconds)

    def is_token_available(self) -> bool:
        return self.access_token is not None and not self.is_expired()

    def set_on_token_refreshed(
        self, callback: Optional[Callable[[str, float], None]]
    ) -> None:
        """새 토큰이 적용될 때마다 ``callback(access_token, expires_at_epoch)`` 을 호출한다.

        자체 발급 경로가 만든 토큰을 공유 저장소에 반영하기 위한 훅이다. 콜백에서 난
        예외는 삼키되 로그로 남긴다 — 되쓰기 실패가 거래 경로를 죽이면 안 된다.
        """
        self._on_token_refreshed = callback

    def ensure_fresh_token(self, force_refresh: bool = False) -> bool:
        """토큰이 만료되었거나 강제 갱신이 필요한 경우 동기적으로 갱신합니다."""
        if not force_refresh and not self.is_expired():
            return True
        return self._refresh_token(force=force_refresh)

    async def ensure_fresh_token_async(self, force_refresh: bool = False) -> bool:
        """토큰이 만료되었거나 강제 갱신이 필요한 경우 비동기적으로 갱신합니다."""
        if not force_refresh and not self.is_expired():
            return True
        return await self._async_refresh_token(force=force_refresh)

    def get_bearer_token(self) -> str:
        """Bearer 형식의 토큰을 반환합니다. 만료 시 자동 갱신을 시도합니다."""
        # 토큰 만료 체크 및 자동 갱신
        if self.is_expired():
            # 동기 컨텍스트라고 가정하고 갱신 시도 (get_bearer_token은 보통 동기 호출됨)
            # 비동기 환경에서 호출될 경우 블로킹이 발생할 수 있으나,
            # 토큰 갱신은 드물게 발생하므로 허용
            self._refresh_token()

        if not self.access_token:
            raise TokenNotFoundException()
        return f"Bearer {self.access_token}"

    def configure_trading_mode(self, paper_trading: bool) -> None:
        mode = bool(paper_trading)
        self.paper_trading = mode
        self.wss_url = URLS.get_wss_url(mode)

    def has_provider(self) -> bool:
        """True if a token provider callback is configured (consumer mode)."""
        return self.token_provider is not None or self.async_token_provider is not None

    # ------------------------------------------------------------------
    # 토큰 적용
    # ------------------------------------------------------------------
    def apply_token(self, access_token: str, expires_at: float) -> None:
        """Inject a server-issued token directly (provider/consumer mode).

        expires_at is an absolute epoch-seconds expiry. We store acquired_at=now
        and derive expires_in so is_expired()/expires_at keep working unchanged.
        """
        self.access_token = access_token
        self.token_type = self.token_type or "Bearer"
        now = time.time()
        self.acquired_at = now
        self.expires_in = max(0, int(expires_at - now))
        self._token_generation += 1
        self._notify_refreshed(access_token, expires_at)

    def update_from_block(self, block) -> None:
        """토큰 응답 블록으로부터 상태를 갱신합니다."""
        if not block:
            return
        self.access_token = block.access_token
        self.token_type = getattr(block, "token_type", None)
        self.scope = getattr(block, "scope", None)
        self.expires_in = getattr(block, "expires_in", None)
        self.acquired_at = time.time()
        self._token_generation += 1
        if self.expires_in is not None:
            self._notify_refreshed(self.access_token, self.acquired_at + self.expires_in)

    def _notify_refreshed(self, access_token: str, expires_at: float) -> None:
        callback = self._on_token_refreshed
        if callback is None or not access_token:
            return
        try:
            callback(access_token, expires_at)
        except Exception as exc:  # 되쓰기 실패가 거래 경로를 죽이면 안 된다
            logger.warning(f"on_token_refreshed callback failed: {exc}")

    # ------------------------------------------------------------------
    # 강제 재발급 (사용 중 토큰 실패로 촉발)
    # ------------------------------------------------------------------
    def force_reissue(self, observed_generation: Optional[int] = None) -> bool:
        """죽은 토큰을 만난 호출자가 부르는 동기 강제 재발급.

        Args:
            observed_generation: 실패한 요청이 쓴 토큰의 세대(:pyattr:`token_generation`).
                Lock 을 잡은 뒤 세대가 이미 바뀌어 있으면 **다른 호출자가 방금
                재발급한 것**이므로, 다시 발급하지 않고 그 결과에 합류한다.

        Returns:
            bool: 사용 가능한 새 토큰이 준비되었는지 여부.

        Raises:
            TokenReissueLimitExceeded: 롤링 창 안의 강제 재발급 상한을 넘었을 때.
        """
        return self._refresh_token(force=True, observed_generation=observed_generation)

    async def force_reissue_async(self, observed_generation: Optional[int] = None) -> bool:
        """:meth:`force_reissue` 의 비동기 판."""
        return await self._async_refresh_token(
            force=True, observed_generation=observed_generation
        )

    def _joined_other_reissue(self, observed_generation: Optional[int]) -> bool:
        """Lock 안에서 호출 — 다른 호출자가 이미 재발급했으면 True."""
        if observed_generation is None:
            return False
        return self._token_generation != observed_generation and self.is_token_available()

    _REISSUE_LIMIT_MESSAGE = (
        f"LS 토큰을 {FORCED_REISSUE_WINDOW_SECONDS}초 안에 {FORCED_REISSUE_MAX}회 새로 "
        "발급했는데도 계속 거부됩니다. 재발급으로 풀리는 문제가 아니므로 멈춥니다 — "
        "앱키 권한(해당 시세/주문 TR 사용 가능 여부)과 같은 앱키를 쓰는 다른 프로그램을 "
        "확인하세요."
    )

    def _reissue_budget_left(self) -> int:
        """롤링 창 안에 남은 강제 재발급 횟수.

        세는 것은 **성공한 재발급**이다. 시도를 세면 네트워크 장애 한 번이 예산을 다 태워,
        몇 분 뒤 찾아온 진짜 토큰 사고를 막지 못하고 엉뚱한 사유("앱키 권한을 확인하세요")로
        실패하게 된다.
        """
        now = time.time()
        self._forced_reissue_times = [
            t for t in self._forced_reissue_times if now - t < FORCED_REISSUE_WINDOW_SECONDS
        ]
        return FORCED_REISSUE_MAX - len(self._forced_reissue_times)

    def _reissue_gap_remaining(self) -> float:
        """연속 강제 재발급 사이 최소 간격 중 남은 시간(초)."""
        if not self._forced_reissue_times:
            return 0.0
        gap = time.time() - self._forced_reissue_times[-1]
        return max(0.0, FORCED_REISSUE_MIN_INTERVAL_SECONDS - gap)

    def _check_forced_reissue_budget(self) -> None:
        """강제 재발급 상한을 검사하고 최소 간격만큼 기다린다. 초과 시 예외."""
        if self._reissue_budget_left() <= 0:
            raise TokenReissueLimitExceeded(self._REISSUE_LIMIT_MESSAGE)
        wait = self._reissue_gap_remaining()
        if wait > 0:
            time.sleep(wait)

    async def _check_forced_reissue_budget_async(self) -> None:
        if self._reissue_budget_left() <= 0:
            raise TokenReissueLimitExceeded(self._REISSUE_LIMIT_MESSAGE)
        wait = self._reissue_gap_remaining()
        if wait > 0:
            await asyncio.sleep(wait)

    def _sync_lock_async(self):
        """비동기 경로에서 동기 ``_refresh_lock`` 을 잡는 async 컨텍스트 매니저.

        동기 경로(``get_bearer_token`` → ``_refresh_token``)와 비동기 경로가 같은
        ``access_token`` / ``_token_generation`` / 재발급 예산을 만진다. 각자 다른 락을
        쓰면 서로를 막지 못해 **동시에 두 번 발급**할 수 있다 — 이 모듈이 없애려는 문제를
        스스로 만드는 셈이다.

        ``acquire`` 는 블로킹이므로 스레드로 넘겨 이벤트 루프를 세우지 않는다. 타임아웃 시에는
        예외를 올린다 — 조용히 통과시키면 배타성이 깨진 채로 발급이 나간다.
        """
        lock = self._refresh_lock

        class _Guard:
            async def __aenter__(self_):
                acquired = await asyncio.to_thread(lock.acquire, True, 10)
                if not acquired:
                    raise TimeoutError(
                        "token refresh lock timeout (another refresh is in progress)"
                    )
                return self_

            async def __aexit__(self_, *exc):
                lock.release()
                return False

        return _Guard()

    def _record_forced_reissue(self) -> None:
        """**성공한** 강제 재발급 1건을 예산에 기록한다."""
        self._forced_reissue_times.append(time.time())

    # ------------------------------------------------------------------
    # provider 호출
    # ------------------------------------------------------------------
    def _provider_kwargs(self, fn: Callable, force: bool) -> dict:
        """provider 시그니처가 받는 만큼만 강제 재발급 인자를 채운다."""
        if not force:
            return {}
        kwargs = {}
        if provider_accepts_kwarg(fn, "force_reissue"):
            kwargs["force_reissue"] = True
        if provider_accepts_kwarg(fn, "stale_token"):
            kwargs["stale_token"] = self.access_token
        if "force_reissue" not in kwargs:
            logger.warning(
                "token_provider 가 force_reissue 를 받지 않습니다 — 서버가 캐시된(죽었을 수 있는) "
                "토큰을 그대로 돌려줄 수 있습니다. provider 를 최신 시그니처로 올리세요."
            )
        return kwargs

    # ------------------------------------------------------------------
    # 내부 갱신
    # ------------------------------------------------------------------
    def _refresh_token(
        self, force: bool = False, observed_generation: Optional[int] = None
    ) -> bool:
        """내부적으로 토큰을 동기 갱신합니다 (중복 갱신 방지 Lock 적용).

        ``force=True`` 면 만료 전이라도 재발급한다 — 사용 중 실패로 죽은 것이 확인된
        토큰을 만료시각만 보고 계속 내주던 것이 경합의 근본 원인이었다.
        """
        # Provider/consumer mode: a remote server is the single token issuer, so
        # never self-issue here. appsecret is not required in this mode.
        if self.token_provider is not None:
            if not self._refresh_lock.acquire(timeout=10):
                logger.warning("Token refresh lock timeout - another refresh in progress")
                return self.is_token_available()
            try:
                if self._joined_other_reissue(observed_generation):
                    logger.info("Joined another caller's token reissue (sync, provider)")
                    return True
                if not force and not self.is_expired():
                    return True
                if force:
                    self._check_forced_reissue_budget()
                kwargs = self._provider_kwargs(self.token_provider, force)
                access_token, expires_at = self.token_provider(**kwargs)
                if access_token:
                    self.apply_token(access_token, expires_at)
                    if force:
                        self._record_forced_reissue()
                    logger.info(
                        "Token refreshed via token_provider (sync, force=%s)", force
                    )
                    return True
                logger.error("token_provider returned an empty access_token (sync)")
                return False
            except TokenReissueLimitExceeded:
                raise
            except Exception as e:
                logger.error(f"token_provider refresh failed (sync): {e}")
                return False
            finally:
                self._refresh_lock.release()

        if not self.appkey or not self.appsecretkey:
            return False

        if not self._refresh_lock.acquire(timeout=10):
            logger.warning("Token refresh lock timeout - another refresh in progress")
            return self.is_token_available()

        try:
            # Lock 획득 후 다시 체크 (다른 스레드가 이미 갱신했을 수 있음)
            if self._joined_other_reissue(observed_generation):
                logger.info("Joined another caller's token reissue (sync, self-issue)")
                return True
            if not force and not self.is_expired():
                return True
            if force:
                self._check_forced_reissue_budget()

            from .oauth.generate_token import GenerateToken
            from .oauth.generate_token.token.blocks import TokenInBlock

            # 최대 2회 시도
            last_error = None
            for attempt in range(2):
                try:
                    response = GenerateToken().token(
                        TokenInBlock(
                            appkey=self.appkey,
                            appsecretkey=self.appsecretkey,
                        )
                    ).req()

                    if response.block and response.block.access_token:
                        self.update_from_block(response.block)
                        if force:
                            self._record_forced_reissue()
                        logger.info("Token refreshed successfully (sync, force=%s)", force)
                        return True
                except Exception as e:
                    last_error = e
                    if attempt < 1:
                        time.sleep(1)

            logger.error(f"Token refresh failed after 2 attempts: {last_error}")
            return False
        finally:
            self._refresh_lock.release()

    async def _async_refresh_token(
        self, force: bool = False, observed_generation: Optional[int] = None
    ) -> bool:
        """내부적으로 토큰을 비동기 갱신합니다 (중복 갱신 방지 Lock 적용)."""
        # Provider/consumer mode: prefer the async callback; fall back to the
        # sync one. A remote server issues the token, so never self-issue.
        if self.has_provider():
            if self._async_refresh_lock is None:
                self._async_refresh_lock = asyncio.Lock()
            # asyncio.Lock 하나로는 부족하다 — 같은 TokenManager 를 **동기 경로**가 동시에
            # 만질 수 있고, 두 락은 서로를 막지 못해 토큰이 두 번 발급된다("1 앱키 = 1 토큰"
            # 위반을 스스로 만든다). 그래서 async 락 안에서 sync 락도 함께 잡는다.
            # 잠금 순서는 항상 async → sync 한 방향이고 동기 경로는 sync 락만 잡으므로
            # 데드락이 생기지 않는다. acquire 는 스레드로 넘겨 이벤트 루프를 막지 않는다.
            async with self._async_refresh_lock, self._sync_lock_async():
                if self._joined_other_reissue(observed_generation):
                    logger.info("Joined another caller's token reissue (async, provider)")
                    return True
                if not force and not self.is_expired():
                    return True
                try:
                    if force:
                        await self._check_forced_reissue_budget_async()
                    if self.async_token_provider is not None:
                        fn = self.async_token_provider
                        access_token, expires_at = await fn(
                            **self._provider_kwargs(fn, force)
                        )
                    else:
                        fn = self.token_provider
                        access_token, expires_at = fn(**self._provider_kwargs(fn, force))
                    if access_token:
                        self.apply_token(access_token, expires_at)
                        if force:
                            self._record_forced_reissue()
                        logger.info(
                            "Token refreshed via token_provider (async, force=%s)", force
                        )
                        return True
                    logger.error("token_provider returned an empty access_token (async)")
                    return False
                except TokenReissueLimitExceeded:
                    raise
                except Exception as e:
                    logger.error(f"token_provider refresh failed (async): {e}")
                    return False

        if not self.appkey or not self.appsecretkey:
            return False

        # 비동기 Lock 초기화 (이벤트 루프에서만 생성 가능)
        if self._async_refresh_lock is None:
            self._async_refresh_lock = asyncio.Lock()

        # provider 경로와 같은 이유로 동기 락도 함께 잡는다(아래 _sync_lock_async 주석 참조).
        async with self._async_refresh_lock, self._sync_lock_async():
            # Lock 획득 후 다시 체크
            if self._joined_other_reissue(observed_generation):
                logger.info("Joined another caller's token reissue (async, self-issue)")
                return True
            if not force and not self.is_expired():
                return True
            if force:
                await self._check_forced_reissue_budget_async()

            from .oauth.generate_token import GenerateToken
            from .oauth.generate_token.token.blocks import TokenInBlock

            # 최대 2회 시도
            last_error = None
            for attempt in range(2):
                try:
                    response = await GenerateToken().token(
                        TokenInBlock(
                            appkey=self.appkey,
                            appsecretkey=self.appsecretkey,
                        )
                    ).req_async()

                    if response.block and response.block.access_token:
                        self.update_from_block(response.block)
                        if force:
                            self._record_forced_reissue()
                        logger.info("Token refreshed successfully (async, force=%s)", force)
                        return True
                except Exception as e:
                    last_error = e
                    if attempt < 1:
                        await asyncio.sleep(1)

            logger.error(f"Async token refresh failed after 2 attempts: {last_error}")
            return False


# 하위 호환 별칭 (내부 호출부가 쓰던 이름)
_accepts_kwarg = provider_accepts_kwarg
