# AI 에이전트 가이드

AI 에이전트를 사용하면 GPT, Claude 같은 LLM이 워크플로우의 노드들을 **도구(Tool)**로 활용하여 시장을 분석하고 의사결정을 내릴 수 있습니다.

---

## 기본 개념

AI 에이전트는 두 개의 노드로 구성됩니다:

```
LLMModelNode ──(ai_model 엣지)──▶ AIAgentNode
                                      ▲
HistoricalDataNode ──(tool 엣지)──────┘
MarketDataNode ──(tool 엣지)──────────┘
```

| 노드 | 역할 |
|------|------|
| `LLMModelNode` | LLM API 연결 (OpenAI, Anthropic 등) |
| `AIAgentNode` | 에이전트 동작 정의 (프롬프트, 도구, 출력 형식) |

---

## 빠른 시작 예시

AAPL의 기술적 분석을 AI에게 맡기는 워크플로우입니다.

```json
{
  "nodes": [
    {
      "id": "broker",
      "type": "OverseasStockBrokerNode",
      "credential_id": "my-broker"
    },
    {
      "id": "llm",
      "type": "LLMModelNode",
      "credential_id": "my-openai",
      "model": "gpt-4o",
      "temperature": 0.3
    },
    {
      "id": "history",
      "type": "OverseasStockHistoricalDataNode",
      "symbol": {"exchange": "NASDAQ", "symbol": "AAPL"},
      "interval": "1d"
    },
    {
      "id": "market",
      "type": "OverseasStockMarketDataNode",
      "symbol": {"exchange": "NASDAQ", "symbol": "AAPL"}
    },
    {
      "id": "agent",
      "type": "AIAgentNode",
      "preset": "technical_analyst",
      "user_prompt": "AAPL의 최근 차트와 현재가를 분석해서 매수/매도/관망 의견을 JSON으로 알려주세요.",
      "output_format": "json",
      "max_tool_calls": 10,
      "cooldown_sec": 60
    }
  ],
  "edges": [
    {"from": "broker", "to": "history"},
    {"from": "broker", "to": "market"},
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "broker", "to": "agent"}
  ],
  "credentials": [
    {
      "credential_id": "my-broker",
      "type": "broker_ls_overseas_stock",
      "data": [
        {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
        {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}
      ]
    },
    {
      "credential_id": "my-openai",
      "type": "llm_openai",
      "data": [
        {"key": "api_key", "value": "", "type": "password", "label": "API Key"}
      ]
    }
  ]
}
```

---

## 3가지 엣지 타입

AI 에이전트는 일반 엣지 외에 두 가지 특수 엣지를 사용합니다.

| 엣지 타입 | 용도 | 예시 |
|----------|------|------|
| `main` (기본) | 실행 순서 | `broker → agent` |
| `ai_model` | LLM 연결 | `llm → agent` |
| `tool` | 도구로 등록 | `history → agent` |

```json
{
  "edges": [
    {"from": "llm", "to": "agent", "type": "ai_model"},
    {"from": "history", "to": "agent", "type": "tool"},
    {"from": "market", "to": "agent", "type": "tool"},
    {"from": "broker", "to": "agent"}
  ]
}
```

- `ai_model` 엣지: LLMModelNode → AIAgentNode (필수, 1개)
- `tool` 엣지: 기존 노드 → AIAgentNode (여러 개 가능)
- `main` 엣지: 타입 생략 시 기본값

> tool로 등록된 노드는 AI가 **필요할 때 직접 호출**합니다. 자동으로 실행되는 것이 아닙니다.

---

## 프리셋

자주 쓰는 역할이 미리 정의되어 있습니다. `preset`을 지정하면 `system_prompt`를 직접 작성하지 않아도 됩니다.

| 프리셋 | 역할 | 주로 사용하는 Tool |
|--------|------|-------------------|
| `technical_analyst` | 기술적 지표 분석 (RSI, MACD 등) | HistoricalDataNode, ConditionNode |
| `risk_manager` | 포지션 리스크 관리 | AccountNode, MarketDataNode |
| `news_analyst` | 뉴스/이벤트 영향 분석 | HTTPRequestNode |
| `strategist` | 종합 전략 수립 | 모든 노드 |
| `custom` | 직접 프롬프트 작성 | - |

**custom 프리셋 예시:**

```json
{
  "id": "agent",
  "type": "AIAgentNode",
  "preset": "custom",
  "system_prompt": "당신은 미국 주식 시장 전문가입니다. 보수적인 투자 관점에서 분석하세요.",
  "user_prompt": "현재 포트폴리오를 분석해주세요: {{ nodes.account.positions }}",
  "output_format": "text"
}
```

---

## 출력 형식

| 형식 | 설명 | 사용 시점 |
|------|------|----------|
| `text` | 자유 텍스트 응답 | 분석 리포트, 설명 |
| `json` | JSON 구조 응답 | 후속 노드에서 데이터로 활용 |
| `structured` | 스키마 기반 검증된 JSON | 정확한 형식이 필요할 때 |

**structured 모드 예시:**

```json
{
  "id": "agent",
  "type": "AIAgentNode",
  "preset": "technical_analyst",
  "user_prompt": "AAPL 매수 여부를 판단해주세요.",
  "output_format": "structured",
  "output_schema": {
    "signal": "string (buy/sell/hold)",
    "confidence": "number (0~100)",
    "reason": "string"
  }
}
```

---

## 실시간 보호

AI 에이전트는 실시간 노드와 **직접 연결할 수 없습니다**. 반드시 ThrottleNode를 거쳐야 합니다.

**차단되는 패턴:**
```
RealMarketDataNode ──▶ AIAgentNode  (차단!)
```

**올바른 패턴:**
```
RealMarketDataNode ──▶ ThrottleNode ──▶ AIAgentNode  (OK)
```

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `cooldown_sec` | `60` | AI 호출 간 최소 대기 시간 (초) |
| `max_tool_calls` | `10` | 한 번 실행에 최대 도구 호출 수 |
| `timeout_seconds` | `60` | 최대 실행 시간 (초) |

---

## 지원 LLM 제공자

| 제공자 | credential 타입 | 모델 예시 |
|--------|----------------|----------|
| OpenAI | `llm_openai` | gpt-4o, gpt-4o-mini |
| Anthropic | `llm_anthropic` | claude-sonnet-4-5-20250929 |
| Google | `llm_google` | gemini-2.0-flash |
| Azure OpenAI | `llm_azure_openai` | (배포 이름) |
| Ollama | `llm_ollama` | llama3, mistral (로컬 실행) |

**credential 설정 예시 (OpenAI):**

```json
{
  "credential_id": "my-openai",
  "type": "llm_openai",
  "data": [
    {"key": "api_key", "value": "sk-...", "type": "password", "label": "API Key"}
  ]
}
```

---

## 실행 모니터링

`ExecutionListener`를 사용하면 AI 에이전트의 실행 상태를 실시간으로 모니터링할 수 있습니다.

| 콜백 | 설명 | 주요 데이터 |
|------|------|------------|
| `on_token_usage` | 토큰 사용량 및 비용 | `total_tokens`, `cost_usd` |
| `on_ai_tool_call` | AI가 도구를 호출할 때 | `tool_name`, `duration_ms` |
| `on_llm_stream` | LLM 스트리밍 청크 | `chunk`, `is_final` |

```python
from programgarden_core.bases import BaseExecutionListener

class MyListener(BaseExecutionListener):
    async def on_token_usage(self, node_id, data):
        print(f"[{node_id}] 토큰: {data['total_tokens']}개, 비용: ${data['cost_usd']:.4f}")

    async def on_ai_tool_call(self, node_id, data):
        print(f"[{node_id}] 도구 호출: {data['tool_name']} ({data['duration_ms']}ms)")

    async def on_llm_stream(self, node_id, data):
        if data.get('is_final'):
            print(f"[{node_id}] 응답 완료")
        else:
            print(data['chunk'], end='')
```

---

## 주의사항

- AI 에이전트는 **Stateless**입니다. 매 실행마다 이전 대화를 기억하지 않습니다.
- Tool로 등록된 노드는 AI가 필요에 따라 호출합니다. 호출하지 않을 수도 있습니다.
- `cooldown_sec`으로 과도한 API 비용을 방지하세요.
- LLM API 비용은 제공자별로 다릅니다. `max_tokens`와 `temperature`를 적절히 설정하세요.
