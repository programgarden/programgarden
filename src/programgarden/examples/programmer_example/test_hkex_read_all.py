"""HKEX 예제 81/83/84/85 read-only 분석 파이프라인 라이브 트리거 (host-only).

목적
----
주문(NewOrder)·메시징(Telegram)·AI(LLM/Agent) 노드를 프로그램적으로 제거하여
**read-only 분석 체인만** 실 LS 모의(paper) appkey 로 실행한다. 시세/지표/로직/
백테스트/스크리너 노드가 실 데이터로 silent failure 없이 흐르는지 확인하는 것이
목적이다. 주문은 절대 발사하지 않는다 (order 노드 자체 제거).

L3 (`test_hkex_81_l3_read.py`) 의 일반화 버전 — id 기반 strip 을 워크플로우별로
지정하고, 완료된 모든 노드의 출력을 자동 dump 한다.

대상
----
- 81: buy_order/telegram 제거 → historical→RSI→Bollinger→Logic→account→filter→sizing
- 84: telegram_morning 제거 → historical→RSI/Boll→Backtest×2→Benchmark→summary
- 85: buy_order/telegram_entry 제거 → watchlist→exclusion→historical→ATR→filter→sizing
- 83: llm/risk_agent/report_* 제거 → historical/account 데이터 피드만 (AI 는 키 필요, 별도)

82 (realtime stop-loss) 는 websocket 틱 의존 + 주문 구동형이라 주말 장마감엔
read-only 로 의미 있는 검증이 불가 → 제외.

실행
----
    cd src/programgarden
    poetry run python examples/programmer_example/test_hkex_read_all.py
    poetry run python examples/programmer_example/test_hkex_read_all.py --only 84

필요 .env 키
------------
- APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE  (LS 해외선물 모의)
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import sys
from pathlib import Path


project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))


env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


from programgarden import ProgramGarden  # noqa: E402
from programgarden_core.bases.listener import BaseExecutionListener  # noqa: E402


WORKFLOW_DIR = project_root / "src" / "programgarden" / "examples" / "workflows"
TIMEOUT_SEC = 90

# 워크플로우별 read-only strip 대상 (node id)
#
# trading_hours (TradingHoursFilterNode) 는 캘린더 게이트일 뿐 read/분석 체인의
# 일부가 아니다. 장 마감(주말/공휴일)에는 이 게이트가 job 을 cancel 시켜
# historical→지표→로직 체인이 아예 실행되지 않으므로, order/messaging/AI 와
# 동일한 논리로 strip 하여 **언제든** read 경로를 검증할 수 있게 한다.
TARGETS = {
    "81": {"glob": "81-*.json", "strip": {"buy_order", "telegram", "trading_hours"}},
    "84": {"glob": "84-*.json", "strip": {"telegram_morning"}},
    "85": {"glob": "85-*.json", "strip": {"buy_order", "telegram_entry", "trading_hours"}},
    "83": {"glob": "83-*.json",
           "strip": {"llm", "risk_agent", "report_table", "report_telegram"}},
}


class ReadListener(BaseExecutionListener):
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.completed: list[str] = []
        self.failed: list[str] = []

    async def on_node_state_change(self, event):
        state = event.state.value
        if state == "completed":
            self.completed.append(event.node_id)
            print(f"  ✅ [{event.node_id}] completed")
        elif state == "failed":
            self.failed.append(event.node_id)
            print(f"  ❌ [{event.node_id}] FAILED")

    async def on_log(self, event):
        if event.level == "error":
            self.errors.append(event.message)
            print(f"  ❌ [error] {event.message}")
        elif event.level == "warning":
            self.warnings.append(event.message)
            print(f"  ⚠️  [warn ] {event.message}")

    async def on_notification(self, event):
        # NotificationEvent fields: job_id/category/severity/title/message/node_id/node_type/data/timestamp
        cat = getattr(event.category, "value", event.category)
        sev = getattr(event.severity, "value", event.severity)
        print(f"  🔔 [{cat}/{sev}] {event.title}: {event.message}")


def _strip_ids(workflow: dict, strip: set) -> dict:
    workflow["nodes"] = [n for n in workflow["nodes"] if n["id"] not in strip]
    workflow["edges"] = [
        e for e in workflow["edges"]
        if e["from"].split(".")[0] not in strip and e["to"].split(".")[0] not in strip
    ]
    # telegram credential 등 더 이상 참조되지 않는 cred 는 그대로 둬도 무방 (검증만 통과하면 됨)
    workflow["credentials"] = [
        c for c in workflow.get("credentials", []) if c.get("type") != "telegram"
    ]
    return workflow


def _inject_broker_cred(workflow: dict) -> dict | None:
    appkey = os.environ.get("APPKEY_FUTURE_FAKE")
    appsecret = os.environ.get("APPSECRET_FUTURE_FAKE")
    if not (appkey and appsecret):
        print("❌ .env 에 APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE 가 없습니다.")
        return None
    new_creds = []
    for cred in workflow.get("credentials", []):
        if cred.get("type") == "broker_ls_overseas_futures":
            new_creds.append({
                "credential_id": cred["credential_id"],
                "type": "broker_ls_overseas_futures",
                "data": [
                    {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                    {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
                ],
            })
        else:
            new_creds.append(cred)
    workflow["credentials"] = new_creds
    return workflow


def _dump_outputs(job, node_ids: list[str]) -> None:
    print("\n  --- 노드 출력 ---")
    if not hasattr(job.context, "get_all_outputs"):
        print("  (context.get_all_outputs 미지원)")
        return
    for nid in node_ids:
        outputs = job.context.get_all_outputs(nid)
        if not outputs:
            continue
        for port, value in outputs.items():
            if port.startswith("_"):
                continue
            text = json.dumps(value, ensure_ascii=False, default=str)
            if len(text) > 300:
                text = text[:300] + " …"
            print(f"  {nid}.{port}: {text}")


async def run_one(key: str) -> bool:
    spec = TARGETS[key]
    matches = sorted(glob.glob(str(WORKFLOW_DIR / spec["glob"])))
    if not matches:
        print(f"❌ {key}: 워크플로우 파일 없음 ({spec['glob']})")
        return False
    path = Path(matches[0])

    print("\n" + "=" * 64)
    print(f"🟢 [{key}] {path.name}  (read-only)")
    print(f"   strip: {sorted(spec['strip'])}")
    print("=" * 64)

    with open(path) as f:
        workflow = json.load(f)
    workflow = _strip_ids(workflow, spec["strip"])
    workflow = _inject_broker_cred(workflow)
    if workflow is None:
        return False

    pg = ProgramGarden()
    listener = ReadListener()
    job = await pg.run_async(workflow, listeners=[listener])

    try:
        await asyncio.wait_for(job._task, timeout=TIMEOUT_SEC)
        print(f"\n  Status (natural exit): {job.status}")
    except asyncio.TimeoutError:
        print(f"\n  ⏰ {TIMEOUT_SEC}s 경과 → force stop")
        await job.stop()
        try:
            await asyncio.wait_for(job._task, timeout=5)
        except asyncio.TimeoutError:
            pass
        print(f"  Status (after stop): {job.status}")

    _dump_outputs(job, listener.completed)

    print(f"\n  completed={len(listener.completed)} failed={len(listener.failed)} "
          f"errors={len(listener.errors)} warnings={len(listener.warnings)}")
    ok = job.status in ("completed", "cancelled", "stopped") and not listener.errors and not listener.failed
    print(f"  → {'✅ PASS' if ok else '⚠️  CHECK'}")
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser(description="HKEX read-only 분석 파이프라인 라이브 트리거")
    parser.add_argument("--only", choices=sorted(TARGETS), default=None,
                        help="특정 예제만 실행 (기본: 81,84,85,83 전부)")
    args = parser.parse_args()

    keys = [args.only] if args.only else ["81", "84", "85", "83"]
    print("🟢 HKEX read-only 분석 파이프라인 라이브 검증")
    print(f"   대상: {keys}  (주문/메시징/AI 노드 제거)")

    results = {}
    for key in keys:
        try:
            results[key] = await run_one(key)
        except Exception as exc:  # noqa: BLE001
            print(f"  💥 [{key}] 예외: {exc!r}")
            results[key] = False

    print("\n" + "=" * 64)
    print("📊 종합")
    for key, ok in results.items():
        print(f"   {key}: {'✅ PASS' if ok else '⚠️  CHECK'}")
    print("=" * 64)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
