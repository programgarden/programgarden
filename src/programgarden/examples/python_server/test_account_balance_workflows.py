"""
AccountNode 잔고 확장 통합 테스트

실제 LS증권 API를 호출하여 확장된 balance 필드를 검증합니다.

테스트 시나리오:
1. 해외주식 AccountNode - COSOQ02701 확장 필드 확인
2. 해외선물 AccountNode - CIDBQ05300 확장 필드 확인
3. 해외주식 balance → IfNode 분기 (orderable_amount 기반 조건)

실행 방법:
    cd src/programgarden
    poetry run python examples/python_server/test_account_balance_workflows.py

필수 환경변수 (.env):
    APPKEY=...
    APPSECRET=...
    FUTURES_APPKEY=...       (선물 테스트용, 없으면 스킵)
    FUTURES_APPSECRET=...    (선물 테스트용, 없으면 스킵)
"""

import asyncio
import sys
import os
from pathlib import Path

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../core"))

# .env 로드
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    print(f"[env] .env loaded from {env_path}")

from programgarden import ProgramGarden
from programgarden_core.bases.listener import ExecutionListener


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    def ok(self, name: str, detail: str = ""):
        self.passed += 1
        print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name} - {reason}")

    def skip(self, name: str, reason: str):
        self.skipped += 1
        print(f"  [SKIP] {name} - {reason}")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"결과: {self.passed}/{total} passed, {self.failed} failed, {self.skipped} skipped")
        if self.errors:
            print(f"\n실패 목록:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


class NodeTracker(ExecutionListener):
    """노드 실행 추적 리스너"""

    def __init__(self):
        self.executed_nodes = []
        self.node_outputs = {}
        self.logs = []

    async def on_node_state_change(self, event) -> None:
        if event.state.value == "running" or str(event.state) == "running":
            self.executed_nodes.append(event.node_id)
        if event.outputs and (event.state.value == "completed" or str(event.state) == "completed"):
            self.node_outputs[event.node_id] = event.outputs

    async def on_log(self, event) -> None:
        self.logs.append({"level": event.level, "message": event.message, "node_id": getattr(event, "node_id", "")})


# ============================================================
# 테스트 1: 해외주식 AccountNode - 확장 balance 필드
# ============================================================

async def test_1_stock_balance_fields(pg: ProgramGarden, result: TestResult):
    """해외주식 balance에 orderable_amount/foreign_cash/exchange_rate 포함 확인"""
    print("\n[Test 1] 해외주식 AccountNode - 확장 balance 필드")
    print("-" * 50)

    appkey = os.environ.get("APPKEY", "")
    appsecret = os.environ.get("APPSECRET", "")

    if not appkey or not appsecret:
        result.skip("해외주식 balance", "APPKEY/APPSECRET 환경변수 없음")
        return

    workflow = {
        "id": "test-stock-balance",
        "name": "해외주식 잔고 확장 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "stock-cred"},
            {"id": "account", "type": "OverseasStockAccountNode"},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
        ],
        "credentials": [
            {
                "credential_id": "stock-cred",
                "type": "broker_ls_overseas_stock",
                "data": [
                    {"key": "appkey", "value": appkey},
                    {"key": "appsecret", "value": appsecret},
                ],
            }
        ],
    }

    tracker = NodeTracker()
    job = await pg.run_async(workflow, listeners=[tracker])
    await asyncio.wait_for(job._task, timeout=30)

    outputs = job.context.get_all_outputs("account")
    if not outputs:
        result.fail("account 출력", "outputs가 None")
        return

    balance = outputs.get("balance", {})
    print(f"  balance 전체 키: {list(balance.keys())}")
    print(f"  balance 값: {balance}")

    # 기존 필드 확인
    for field in ["total_pnl_rate", "cash_krw", "stock_eval_krw", "total_eval_krw", "total_pnl_krw"]:
        if field in balance:
            result.ok(f"기존 필드 '{field}'", f"값: {balance[field]}")
        else:
            result.fail(f"기존 필드 '{field}'", "누락")

    # 신규 필드 확인 (COSOQ02701)
    for field in ["orderable_amount", "foreign_cash", "exchange_rate"]:
        if field in balance:
            result.ok(f"신규 필드 '{field}'", f"값: {balance[field]}")
        else:
            result.fail(f"신규 필드 '{field}'", "누락 (COSOQ02701 실패?)")

    # 포지션 확인
    positions = outputs.get("positions", [])
    print(f"  보유종목 수: {len(positions)}")
    for p in positions[:3]:
        print(f"    - {p.get('symbol')} @ {p.get('exchange')}: {p.get('quantity')}주, 수익률 {p.get('pnl_rate')}%")


# ============================================================
# 테스트 2: 해외선물 AccountNode - 증거금/마진콜 필드
# ============================================================

async def test_2_futures_balance_fields(pg: ProgramGarden, result: TestResult):
    """해외선물 balance에 margin/maintenance_margin/margin_call_rate 포함 확인"""
    print("\n[Test 2] 해외선물 AccountNode - 증거금/마진콜 필드")
    print("-" * 50)

    appkey = os.environ.get("FUTURES_APPKEY", "")
    appsecret = os.environ.get("FUTURES_APPSECRET", "")

    if not appkey or not appsecret:
        result.skip("해외선물 balance", "FUTURES_APPKEY/FUTURES_APPSECRET 환경변수 없음")
        return

    workflow = {
        "id": "test-futures-balance",
        "name": "해외선물 잔고 확장 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "futures-cred"},
            {"id": "account", "type": "OverseasFuturesAccountNode"},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
        ],
        "credentials": [
            {
                "credential_id": "futures-cred",
                "type": "broker_ls_overseas_futures",
                "data": [
                    {"key": "appkey", "value": appkey},
                    {"key": "appsecret", "value": appsecret},
                    {"key": "paper_trading", "value": "true"},
                ],
            }
        ],
    }

    tracker = NodeTracker()
    job = await pg.run_async(workflow, listeners=[tracker])
    await asyncio.wait_for(job._task, timeout=30)

    outputs = job.context.get_all_outputs("account")
    if not outputs:
        result.fail("account 출력", "outputs가 None")
        return

    balance = outputs.get("balance", {})
    print(f"  balance 전체 키: {list(balance.keys())}")
    print(f"  balance 값: {balance}")

    # 기존 필드 확인 (하위 호환)
    for field in ["deposit", "orderable_amount", "total_orderable"]:
        if field in balance:
            result.ok(f"기존 필드 '{field}'", f"값: {balance[field]}")
        else:
            result.fail(f"기존 필드 '{field}'", "누락")

    # by_currency 구조 확인
    if "by_currency" in balance and isinstance(balance["by_currency"], dict):
        currencies = list(balance["by_currency"].keys())
        result.ok("by_currency 구조", f"통화: {currencies}")
        # 각 통화의 하위 키 확인
        for cur, data in balance["by_currency"].items():
            for key in ["deposit", "orderable_amount", "withdrawable_amount", "eval_pnl"]:
                if key not in data:
                    result.fail(f"by_currency.{cur}.{key}", "누락")
    else:
        result.fail("by_currency 구조", f"없거나 dict 아님: {type(balance.get('by_currency'))}")

    # 신규 필드 확인 (CIDBQ05300 block3)
    for field in ["margin", "maintenance_margin", "margin_call_rate", "total_eval", "settlement_pnl"]:
        if field in balance:
            result.ok(f"신규 필드 '{field}'", f"값: {balance[field]}")
        else:
            result.fail(f"신규 필드 '{field}'", "누락 (CIDBQ05300 block3 없음?)")

    # 포지션 확인
    positions = outputs.get("positions", [])
    print(f"  보유 포지션 수: {len(positions)}")
    for p in positions[:3]:
        print(f"    - {p.get('symbol')}: {p.get('direction')} {p.get('quantity')}계약, "
              f"진입 ${p.get('entry_price')}, 현재 ${p.get('current_price')}")


# ============================================================
# 테스트 3: balance → IfNode 분기 (orderable_amount 기반)
# ============================================================

async def test_3_balance_if_branch(pg: ProgramGarden, result: TestResult):
    """balance.orderable_amount 기반 IfNode 분기 테스트"""
    print("\n[Test 3] balance → IfNode 분기 (orderable_amount 기반)")
    print("-" * 50)

    appkey = os.environ.get("APPKEY", "")
    appsecret = os.environ.get("APPSECRET", "")

    if not appkey or not appsecret:
        result.skip("balance→IfNode 분기", "APPKEY/APPSECRET 환경변수 없음")
        return

    workflow = {
        "id": "test-balance-if",
        "name": "잔고 기반 조건 분기 테스트",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "stock-cred"},
            {"id": "account", "type": "OverseasStockAccountNode"},
            {
                "id": "check-balance",
                "type": "IfNode",
                "left": "{{ nodes.account.balance.orderable_amount }}",
                "operator": ">=",
                "right": 0,
            },
            {"id": "can-order", "type": "FieldMappingNode", "mappings": {}},
            {"id": "no-funds", "type": "FieldMappingNode", "mappings": {}},
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "account"},
            {"from": "account", "to": "check-balance"},
            {"from": "check-balance", "to": "can-order", "from_port": "true"},
            {"from": "check-balance", "to": "no-funds", "from_port": "false"},
        ],
        "credentials": [
            {
                "credential_id": "stock-cred",
                "type": "broker_ls_overseas_stock",
                "data": [
                    {"key": "appkey", "value": appkey},
                    {"key": "appsecret", "value": appsecret},
                ],
            }
        ],
    }

    tracker = NodeTracker()
    job = await pg.run_async(workflow, listeners=[tracker])
    await asyncio.wait_for(job._task, timeout=30)

    # AccountNode 출력 확인
    account_outputs = job.context.get_all_outputs("account")
    if account_outputs:
        balance = account_outputs.get("balance", {})
        orderable = balance.get("orderable_amount", "N/A")
        print(f"  orderable_amount: {orderable}")
    else:
        result.fail("account 출력", "없음")
        return

    # IfNode 결과 확인
    if_outputs = job.context.get_all_outputs("check-balance")
    if if_outputs:
        if_result = if_outputs.get("result")
        print(f"  IfNode result: {if_result}")

        if if_result is True:
            result.ok("IfNode 판정", f"orderable_amount({orderable}) >= 0 → true")
            if "can-order" in tracker.executed_nodes:
                result.ok("true 분기 (can-order) 실행됨")
            else:
                result.fail("true 분기", "실행되지 않음")
            if "no-funds" not in tracker.executed_nodes:
                result.ok("false 분기 (no-funds) 스킵됨")
            else:
                result.fail("false 분기", "스킵되지 않음")
        elif if_result is False:
            result.ok("IfNode 판정", f"orderable_amount({orderable}) < 0 → false")
            if "no-funds" in tracker.executed_nodes:
                result.ok("false 분기 (no-funds) 실행됨")
            else:
                result.fail("false 분기", "실행되지 않음")
        else:
            result.fail("IfNode result", f"예상치 못한 값: {if_result}")
    else:
        result.fail("IfNode 출력", "없음")


# ============================================================
# 메인 실행
# ============================================================

async def main():
    print("=" * 60)
    print("  AccountNode 잔고 확장 통합 테스트")
    print("  (LS증권 API 실제 호출)")
    print("=" * 60)

    pg = ProgramGarden()
    result = TestResult()

    tests = [
        test_1_stock_balance_fields,
        test_2_futures_balance_fields,
        test_3_balance_if_branch,
    ]

    for test_fn in tests:
        try:
            await test_fn(pg, result)
        except Exception as e:
            result.fail(test_fn.__name__, f"Exception: {e}")
            import traceback
            traceback.print_exc()

    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
