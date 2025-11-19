from programgarden_core.exceptions import TokenNotFoundException
from dataclasses import dataclass
import time
from typing import Awaitable, Callable, Optional, ClassVar

from .config import URLS
from programgarden_core.logs import pg_logger

# 토큰 재발급 임계 시간(초): 만료 5분 전부터 재발급 시도
TOKEN_REFRESH_SKEW_SECONDS = 300


@dataclass
class TokenManager:
    appkey: Optional[str] = None
    appsecretkey: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_in: Optional[int] = None  # 초 단위
    acquired_at: ClassVar[float] = None  # epoch seconds
    paper_trading: bool = False
    wss_url: Optional[str] = None

    @property
    def expires_at(self) -> Optional[float]:
        if self.acquired_at is None or self.expires_in is None:
            return None
        return self.acquired_at + self.expires_in

    def is_expired(self, skew_seconds: int = TOKEN_REFRESH_SKEW_SECONDS) -> bool:
        if self.expires_at is None:
            return True
        return time.time() >= (self.expires_at - skew_seconds)

    def is_token_available(self) -> bool:
        return self.access_token is not None and not self.is_expired()

    def ensure_fresh_token(self, force_refresh: bool = False) -> bool:
        """토큰이 만료되었거나 강제 갱신이 필요한 경우 동기적으로 갱신합니다."""
        if not force_refresh and not self.is_expired():
            return True
        return self._refresh_token()

    async def ensure_fresh_token_async(self, force_refresh: bool = False) -> bool:
        """토큰이 만료되었거나 강제 갱신이 필요한 경우 비동기적으로 갱신합니다."""
        if not force_refresh and not self.is_expired():
            return True
        return await self._async_refresh_token()

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

    def update_from_block(self, block) -> None:
        """토큰 응답 블록으로부터 상태를 갱신합니다."""
        if not block:
            return
        self.access_token = block.access_token
        self.token_type = getattr(block, "token_type", None)
        self.scope = getattr(block, "scope", None)
        self.expires_in = getattr(block, "expires_in", None)
        self.acquired_at = time.time()

    def _refresh_token(self) -> bool:
        """내부적으로 토큰을 동기 갱신합니다."""
        if not self.appkey or not self.appsecretkey:
            return False

        try:
            # Avoid circular import
            from .oauth.generate_token import GenerateToken
            from .oauth.generate_token.token.blocks import TokenInBlock

            response = GenerateToken().token(
                TokenInBlock(
                    appkey=self.appkey,
                    appsecretkey=self.appsecretkey,
                )
            ).req()

            if response.block and response.block.access_token:
                self.update_from_block(response.block)
                return True
            return False
        except Exception:
            return False

    async def _async_refresh_token(self) -> bool:
        """내부적으로 토큰을 비동기 갱신합니다."""
        if not self.appkey or not self.appsecretkey:
            return False

        try:
            # Avoid circular import
            from .oauth.generate_token import GenerateToken
            from .oauth.generate_token.token.blocks import TokenInBlock

            response = await GenerateToken().token(
                TokenInBlock(
                    appkey=self.appkey,
                    appsecretkey=self.appsecretkey,
                )
            ).req_async()

            if response.block and response.block.access_token:
                self.update_from_block(response.block)
                return True
            return False
        except Exception:
            return False
