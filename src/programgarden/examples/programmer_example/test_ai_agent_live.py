"""AI Agent 노드 실제 LLM API 테스트.

.env의 OPENAI_API_KEY / ANTHROPIC_API_KEY를 사용하여
32~36번 워크플로우의 핵심 흐름을 테스트합니다.

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_ai_agent_live.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 경로 설정
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))

# .env 로드
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from programgarden import ProgramGarden
from programgarden_core.bases.listener import BaseExecutionListener


# 테스트 타임아웃 (초)
TEST_TIMEOUT = 60


class TestListener(BaseExecutionListener):
    """테스트용 리스너 - 이벤트 콘솔 출력."""

    async def on_node_state_change(self, event):
        print(f"  [{event.node_id}] {event.state.value}")

    async def on_log(self, event):
        if event.level in ("info", "warning", "error"):
            print(f"  📝 [{event.level}] {event.message}")

    async def on_token_usage(self, event):
        print(f"  💰 Token: {event.total_tokens} tokens, ${event.cost_usd:.4f}")

    async def on_ai_tool_call(self, event):
        print(f"  🛠️  Tool: {event.tool_name} ({event.duration_ms:.0f}ms)")

    async def on_llm_stream(self, event):
        if event.is_final:
            print(f"  📡 Stream complete")


async def _wait_for_job(job, timeout: float = TEST_TIMEOUT):
    """Job 완료 대기 (타임아웃 포함)."""
    try:
        await asyncio.wait_for(job._task, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"  ⏰ TIMEOUT ({timeout}s) - 강제 종료")
        await job.stop()
        job.status = "timeout"


# ============================================================
# 테스트 1: 기본 텍스트 응답 (워크플로우 32 패턴)
# ============================================================
async def test_basic_text_response():
    """LLMModelNode → AIAgentNode (텍스트 응답, Tool 없음)"""
    print("\n" + "=" * 60)
    print("Test 1: 기본 텍스트 응답 (OpenAI GPT-4o-mini)")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping")
        return None

    workflow = {
        "id": "test-basic",
        "name": "AI Agent Basic Test",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "llm",
                "type": "LLMModelNode",
                "credential_id": "test-openai",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 200,
            },
            {
                "id": "agent",
                "type": "AIAgentNode",
                "system_prompt": "당신은 금융 분석가입니다. 한국어로 답하세요.",
                "user_prompt": "미국 S&P 500 지수에 대해 한 줄로 설명해주세요.",
                "output_format": "text",
                "max_tool_calls": 0,
                "timeout_seconds": 30,
            },
        ],
        "edges": [
            {"from": "start", "to": "llm"},
            {"from": "llm", "to": "agent", "type": "ai_model"},
        ],
        "credentials": [
            {
                "credential_id": "test-openai",
                "type": "llm_openai",
                "data": {"api_key": api_key},
            }
        ],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    await _wait_for_job(job)

    result = job.context.get_all_outputs("agent")
    response = result.get("response", "N/A")
    print(f"\n📤 Response: {response}")
    print(f"✅ Status: {job.status}")

    success = job.status == "completed" and response and response != "N/A"
    print(f"{'✅ PASS' if success else '❌ FAIL'}")
    return success


# ============================================================
# 테스트 2: Anthropic Claude + JSON 출력 (워크플로우 36 패턴)
# ============================================================
async def test_anthropic_json_output():
    """Anthropic Claude로 JSON 출력."""
    print("\n" + "=" * 60)
    print("Test 2: Anthropic Claude JSON 출력")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set, skipping")
        return None

    workflow = {
        "id": "test-json",
        "name": "AI Agent JSON Test",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "llm",
                "type": "LLMModelNode",
                "credential_id": "test-anthropic",
                "model": "claude-haiku-4-5-20251001",
                "temperature": 0.3,
                "max_tokens": 500,
            },
            {
                "id": "agent",
                "type": "AIAgentNode",
                "system_prompt": "당신은 금융 데이터 분석가입니다.",
                "user_prompt": "AAPL, NVDA, TSLA 세 종목에 대한 투자 의견을 JSON으로 제공해주세요.",
                "output_format": "json",
                "max_tool_calls": 0,
                "timeout_seconds": 30,
            },
        ],
        "edges": [
            {"from": "start", "to": "llm"},
            {"from": "llm", "to": "agent", "type": "ai_model"},
        ],
        "credentials": [
            {
                "credential_id": "test-anthropic",
                "type": "llm_anthropic",
                "data": {"api_key": api_key},
            }
        ],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    await _wait_for_job(job)

    result = job.context.get_all_outputs("agent")
    response = result.get("response")
    print(f"\n📤 Response type: {type(response).__name__}")
    if isinstance(response, dict):
        print(f"📤 Response: {json.dumps(response, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"📤 Response: {str(response)[:500]}")
    print(f"✅ Status: {job.status}")

    success = job.status == "completed" and isinstance(response, dict)
    print(f"{'✅ PASS' if success else '❌ FAIL'}")
    return success


# ============================================================
# 테스트 3: Structured Output (워크플로우 33 패턴)
# ============================================================
async def test_structured_output():
    """프리셋 + Structured Output (output_schema)."""
    print("\n" + "=" * 60)
    print("Test 3: Structured Output (risk_manager 프리셋)")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping")
        return None

    workflow = {
        "id": "test-structured",
        "name": "AI Agent Structured Test",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "llm",
                "type": "LLMModelNode",
                "credential_id": "test-openai",
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 500,
            },
            {
                "id": "agent",
                "type": "AIAgentNode",
                "preset": "risk_manager",
                "user_prompt": "AAPL 100주, TSLA 50주 보유 중입니다. AAPL은 +5%, TSLA는 -12% 수익률입니다. 포트폴리오 위험을 분석해주세요.",
                "timeout_seconds": 30,
            },
        ],
        "edges": [
            {"from": "start", "to": "llm"},
            {"from": "llm", "to": "agent", "type": "ai_model"},
        ],
        "credentials": [
            {
                "credential_id": "test-openai",
                "type": "llm_openai",
                "data": {"api_key": api_key},
            }
        ],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    await _wait_for_job(job)

    result = job.context.get_all_outputs("agent")
    response = result.get("response")
    print(f"\n📤 Response type: {type(response).__name__}")
    if isinstance(response, dict):
        print(f"📤 Response: {json.dumps(response, ensure_ascii=False, indent=2)[:500]}")
        risk_level = response.get("risk_level", "")
        has_valid_risk_level = risk_level in ("low", "medium", "high", "critical")
        print(f"📤 risk_level: {risk_level} {'✅' if has_valid_risk_level else '⚠️'}")
    else:
        print(f"📤 Response: {str(response)[:500]}")
    print(f"✅ Status: {job.status}")

    success = job.status == "completed" and isinstance(response, dict)
    print(f"{'✅ PASS' if success else '❌ FAIL'}")
    return success


# ============================================================
# 테스트 4: 스트리밍 응답
# ============================================================
async def test_streaming():
    """스트리밍 응답 (streaming=True)."""
    print("\n" + "=" * 60)
    print("Test 4: 스트리밍 응답 (OpenAI)")
    print("=" * 60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping")
        return None

    workflow = {
        "id": "test-streaming",
        "name": "AI Agent Streaming Test",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "llm",
                "type": "LLMModelNode",
                "credential_id": "test-openai",
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 200,
                "streaming": True,
            },
            {
                "id": "agent",
                "type": "AIAgentNode",
                "system_prompt": "한국어로 간결하게 답하세요.",
                "user_prompt": "비트코인이 뭔가요? 2문장으로 설명해주세요.",
                "output_format": "text",
                "max_tool_calls": 0,
                "timeout_seconds": 30,
            },
        ],
        "edges": [
            {"from": "start", "to": "llm"},
            {"from": "llm", "to": "agent", "type": "ai_model"},
        ],
        "credentials": [
            {
                "credential_id": "test-openai",
                "type": "llm_openai",
                "data": {"api_key": api_key},
            }
        ],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    await _wait_for_job(job)

    result = job.context.get_all_outputs("agent")
    response = result.get("response", "N/A")
    print(f"\n📤 Response: {response}")
    print(f"✅ Status: {job.status}")

    success = job.status == "completed" and response and response != "N/A"
    print(f"{'✅ PASS' if success else '❌ FAIL'}")
    return success


# ============================================================
# Main
# ============================================================
async def main():
    print("🤖 AI Agent Live API Test Suite")
    print("=" * 60)

    results = {}
    tests = [
        ("basic_text", test_basic_text_response),
        ("anthropic_json", test_anthropic_json_output),
        ("structured_output", test_structured_output),
        ("streaming", test_streaming),
    ]

    for name, test_fn in tests:
        try:
            result = await test_fn()
            if result is None:
                results[name] = "skipped"
            else:
                results[name] = result
        except Exception as e:
            import traceback
            print(f"\n❌ {name} EXCEPTION: {e}")
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    for name, passed in results.items():
        if passed == "skipped":
            status = "⏭️ SKIP"
        elif passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"  {status}  {name}")

    total = sum(1 for v in results.values() if v != "skipped")
    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v == "skipped")
    print(f"\n  Total: {passed}/{total} passed ({skipped} skipped)")

    return all(v is True or v == "skipped" for v in results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
