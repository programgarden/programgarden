"""LLM Provider 단위 테스트.

litellm, instructor를 mock하여 외부 API 호출 없이 검증.
"""

from __future__ import annotations

import pytest
import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel

from programgarden.providers import (
    LLMProvider,
    LLMConfig,
    LLMResponse,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMTokenLimitError,
    LLMTimeoutError,
    LLMProviderError,
)


# ============================================================
# Fixtures
# ============================================================


def _make_config(**overrides: Any) -> LLMConfig:
    defaults = {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "sk-test-key",
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _make_litellm_response(
    content: str = "Hello",
    model: str = "gpt-4o",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    finish_reason: str = "stop",
    tool_calls: list | None = None,
):
    """litellm ModelResponse 대체 mock 객체 생성."""
    msg = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )
    choice = SimpleNamespace(
        message=msg,
        finish_reason=finish_reason,
    )
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return SimpleNamespace(
        choices=[choice],
        usage=usage,
        model=model,
    )


# ============================================================
# LLMProvider.chat() 테스트
# ============================================================


class TestChat:
    @pytest.mark.asyncio
    async def test_basic_chat(self):
        """기본 chat 호출 및 응답 파싱."""
        config = _make_config()
        provider = LLMProvider(config)

        mock_resp = _make_litellm_response(content="Hi!", prompt_tokens=12, completion_tokens=8)

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            with patch("litellm.completion_cost", return_value=0.0003):
                result = await provider.chat([{"role": "user", "content": "Hello"}])

        assert isinstance(result, LLMResponse)
        assert result.content == "Hi!"
        assert result.model == "gpt-4o"
        assert result.input_tokens == 12
        assert result.output_tokens == 8
        assert result.total_tokens == 20
        assert result.finish_reason == "stop"
        assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        """tool_calls가 포함된 응답 파싱."""
        config = _make_config()
        provider = LLMProvider(config)

        tc = SimpleNamespace(
            id="call_123",
            function=SimpleNamespace(name="get_price", arguments='{"symbol":"AAPL"}'),
        )
        mock_resp = _make_litellm_response(
            content="",
            tool_calls=[tc],
            finish_reason="tool_calls",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            with patch("litellm.completion_cost", return_value=0.0):
                result = await provider.chat(
                    [{"role": "user", "content": "price?"}],
                    tools=[{"type": "function", "function": {"name": "get_price"}}],
                )

        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["function"]["name"] == "get_price"
        assert result.finish_reason == "tool_calls"

    @pytest.mark.asyncio
    async def test_chat_params_build(self):
        """_build_params가 올바른 litellm 파라미터를 생성하는지 확인."""
        config = _make_config(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            seed=42,
        )
        provider = LLMProvider(config)
        params = provider._build_params([{"role": "user", "content": "hi"}])

        assert params["model"] == "claude-haiku-4-5-20251001"
        assert params["api_key"] == "sk-test-key"
        assert params["seed"] == 42
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_chat_cost_calculation_fallback(self):
        """completion_cost 실패 시 0.0 반환."""
        config = _make_config()
        provider = LLMProvider(config)
        mock_resp = _make_litellm_response()

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            with patch("litellm.completion_cost", side_effect=Exception("unknown model")):
                result = await provider.chat([{"role": "user", "content": "hi"}])

        assert result.cost_usd == 0.0


# ============================================================
# LLMProvider.chat_stream() 테스트
# ============================================================


class TestChatStream:
    @pytest.mark.asyncio
    async def test_stream_collects_tokens(self):
        """스트리밍 토큰 수집 및 on_token 콜백 호출."""
        config = _make_config(streaming=True)
        provider = LLMProvider(config)

        # 스트리밍 chunk 생성
        chunks = []
        for token in ["He", "llo", " world"]:
            chunk = SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=token, tool_calls=None, model=None),
                        finish_reason=None,
                    )
                ],
                usage=None,
            )
            chunks.append(chunk)

        # 마지막 chunk (finish_reason 포함)
        final = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=None, tool_calls=None, model=None),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
        )
        chunks.append(final)

        async def mock_stream():
            for c in chunks:
                yield c

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_stream()):
            with patch("litellm.completion_cost", return_value=0.0001):
                collected: list[str] = []
                on_token = AsyncMock(side_effect=lambda t: collected.append(t))
                result = await provider.chat_stream(
                    [{"role": "user", "content": "hi"}],
                    on_token=on_token,
                )

        assert result.content == "Hello world"
        assert on_token.call_count == 3
        assert collected == ["He", "llo", " world"]
        assert result.finish_reason == "stop"


# ============================================================
# LLMProvider.chat_structured() 테스트
# ============================================================


class SentimentResult(BaseModel):
    sentiment: str
    confidence: float


class TestChatStructured:
    @pytest.mark.asyncio
    async def test_structured_output(self):
        """JSON mode + Pydantic 검증으로 구조화 출력 파싱."""
        config = _make_config()
        provider = LLMProvider(config)

        # LLM이 올바른 JSON을 반환하는 경우
        mock_resp = _make_litellm_response(
            content='{"sentiment": "positive", "confidence": 0.95}',
            prompt_tokens=20,
            completion_tokens=10,
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            with patch("litellm.completion_cost", return_value=0.0005):
                result_model, llm_resp = await provider.chat_structured(
                    [{"role": "user", "content": "analyze sentiment"}],
                    response_model=SentimentResult,
                )

        assert isinstance(result_model, SentimentResult)
        assert result_model.sentiment == "positive"
        assert result_model.confidence == 0.95
        assert llm_resp.input_tokens == 20
        assert llm_resp.output_tokens == 10
        assert llm_resp.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_structured_with_json_block(self):
        """```json ... ``` 블록 포함 응답 파싱."""
        config = _make_config()
        provider = LLMProvider(config)

        mock_resp = _make_litellm_response(
            content='Sure:\n```json\n{"sentiment": "negative", "confidence": 0.8}\n```',
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp):
            with patch("litellm.completion_cost", return_value=0.0):
                result_model, _ = await provider.chat_structured(
                    [{"role": "user", "content": "analyze"}],
                    response_model=SentimentResult,
                )

        assert result_model.sentiment == "negative"
        assert result_model.confidence == 0.8

    @pytest.mark.asyncio
    async def test_structured_retry_on_invalid(self):
        """잘못된 JSON → 에러 피드백 후 재시도."""
        config = _make_config()
        provider = LLMProvider(config)

        bad_resp = _make_litellm_response(content='not json at all')
        good_resp = _make_litellm_response(
            content='{"sentiment": "neutral", "confidence": 0.5}',
        )

        call_count = 0

        async def mock_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            return bad_resp if call_count == 1 else good_resp

        with patch("litellm.acompletion", side_effect=mock_completion):
            with patch("litellm.completion_cost", return_value=0.0):
                result_model, _ = await provider.chat_structured(
                    [{"role": "user", "content": "analyze"}],
                    response_model=SentimentResult,
                    max_retries=2,
                )

        assert result_model.sentiment == "neutral"
        assert call_count == 2  # 1번 실패 + 1번 성공


# ============================================================
# 에러 매핑 테스트
# ============================================================


class TestErrorMapping:
    def _make_provider(self) -> LLMProvider:
        return LLMProvider(_make_config())

    @pytest.mark.asyncio
    async def test_auth_error(self):
        """AuthenticationError → LLMAuthError."""
        import litellm

        provider = self._make_provider()
        exc = litellm.AuthenticationError(
            message="invalid key",
            llm_provider="openai",
            model="gpt-4o",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(LLMAuthError) as exc_info:
                await provider.chat([{"role": "user", "content": "hi"}])

        assert exc_info.value.provider == "openai"
        assert exc_info.value.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """RateLimitError → LLMRateLimitError."""
        import litellm

        provider = self._make_provider()
        exc = litellm.RateLimitError(
            message="rate limited",
            llm_provider="openai",
            model="gpt-4o",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(LLMRateLimitError):
                await provider.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_context_window_error(self):
        """ContextWindowExceededError → LLMTokenLimitError."""
        import litellm

        provider = self._make_provider()
        exc = litellm.ContextWindowExceededError(
            message="context exceeded",
            llm_provider="openai",
            model="gpt-4o",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(LLMTokenLimitError):
                await provider.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """Timeout → LLMTimeoutError."""
        import litellm

        provider = self._make_provider()
        exc = litellm.Timeout(
            message="timed out",
            llm_provider="openai",
            model="gpt-4o",
        )

        with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(LLMTimeoutError):
                await provider.chat([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_generic_error(self):
        """기타 예외 → LLMProviderError."""
        provider = self._make_provider()

        with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            with pytest.raises(LLMProviderError):
                await provider.chat([{"role": "user", "content": "hi"}])


# ============================================================
# LLMProvider.from_connection() 테스트
# ============================================================


class TestFromConnection:
    def test_basic(self):
        """connection dict → LLMProvider 변환."""
        conn = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5-20250929",
            "api_key": "sk-ant-xxx",
            "temperature": 0.5,
            "max_tokens": 2000,
            "streaming": True,
        }
        provider = LLMProvider.from_connection(conn)

        assert provider.config.provider == "anthropic"
        assert provider.config.model == "claude-sonnet-4-5-20250929"
        assert provider.config.api_key == "sk-ant-xxx"
        assert provider.config.temperature == 0.5
        assert provider.config.max_tokens == 2000
        assert provider.config.streaming is True

    def test_defaults(self):
        """누락 필드는 기본값 적용."""
        provider = LLMProvider.from_connection({})

        assert provider.config.provider == "openai"
        assert provider.config.model == "gpt-4o"
        assert provider.config.temperature == 0.7
        assert provider.config.max_tokens == 1000
        assert provider.config.streaming is False

    def test_anthropic_fields(self):
        """Anthropic 필드 포함 변환."""
        conn = {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key": "sk-ant-xxx",
        }
        provider = LLMProvider.from_connection(conn)

        assert provider.config.provider == "anthropic"
        assert provider.config.model == "claude-haiku-4-5-20251001"
        assert provider.config.api_key == "sk-ant-xxx"


# ============================================================
# LLMModelNodeExecutor 테스트
# ============================================================


class TestLLMModelNodeExecutor:
    """executor.py의 LLMModelNodeExecutor 테스트."""

    def _make_context(self, credential_data: dict | None = None):
        """간이 ExecutionContext mock."""
        ctx = MagicMock()
        ctx.log = MagicMock()
        ctx.get_workflow_credential = MagicMock(return_value=credential_data)
        return ctx

    @pytest.mark.asyncio
    async def test_openai_connection(self):
        """OpenAI credential → connection dict 변환."""
        from programgarden.executor import LLMModelNodeExecutor

        executor = LLMModelNodeExecutor()
        config = {
            "credential_id": "my-openai",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 2000,
            "streaming": True,
        }
        ctx = self._make_context({
            "provider": "openai",
            "api_key": "sk-xxx",
            "organization": "org-123",
        })

        result = await executor.execute("llm-1", "LLMModelNode", config, ctx)

        conn = result["connection"]
        assert conn["provider"] == "openai"
        assert conn["model"] == "gpt-4o"  # openai는 prefix 없음
        assert conn["api_key"] is None  # secrets에 별도 저장됨
        ctx.set_secret.assert_called_once_with("llm_api_key_llm-1", "sk-xxx")
        assert conn["organization"] == "org-123"
        assert conn["temperature"] == 0.5
        assert conn["max_tokens"] == 2000
        assert conn["streaming"] is True

    @pytest.mark.asyncio
    async def test_anthropic_connection(self):
        """Anthropic credential → connection dict 변환."""
        from programgarden.executor import LLMModelNodeExecutor

        executor = LLMModelNodeExecutor()
        config = {
            "credential_id": "my-anthropic",
            "model": "claude-haiku-4-5-20251001",
        }
        ctx = self._make_context({
            "provider": "anthropic",
            "api_key": "sk-ant-xxx",
        })

        result = await executor.execute("llm-1", "LLMModelNode", config, ctx)
        conn = result["connection"]
        assert conn["provider"] == "anthropic"
        assert conn["model"] == "claude-haiku-4-5-20251001"
        assert conn["api_key"] is None  # secrets에 별도 저장됨
        ctx.set_secret.assert_called_once_with("llm_api_key_llm-1", "sk-ant-xxx")


# ============================================================
# 실제 API 호출 테스트 (ANTHROPIC_API_KEY 필요)
# ============================================================


class TestRealAPI:
    @pytest.mark.asyncio
    async def test_haiku_chat(self):
        """Claude Haiku 실제 API 호출."""
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        config = _make_config(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            api_key=api_key,
            max_tokens=30,
        )
        provider = LLMProvider(config)
        result = await provider.chat([{"role": "user", "content": "Say hello in one word."}])

        assert isinstance(result, LLMResponse)
        assert result.content
        assert result.input_tokens > 0
        assert result.output_tokens > 0
