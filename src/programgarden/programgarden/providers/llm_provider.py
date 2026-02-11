"""LLM Provider - LiteLLM 통합 래퍼.

단일 클래스로 OpenAI, Anthropic, Azure OpenAI, Ollama 등 100+ 모델 지원.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from pydantic import BaseModel

from .llm_errors import (
    LLMAuthError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTokenLimitError,
)

logger = logging.getLogger("programgarden.providers.llm")


@dataclass
class LLMConfig:
    """LLMModelNode connection 출력에서 생성되는 설정."""

    provider: str  # "openai" | "anthropic" | "azure" | "ollama"
    model: str  # litellm 형식 ("gpt-4o", "azure/deploy", "ollama/llama3")
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None  # OpenAI
    api_version: str | None = None  # Azure
    temperature: float = 0.7
    max_tokens: int = 1000
    seed: int | None = None
    streaming: bool = False


@dataclass
class LLMResponse:
    """LLM 호출 결과."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    tool_calls: list[dict] | None = None
    finish_reason: str = "stop"
    raw_response: Any = None


class LLMProvider:
    """LiteLLM 기반 통합 LLM Provider.

    모든 벤더(OpenAI, Anthropic, Azure, Ollama)를 단일 인터페이스로 지원.
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @classmethod
    def from_connection(cls, conn: dict[str, Any]) -> LLMProvider:
        """LLMModelNode의 connection dict에서 Provider 생성."""
        return cls(
            LLMConfig(
                provider=conn.get("provider", "openai"),
                model=conn.get("model", "gpt-4o"),
                api_key=conn.get("api_key"),
                base_url=conn.get("base_url"),
                organization=conn.get("organization"),
                api_version=conn.get("api_version"),
                temperature=conn.get("temperature", 0.7),
                max_tokens=conn.get("max_tokens", 1000),
                seed=conn.get("seed"),
                streaming=conn.get("streaming", False),
            )
        )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """비스트리밍 LLM 호출."""
        import litellm

        params = self._build_params(messages, tools, **kwargs)

        try:
            response = await litellm.acompletion(**params)
        except Exception as exc:
            raise self._convert_error(exc) from exc

        return self._parse_response(response)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        on_token: Callable[[str], Awaitable[None]] | None = None,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """스트리밍 LLM 호출."""
        import litellm

        params = self._build_params(messages, tools, **kwargs)
        params["stream"] = True

        collected_content: list[str] = []
        tool_calls_chunks: list[dict] = []
        finish_reason = "stop"
        model_name = self.config.model
        raw_response = None

        try:
            response = await litellm.acompletion(**params)
            async for chunk in response:
                raw_response = chunk
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if hasattr(delta, "model") and delta.model:
                    model_name = delta.model

                if delta.content:
                    collected_content.append(delta.content)
                    if on_token:
                        await on_token(delta.content)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls_chunks.append(
                            {
                                "id": getattr(tc, "id", None),
                                "type": "function",
                                "function": {
                                    "name": getattr(tc.function, "name", None),
                                    "arguments": getattr(tc.function, "arguments", ""),
                                },
                            }
                        )

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

        except Exception as exc:
            raise self._convert_error(exc) from exc

        content = "".join(collected_content)

        # 스트리밍에서는 usage가 마지막 chunk에 올 수 있음
        usage = getattr(raw_response, "usage", None) if raw_response else None
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        cost = self._calc_cost(model_name, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            tool_calls=tool_calls_chunks or None,
            finish_reason=finish_reason,
            raw_response=raw_response,
        )

    async def chat_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
        max_retries: int = 2,
        **kwargs: Any,
    ) -> tuple[BaseModel, LLMResponse]:
        """구조화 출력 (JSON mode + Pydantic 검증).

        instructor 없이 직접 구현:
        1. response_model의 JSON schema를 시스템 프롬프트에 주입
        2. LLM에 JSON 출력 요청
        3. Pydantic으로 검증 (실패 시 에러 피드백 후 재시도)
        """
        import json

        schema = response_model.model_json_schema()
        schema_instruction = (
            "\n\n[출력 규칙] 반드시 다음 JSON 스키마에 맞춰 응답하세요:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n"
            "JSON 외의 텍스트는 출력하지 마세요."
        )

        # 메시지 복사 후 시스템 프롬프트에 스키마 지시 추가
        augmented = list(messages)
        if augmented and augmented[0].get("role") == "system":
            augmented[0] = {**augmented[0], "content": augmented[0]["content"] + schema_instruction}
        else:
            augmented.insert(0, {"role": "system", "content": schema_instruction})

        last_error = None
        for attempt in range(max_retries + 1):
            response = await self.chat(augmented, **kwargs)

            text = response.content.strip()
            # ```json ... ``` 블록 추출
            if "```json" in text:
                start = text.index("```json") + len("```json")
                end = text.index("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.index("```") + 3
                end = text.index("```", start)
                text = text[start:end].strip()

            try:
                data = json.loads(text)
                result = response_model.model_validate(data)
                llm_response = LLMResponse(
                    content=result.model_dump_json(),
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    total_tokens=response.total_tokens,
                    cost_usd=response.cost_usd,
                    finish_reason="stop",
                    raw_response=response.raw_response,
                )
                return result, llm_response
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    # 에러 피드백을 메시지에 추가하여 재시도
                    augmented.append({"role": "assistant", "content": response.content})
                    augmented.append({
                        "role": "user",
                        "content": f"JSON 파싱/검증 실패: {e}\n올바른 JSON으로 다시 응답해주세요.",
                    })

        raise ValueError(f"Structured output 파싱 실패 ({max_retries + 1}회 시도): {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_params(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """litellm.acompletion 파라미터 빌드."""
        cfg = self.config

        params: dict[str, Any] = {
            "model": cfg.model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
        }

        if cfg.api_key:
            params["api_key"] = cfg.api_key
        if cfg.base_url:
            params["api_base"] = cfg.base_url
        if cfg.organization:
            params["organization"] = cfg.organization
        if cfg.api_version:
            params["api_version"] = cfg.api_version
        if cfg.seed is not None:
            params["seed"] = cfg.seed
        if tools:
            params["tools"] = tools

        params.update(kwargs)
        return params

    def _parse_response(self, response: Any) -> LLMResponse:
        """litellm 응답을 LLMResponse로 변환."""
        choice = response.choices[0]
        message = choice.message
        usage = response.usage

        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        model_name = response.model or self.config.model

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        cost = self._calc_cost(model_name, input_tokens, output_tokens)

        return LLMResponse(
            content=message.content or "",
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            raw_response=response,
        )

    def _calc_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """비용 계산 (litellm.completion_cost 활용, 실패 시 0)."""
        try:
            import litellm

            return litellm.completion_cost(
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
            )
        except Exception:
            return 0.0

    def _convert_error(self, exc: Exception) -> Exception:
        """litellm 예외를 커스텀 LLM 에러로 변환."""
        import litellm

        provider = self.config.provider
        model = self.config.model
        msg = str(exc)

        if isinstance(exc, litellm.AuthenticationError):
            return LLMAuthError(msg, provider=provider, model=model)
        if isinstance(exc, litellm.RateLimitError):
            retry_after = getattr(exc, "retry_after", None)
            return LLMRateLimitError(
                msg, provider=provider, model=model, retry_after=retry_after
            )
        if isinstance(exc, litellm.ContextWindowExceededError):
            return LLMTokenLimitError(msg, provider=provider, model=model)
        if isinstance(exc, litellm.Timeout):
            return LLMTimeoutError(msg, provider=provider, model=model)
        return LLMProviderError(msg, provider=provider, model=model)
