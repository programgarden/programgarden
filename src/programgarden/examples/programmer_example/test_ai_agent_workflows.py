"""AI Agent 워크플로우 32~36 JSON 통합 테스트.

실제 워크플로우 JSON 파일을 로드하고, .env의 크리덴셜을 주입하여 실행합니다.
Broker/LLM 크리덴셜이 모두 필요합니다.

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_ai_agent_workflows.py
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

# 워크플로우 JSON 경로
WORKFLOWS_DIR = project_root / "src" / "programgarden" / "examples" / "workflows"

# 테스트 타임아웃 (초) - Tool 호출 포함 워크플로우는 더 오래 걸림
TIMEOUT_SIMPLE = 60      # Tool 없는 워크플로우
TIMEOUT_WITH_TOOLS = 120  # Tool 있는 워크플로우


class TestListener(BaseExecutionListener):
    """테스트용 리스너."""

    async def on_node_state_change(self, event):
        print(f"  [{event.node_id}] {event.state.value}")

    async def on_log(self, event):
        if event.level in ("info", "warning", "error"):
            print(f"  📝 [{event.level}] {event.message}")

    async def on_token_usage(self, event):
        print(f"  💰 Token: {event.total_tokens} tokens, ${event.cost_usd:.4f}")

    async def on_ai_tool_call(self, event):
        print(f"  🛠️  Tool: {event.tool_name} ({event.duration_ms:.0f}ms)")


async def _wait_for_job(job, timeout: float):
    """Job 완료 대기 (타임아웃 포함)."""
    try:
        await asyncio.wait_for(job._task, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"  ⏰ TIMEOUT ({timeout}s) - 강제 종료")
        await job.stop()
        job.status = "timeout"


def _inject_credentials(workflow: dict) -> dict:
    """워크플로우 JSON의 credential_id에 실제 키를 주입."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    appkey = os.environ.get("APPKEY")
    appsecret = os.environ.get("APPSECRET")

    new_creds = []
    for cred in workflow.get("credentials", []):
        cred_id = cred.get("credential_id", "")

        # LLM credential (18a59164...) → Anthropic 또는 OpenAI
        if cred_id == "18a59164-9450-4b22-bccf-f42e7c5b71f6":
            if anthropic_key:
                new_creds.append({
                    "credential_id": cred_id,
                    "type": "llm_anthropic",
                    "data": {"api_key": anthropic_key},
                })
            elif openai_key:
                # Anthropic 키가 없으면 OpenAI로 대체
                new_creds.append({
                    "credential_id": cred_id,
                    "type": "llm_openai",
                    "data": {"api_key": openai_key},
                })
                # 모델도 변경
                for node in workflow.get("nodes", []):
                    if node.get("type") == "LLMModelNode":
                        node["model"] = "gpt-4o-mini"
            else:
                print("  ⚠️ LLM API 키 없음")
                return None

        # Broker credential (7c5caa90...) → LS Securities
        elif cred_id == "7c5caa90-f013-44fd-855d-410437c86737":
            if appkey and appsecret:
                new_creds.append({
                    "credential_id": cred_id,
                    "type": "broker_ls_overseas_stock",
                    "data": [
                        {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                        {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
                    ],
                })
            else:
                print("  ⚠️ LS Securities API 키 없음")
                return None
        else:
            new_creds.append(cred)

    workflow["credentials"] = new_creds
    return workflow


async def test_workflow(workflow_file: str, timeout: float) -> bool:
    """워크플로우 JSON 파일을 로드하고 실행."""
    filepath = WORKFLOWS_DIR / workflow_file
    if not filepath.exists():
        print(f"  ⚠️ 파일 없음: {filepath}")
        return None

    with open(filepath) as f:
        workflow = json.load(f)

    print(f"\n{'=' * 60}")
    print(f"Workflow: {workflow.get('name', workflow_file)}")
    print(f"  파일: {workflow_file}")
    print(f"  노드: {len(workflow.get('nodes', []))}")
    print(f"  엣지: {len(workflow.get('edges', []))}")
    print("=" * 60)

    # 크리덴셜 주입
    workflow = _inject_credentials(workflow)
    if workflow is None:
        print("  ⏭️ 크리덴셜 부족으로 SKIP")
        return None

    # paper_trading 모드 설정 (실전 주문 방지)
    for node in workflow.get("nodes", []):
        if "paper_trading" not in node:
            node["paper_trading"] = True

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    await _wait_for_job(job, timeout)

    # 결과 확인
    agent_result = job.context.get_all_outputs("agent")
    response = agent_result.get("response")

    print(f"\n📤 Response type: {type(response).__name__}")
    if isinstance(response, dict):
        print(f"📤 Response: {json.dumps(response, ensure_ascii=False, indent=2)[:600]}")
    elif response:
        print(f"📤 Response: {str(response)[:600]}")
    else:
        print(f"📤 Response: (없음)")

    print(f"✅ Status: {job.status}")

    if job.status == "timeout":
        print("❌ FAIL (timeout)")
        return False

    success = job.status == "completed" and response is not None
    print(f"{'✅ PASS' if success else '❌ FAIL'}")
    return success


async def main():
    print("🤖 AI Agent Workflow 32~36 통합 테스트")
    print("=" * 60)

    # 키 확인
    has_llm = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    has_broker = bool(os.environ.get("APPKEY") and os.environ.get("APPSECRET"))
    print(f"  LLM API 키: {'✅' if has_llm else '❌'}")
    print(f"  Broker API 키: {'✅' if has_broker else '❌'}")

    tests = [
        # (파일명, 타임아웃, Tool 사용 여부)
        ("32-ai-agent-basic.json", TIMEOUT_SIMPLE),           # LLM만
        ("33-ai-agent-risk-manager.json", TIMEOUT_WITH_TOOLS), # LLM + Broker Tool
        ("34-ai-agent-technical-analyst.json", TIMEOUT_WITH_TOOLS),
        ("35-ai-agent-strategist.json", TIMEOUT_WITH_TOOLS),
        ("36-ai-agent-json-output.json", TIMEOUT_WITH_TOOLS),
    ]

    results = {}
    for filename, timeout in tests:
        name = filename.replace(".json", "")
        try:
            result = await test_workflow(filename, timeout)
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
    print("📊 Workflow Test Results")
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
