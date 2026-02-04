#!/usr/bin/env python
"""
Dynamic Node Injection 실전 테스트

실제 WorkflowExecutor를 사용하여 동적 노드 전체 흐름 테스트:
1. 스키마 등록
2. 워크플로우 검증
3. 클래스 주입
4. 워크플로우 실행
5. 결과 확인

실행:
    cd src/programgarden
    poetry run python examples/test_dynamic_node_real.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add paths for imports
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "programgarden"))

from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort, InputPort
from programgarden_core.registry import DynamicNodeRegistry


# ============================================
# 1. 테스트용 동적 노드 클래스 정의
# ============================================

class CustomRSINode(BaseNode):
    """커스텀 RSI 지표 노드"""
    type: str = "Custom_RSI"
    category: NodeCategory = NodeCategory.CONDITION
    period: int = 14
    overbought: float = 70.0
    oversold: float = 30.0

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=False, description="시세 데이터"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number", description="RSI 값"),
        OutputPort(name="signal", type="string", description="매매 신호"),
        OutputPort(name="message", type="string", description="분석 메시지"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        """RSI 계산 및 신호 생성"""
        # 실제 RSI 계산 로직은 생략, 테스트용 값 반환
        rsi_value = 28.5  # 테스트용 값

        if rsi_value < self.oversold:
            signal = "buy"
            message = f"RSI {rsi_value:.1f} < {self.oversold} (과매도)"
        elif rsi_value > self.overbought:
            signal = "sell"
            message = f"RSI {rsi_value:.1f} > {self.overbought} (과매수)"
        else:
            signal = "hold"
            message = f"RSI {rsi_value:.1f} (중립)"

        context.log("info", f"[Custom_RSI] {message}", self.id)

        return {
            "rsi": rsi_value,
            "signal": signal,
            "message": message,
        }


class CustomLoggerNode(BaseNode):
    """커스텀 로깅 노드"""
    type: str = "Custom_Logger"
    category: NodeCategory = NodeCategory.DATA
    prefix: str = "[LOG]"

    _inputs: List[InputPort] = [
        InputPort(name="input", type="any", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="logged", type="boolean"),
        OutputPort(name="output", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        """입력값 로깅"""
        output = f"{self.prefix} Executed at node {self.id}"
        context.log("info", output, self.id)

        return {
            "logged": True,
            "output": output,
        }


# ============================================
# 2. 테스트용 Listener
# ============================================

class TestListener:
    """테스트용 리스너"""

    def __init__(self):
        self.events = []

    async def on_node_state_change(self, node_id, node_type, state, outputs=None, error=None):
        event = {
            "type": "node_state",
            "node_id": node_id,
            "node_type": node_type,
            "state": state,
            "outputs": outputs,
        }
        self.events.append(event)
        print(f"  📍 Node [{node_id}] ({node_type}): {state}")
        if outputs:
            for key, value in outputs.items():
                if not key.startswith("_"):
                    print(f"      → {key}: {value}")

    async def on_log(self, level, message, node_id=None):
        print(f"  📝 [{level.upper()}] {message}")

    async def on_job_state_change(self, job_id, state, error=None):
        print(f"  🎯 Job [{job_id}]: {state}")


# ============================================
# 3. 테스트 실행
# ============================================

async def test_dynamic_node_injection():
    """동적 노드 주입 실전 테스트"""

    print("=" * 60)
    print("🧪 Dynamic Node Injection 실전 테스트")
    print("=" * 60)

    # DynamicNodeRegistry 초기화
    DynamicNodeRegistry.reset_instance()

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()

    # ----------------------------------------
    # Step 1: 스키마 등록
    # ----------------------------------------
    print("\n📋 Step 1: 스키마 등록")

    schemas = [
        {
            "node_type": "Custom_RSI",
            "category": "condition",
            "description": "커스텀 RSI 지표 노드",
            "inputs": [{"name": "data", "type": "array", "required": False}],
            "outputs": [
                {"name": "rsi", "type": "number"},
                {"name": "signal", "type": "string"},
                {"name": "message", "type": "string"},
            ],
            "config_schema": {
                "period": {"type": "integer", "default": 14},
                "overbought": {"type": "number", "default": 70.0},
                "oversold": {"type": "number", "default": 30.0},
            },
        },
        {
            "node_type": "Custom_Logger",
            "category": "data",
            "description": "커스텀 로깅 노드",
            "inputs": [{"name": "input", "type": "any", "required": False}],
            "outputs": [
                {"name": "logged", "type": "boolean"},
                {"name": "output", "type": "string"},
            ],
            "config_schema": {
                "prefix": {"type": "string", "default": "[LOG]"},
            },
        },
    ]

    executor.register_dynamic_schemas(schemas)
    print(f"  ✅ 등록된 스키마: {executor.list_dynamic_node_types()}")

    # ----------------------------------------
    # Step 2: 워크플로우 정의
    # ----------------------------------------
    print("\n📋 Step 2: 워크플로우 정의")

    workflow = {
        "id": "test-dynamic-workflow",
        "name": "Dynamic Node Test",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "rsi", "type": "Custom_RSI", "period": 14, "oversold": 30.0, "overbought": 70.0},
            {"id": "logger", "type": "Custom_Logger", "prefix": "[TEST]"},
        ],
        "edges": [
            {"from": "start", "to": "rsi"},
            {"from": "rsi", "to": "logger"},
        ],
    }

    print(f"  📍 노드: {[n['id'] for n in workflow['nodes']]}")
    print(f"  📍 엣지: {[(e['from'], e['to']) for e in workflow['edges']]}")

    # ----------------------------------------
    # Step 3: 필요한 커스텀 타입 확인
    # ----------------------------------------
    print("\n📋 Step 3: 필요한 커스텀 타입 확인")

    required_types = executor.get_required_custom_types(workflow)
    print(f"  ✅ 필요한 커스텀 타입: {required_types}")

    # ----------------------------------------
    # Step 4: 검증 (클래스 주입 전)
    # ----------------------------------------
    print("\n📋 Step 4: 워크플로우 검증")

    validation = executor.validate(workflow)
    print(f"  ✅ 검증 결과: {'통과' if validation.is_valid else '실패'}")
    if validation.errors:
        for error in validation.errors:
            print(f"    ❌ {error}")
    if validation.warnings:
        for warning in validation.warnings:
            print(f"    ⚠️ {warning}")

    if not validation.is_valid:
        print("\n❌ 검증 실패. 테스트 중단.")
        return False

    # ----------------------------------------
    # Step 5: 클래스 주입
    # ----------------------------------------
    print("\n📋 Step 5: 클래스 주입")

    executor.inject_node_classes({
        "Custom_RSI": CustomRSINode,
        "Custom_Logger": CustomLoggerNode,
    })

    for node_type in required_types:
        ready = executor.is_dynamic_node_ready(node_type)
        print(f"  {'✅' if ready else '❌'} {node_type}: {'준비 완료' if ready else '준비 안 됨'}")

    # ----------------------------------------
    # Step 6: 워크플로우 실행
    # ----------------------------------------
    print("\n📋 Step 6: 워크플로우 실행")

    listener = TestListener()

    try:
        job = await executor.execute(
            workflow,
            listeners=[listener],
        )

        print(f"\n  🚀 Job 시작: {job.job_id}")

        # 실행 완료 대기 (최대 10초)
        for _ in range(100):
            if job.status in ("completed", "failed"):
                break
            await asyncio.sleep(0.1)

        print(f"\n  🏁 Job 상태: {job.status}")

        # Job 정리
        if job.status == "running":
            await job.stop()

    except Exception as e:
        print(f"\n  ❌ 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

    # ----------------------------------------
    # Step 7: 결과 확인
    # ----------------------------------------
    print("\n📋 Step 7: 결과 확인")

    # 이벤트 요약
    node_results = {}
    for event in listener.events:
        if event["type"] == "node_state" and event["state"] == "completed":
            node_results[event["node_id"]] = event.get("outputs", {})

    print(f"  📊 완료된 노드: {list(node_results.keys())}")

    # 동적 노드 결과 확인
    if "rsi" in node_results:
        rsi_result = node_results["rsi"]
        print(f"\n  📈 Custom_RSI 결과:")
        print(f"      RSI: {rsi_result.get('rsi')}")
        print(f"      Signal: {rsi_result.get('signal')}")
        print(f"      Message: {rsi_result.get('message')}")

    if "logger" in node_results:
        logger_result = node_results["logger"]
        print(f"\n  📝 Custom_Logger 결과:")
        print(f"      Logged: {logger_result.get('logged')}")
        print(f"      Output: {logger_result.get('output')}")

    # ----------------------------------------
    # Step 8: 메모리 정리
    # ----------------------------------------
    print("\n📋 Step 8: 메모리 정리")

    executor.clear_injected_classes()
    print("  ✅ 주입된 클래스 초기화 완료")

    # 스키마는 유지되는지 확인
    remaining = executor.list_dynamic_node_types()
    print(f"  📋 남아있는 스키마: {remaining}")

    print("\n" + "=" * 60)
    print("✅ 실전 테스트 완료!")
    print("=" * 60)

    return True


# ============================================
# 4. 추가 테스트: credential_id 사용 차단
# ============================================

async def test_credential_blocked():
    """동적 노드에서 credential_id 사용 차단 테스트"""

    print("\n" + "=" * 60)
    print("🧪 credential_id 차단 테스트")
    print("=" * 60)

    DynamicNodeRegistry.reset_instance()

    from programgarden import WorkflowExecutor

    executor = WorkflowExecutor()

    # 스키마 등록
    executor.register_dynamic_schemas([{
        "node_type": "Custom_Test",
        "category": "data",
        "outputs": [{"name": "result", "type": "string"}],
    }])

    # credential_id를 사용하는 워크플로우
    workflow = {
        "id": "test-cred-blocked",
        "name": "Credential Blocked Test",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "custom", "type": "Custom_Test", "credential_id": "my-secret"},
        ],
        "edges": [{"from": "start", "to": "custom"}],
    }

    validation = executor.validate(workflow)

    if not validation.is_valid:
        print("  ✅ 예상대로 검증 실패!")
        for error in validation.errors:
            print(f"    → {error}")
        return True
    else:
        print("  ❌ 검증이 통과되어버림 (오류!)")
        return False


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    print("\n🌱 ProgramGarden - Dynamic Node Injection 실전 테스트\n")

    success1 = asyncio.run(test_dynamic_node_injection())
    success2 = asyncio.run(test_credential_blocked())

    if success1 and success2:
        print("\n✅ 모든 실전 테스트 통과!")
        sys.exit(0)
    else:
        print("\n❌ 일부 테스트 실패")
        sys.exit(1)
