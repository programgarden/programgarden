# from typing import Optional
from programgarden_core.exceptions import TokenNotFoundException


# class TokenManager:
#     """
#     애플리케이션 전체에서 사용할 토큰을 관리하는 클래스
#     인스턴스화 할 때마다 상태가 초기화됩니다.
#     """

#     def __init__(self) -> None:
#         self._access_token = None
#         self._appkey = None
#         self._appsecretkey = None

#     @property
#     def access_token(self) -> Optional[str]:
#         """현재 저장된 access_token을 반환합니다."""
#         return self._access_token

#     @access_token.setter
#     def access_token(self, token: str) -> None:
#         """access_token을 설정합니다."""
#         self._access_token = token

#     @property
#     def appkey(self) -> Optional[str]:
#         """현재 저장된 appkey를 반환합니다."""
#         return self._appkey

#     @appkey.setter
#     def appkey(self, key: str) -> None:
#         """appkey를 설정합니다."""
#         self._appkey = key

#     @property
#     def appsecretkey(self) -> Optional[str]:
#         """현재 저장된 appsecretkey를 반환합니다."""
#         return self._appsecretkey

#     @appsecretkey.setter
#     def appsecretkey(self, key: str) -> None:
#         """appsecretkey를 설정합니다."""
#         self._appsecretkey = key

#     def get_bearer_token(self) -> str:
#         """Bearer 형식의 토큰을 반환합니다."""
#         if not self._access_token:
#             raise TokenNotFoundException()
#         return f"Bearer {self._access_token}"

#     def is_token_available(self) -> bool:
#         """토큰이 존재하는지 확인합니다."""
#         return self._access_token is not None

#     def clear_tokens(self) -> None:
#         """모든 토큰 정보를 초기화합니다."""
#         self._access_token = None
#         self._appkey = None
#         self._appsecretkey = None


from dataclasses import dataclass
import time
from typing import Optional, ClassVar

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

    def get_bearer_token(self) -> str:
        """Bearer 형식의 토큰을 반환합니다."""
        if not self.access_token:
            raise TokenNotFoundException()
        return f"Bearer {self.access_token}"
