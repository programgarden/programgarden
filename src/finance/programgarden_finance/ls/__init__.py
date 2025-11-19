import asyncio
import threading
import time
from typing import Optional
from programgarden_core.korea_alias import EnforceKoreanAliasMeta, require_korean_alias

from . import overseas_stock, overseas_futureoption, oauth

from .overseas_stock import OverseasStock
from .overseas_futureoption import OverseasFutureoption
from .oauth.generate_token import GenerateToken
from .oauth.generate_token.token.blocks import TokenInBlock
from .token_manager import TokenManager
from programgarden_core.exceptions import AppKeyException, LoginException
from .config import URLS


class LS(metaclass=EnforceKoreanAliasMeta):

    # Singleton support: use LS.get_instance() to obtain a process-global instance.
    # Regular instantiation via LS() remains unchanged.
    _singleton_instance: Optional["LS"] = None
    _singleton_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "LS":
        """
        Return a thread-safe singleton instance of LS. Multiple calls return the
        same object. This does not prevent creating additional instances via LS().
        """
        with cls._singleton_lock:
            if cls._singleton_instance is None:
                cls._singleton_instance = cls()
            return cls._singleton_instance

    def __init__(self):
        self.token_manager: Optional[TokenManager] = TokenManager()

        # 동시성 보호용 락: sync/async 각각
        # _async_lock은 이벤트 루프가 없는 컨텍스트에서 생성할 때 문제를 피하기 위해 지연 초기화합니다.
        self._sync_lock = threading.RLock()
        self._async_lock: Optional[asyncio.Lock] = None

    def is_logged_in(self) -> bool:
        """
        현재 로그인 상태인지 확인합니다.

        Returns:
            bool: 로그인 상태 여부. True면 로그인됨, False면 로그인되지 않음.
        """
        return self.token_manager.is_token_available()

    # helper: token block로부터 token_manager를 안전하게 갱신 (스레드 락 사용)
    def _update_token_from_block(self, block) -> None:
        if not block:
            return
        with self._sync_lock:
            self.token = block
            self.token_manager.update_from_block(block)

    @require_korean_alias
    def login(
        self,
        appkey: str = None,
        appsecretkey: str = None,
        paper_trading: bool = False,
    ) -> bool:
        """
        LS증권사 로그인 (동기)

        Args:
            appkey (str): LS 증권의 앱 키.
            appsecretkey (str): LS 증권의 앱 시크릿 키.
            paper_trading (bool): 모의 투자 환경(WSS 포함)을 사용할지 여부. 기본값은 False입니다.

        Returns:
            bool: 로그인 성공 여부. 성공하면 True, 실패하면 False.

        Raises:
            AppKeyException: 앱 키 또는 시크릿 키가 제공되지 않은 경우.
            LoginException: 로그인 과정에서 오류가 발생한 경우.
        """

        if not appkey or not appsecretkey:
            raise AppKeyException()

        try:
            # sync 락으로 상태 변경 보호
            with self._sync_lock:
                self.token_manager.appkey = appkey
                self.token_manager.appsecretkey = appsecretkey
                self.token_manager.configure_trading_mode(paper_trading)

            response = GenerateToken().token(
                TokenInBlock(
                    appkey=appkey,
                    appsecretkey=appsecretkey,
                )
            ).req()

            self.token = response.block
            # 안전하게 업데이트
            if response.block and response.block.access_token:
                # 토큰/만료 정보 저장
                self._update_token_from_block(response.block)
                return True

            return False

        except Exception as e:
            raise LoginException(message=str(e))

    @require_korean_alias
    async def async_login(self, appkey: str, appsecretkey: str, paper_trading: bool = False) -> bool:
        """
        LS증권사 로그인 (비동기)

        Args:
            appkey (str): LS 증권의 앱 키.
            appsecretkey (str): LS 증권의 앱 시크릿 키.
            paper_trading (bool): 모의 투자 환경(WSS 포함)을 사용할지 여부. 기본값은 False입니다.

        Returns:
            bool: 로그인 성공 여부. 성공하면 True, 실패하면 False.

        Raises:
            AppKeyException: 앱 키 또는 시크릿 키가 제공되지 않은 경우.
            LoginException: 로그인 과정에서 오류가 발생한 경우.
        """

        if not appkey or not appsecretkey:
            raise AppKeyException()

        try:
            # async 락으로 상태 변경 보호
            # lazy-init async lock under thread-safe guard to avoid races
            if self._async_lock is None:
                with self._sync_lock:
                    if self._async_lock is None:
                        self._async_lock = asyncio.Lock()
            async with self._async_lock:
                self.token_manager.appkey = appkey
                self.token_manager.appsecretkey = appsecretkey
                self.token_manager.configure_trading_mode(paper_trading)

            response = await GenerateToken().token(
                TokenInBlock(
                    appkey=appkey,
                    appsecretkey=appsecretkey,
                )
            ).req_async()

            if response.block and response.block.access_token:
                # 코루틴에서 threading.RLock과 동일한 보호를 얻기 위해 executor로 위임
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._update_token_from_block, response.block)
                return True

            return False

        except Exception as e:
            raise LoginException(message=str(e))

    로그인 = login
    로그인.__doc__ = "로그인을 수행합니다. appkey와 appsecretkey를 입력해야 합니다."

    비동기로그인 = async_login
    비동기로그인.__doc__ = "비동기로 로그인을 수행합니다. appkey와 appsecretkey를 입력해야 합니다."

    @require_korean_alias
    def overseas_stock(self) -> OverseasStock:
        """해외 주식 데이터를 조회합니다."""

        # 토큰 확인
        if not self.ensure_token():
            raise LoginException("토큰이 유효하지 않습니다.")

        return OverseasStock(
            token_manager=self.token_manager,
        )

    해외주식 = overseas_stock
    해외주식.__doc__ = "해외 주식 데이터를 조회합니다."

    @require_korean_alias
    def overseas_futureoption(self) -> OverseasFutureoption:
        """해외 선물 데이터를 조회합니다."""

        # 토큰 확인
        if not self.ensure_token():
            raise LoginException("토큰이 유효하지 않습니다.")

        return OverseasFutureoption(
            token_manager=self.token_manager,
        )

    해외선물 = overseas_futureoption
    해외선물.__doc__ = "해외 선물 데이터를 조회합니다."

    def ensure_token(self, force_refresh: bool = False) -> bool:
        """토큰이 만료(또는 임박)되었으면 재발급합니다."""
        if not self.token_manager:
            return False
        return self.token_manager.ensure_fresh_token(force_refresh)

    async def async_ensure_token(self, force_refresh: bool = False) -> bool:
        """토큰이 만료(또는 임박)되었으면 비동기로 재발급합니다."""
        if not self.token_manager:
            return False
        return await self.token_manager.ensure_fresh_token_async(force_refresh)


__all__ = [
    LS,
    OverseasStock,
    OverseasFutureoption,
    GenerateToken,
    URLS,
    TokenManager,

    overseas_stock,
    overseas_futureoption,
    oauth,
]
