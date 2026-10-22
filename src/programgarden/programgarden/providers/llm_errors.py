"""LLM Provider 에러 계층.

litellm 예외를 래핑하여 일관된 에러 인터페이스 제공.
"""

from __future__ import annotations


class LLMError(Exception):
    """LLM Provider 에러 기본 클래스."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        model: str = "",
    ) -> None:
        self.provider = provider
        self.model = model
        super().__init__(message)


class LLMAuthError(LLMError):
    """401/403 인증 실패. API 키 확인 필요."""


class LLMRateLimitError(LLMError):
    """429 Rate limit 초과."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        model: str = "",
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider=provider, model=model)


class LLMTokenLimitError(LLMError):
    """컨텍스트 윈도우 초과."""


class LLMTimeoutError(LLMError):
    """응답 타임아웃."""


class LLMProviderError(LLMError):
    """500 내부 오류 등 기타 Provider 에러."""
