"""HKEX 예제 81 L3 시세 read 트리거 (host-only).

목적
----
workflow 81 (HKEX 다종목 RSI+Bollinger) 에서 NewOrderNode / TelegramNode 를
프로그램적으로 제거하여 **read-only** 로 실행한다. 실 LS 모의 appkey 로
historical / market_data / account / condition / logic / symbol_filter / sizing
체인이 정상 동작하는지 확인하는 것이 목적.

주문은 절대 발사하지 않는다 (NewOrderNode 노드 자체 제거).
ScheduleNode 의 cron 첫 fire 직후 force_stop.

실행
----
호스트에서 (실 .env 가 있는 환경):
    cd src/programgarden
    poetry run python examples/programmer_example/test_hkex_81_l3_read.py

필요 .env 키
------------
- APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE  (LS 해외선물 모의)

L4 (실 모의주문) 는 별도 스크립트 / 사용자 직접 트리거. 이 파일은 read-only.
"""

from __future__ import annotations

import asyncio
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


WORKFLOW_PATH = (
    project_root
    / "src"
    / "programgarden"
    / "examples"
    / "workflows"
    / "81-hkex-multi-symbol-rsi-bollinger.json"
)

STRIP_NODE_IDS = {"buy_order", "telegram"}
TIMEOUT_SEC = 90


class L3Listener(BaseExecutionListener):
    """L3 검증용 — 노드 완료 + 경고/에러 로그만 출력."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    async def on_node_state_change(self, event):
        state = event.state.value
        if state in ("completed", "failed"):
            print(f"  [{event.node_id}] {state}")

    async def on_log(self, event):
        if event.level == "error":
            self.errors.append(event.message)
            print(f"  ❌ [error] {event.message}")
        elif event.level == "warning":
            self.warnings.append(event.message)
            print(f"  ⚠️  [warn ] {event.message}")

    async def on_notification(self, event):
        print(f"  🔔 {event.kind}: {event.message}")


def _strip_order_telegram(workflow: dict) -> dict:
    """NewOrder + Telegram 노드 / 엣지 / credential 을 제거하여 read-only 화."""
    workflow["nodes"] = [n for n in workflow["nodes"] if n["id"] not in STRIP_NODE_IDS]
    workflow["edges"] = [
        e
        for e in workflow["edges"]
        if e["from"] not in STRIP_NODE_IDS and e["to"] not in STRIP_NODE_IDS
    ]
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
            new_creds.append(
                {
                    "credential_id": cred["credential_id"],
                    "type": "broker_ls_overseas_futures",
                    "data": [
                        {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                        {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
                    ],
                }
            )
        else:
            new_creds.append(cred)
    workflow["credentials"] = new_creds
    return workflow


def _summarize_outputs(job) -> None:
    """주요 노드 출력을 사람이 읽기 쉽게 dump."""
    print("\n" + "=" * 60)
    print("📤 노드 출력 요약")
    print("=" * 60)

    targets = [
        ("watchlist", "symbols"),
        ("account", "positions"),
        ("account", "balance"),
        ("historical", "value"),
        ("rsi_condition", "value"),
        ("bollinger_condition", "value"),
        ("logic", "matches"),
        ("filter_buy", "passed_symbols"),
        ("market_data", "value"),
        ("sizing", "order"),
    ]

    for node_id, port in targets:
        outputs = job.context.get_all_outputs(node_id) if hasattr(job.context, "get_all_outputs") else None
        if not outputs:
            print(f"  {node_id}.{port}: (no outputs)")
            continue
        value = outputs.get(port, "(missing port)")
        if isinstance(value, (list, dict)):
            text = json.dumps(value, ensure_ascii=False, default=str)
            if len(text) > 400:
                text = text[:400] + " …(truncated)"
            print(f"  {node_id}.{port}: {text}")
        else:
            print(f"  {node_id}.{port}: {value!r}")


async def main() -> int:
    with open(WORKFLOW_PATH) as f:
        workflow = json.load(f)

    print("🟢 HKEX 81 L3 read-only 트리거")
    print(f"  원본: {WORKFLOW_PATH.name}")
    print(f"  read-only 변환: NewOrder+Telegram 제거")

    workflow = _strip_order_telegram(workflow)
    print(f"  변환 후 nodes={len(workflow['nodes'])} edges={len(workflow['edges'])}")
    assert all(n["id"] not in STRIP_NODE_IDS for n in workflow["nodes"]), "strip 실패"

    workflow = _inject_broker_cred(workflow)
    if workflow is None:
        return 2

    pg = ProgramGarden()
    listener = L3Listener()
    job = await pg.run_async(workflow, listeners=[listener])

    try:
        await asyncio.wait_for(job._task, timeout=TIMEOUT_SEC)
        print(f"\n  Status (natural exit): {job.status}")
    except asyncio.TimeoutError:
        print(f"\n  ⏰ {TIMEOUT_SEC}s 경과 → ScheduleNode force stop")
        await job.stop()
        try:
            await asyncio.wait_for(job._task, timeout=5)
        except asyncio.TimeoutError:
            pass
        print(f"  Status (after stop): {job.status}")

    _summarize_outputs(job)

    print("\n" + "=" * 60)
    print(f"❗ errors  : {len(listener.errors)}")
    print(f"⚠️  warnings: {len(listener.warnings)}")
    print("=" * 60)

    # cancelled / stopped / completed 모두 정상으로 간주
    ok = job.status in ("completed", "cancelled", "stopped") and not listener.errors
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
