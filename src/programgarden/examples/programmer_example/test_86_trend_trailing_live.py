"""86-trend-trailing-live 워크플로우 라이브 러너 (host-only).

목적
----
NASDAQ 추세 상위 최대 2종목 매수 + 고점 대비 -5% 고정 트레일링스탑 워크플로우
(`86-trend-trailing-live.json`) 를 실 LS 해외주식 키로 실행한다.

⚠️ 해외주식은 LS 모의투자를 지원하지 않는다 — `--live` 는 **실계좌 주문**이다.
프로젝트 정책상 주문 발사는 사용자가 직접 확인한다: `--confirm` 플래그 또는
`L4_CONFIRM=1` 환경변수 없이는 --live 가 실행되지 않는다.

모드
----
    --validate (기본) : validate + 실로그인 dry_run 1사이클
                        (주문/실시간/텔레그램은 skip — 계좌/시세 조회만 발생)
    --read            : 주문·텔레그램·시간게이트 노드를 strip 한 read-only 라이브.
                        스크리너→추세필터→사이징 체인이 실데이터로 흐르는지 검증.
    --live            : 실주문 라이브. --confirm 또는 L4_CONFIRM=1 필수.

옵션
----
    --cycles N   : N 사이클 완료 후 정지 (기본 3)
    --minutes M  : M 분 경과 후 정지 (기본 30)

실행
----
    cd src/programgarden
    poetry run python examples/programmer_example/test_86_trend_trailing_live.py            # validate+dry_run
    poetry run python examples/programmer_example/test_86_trend_trailing_live.py --read
    poetry run python examples/programmer_example/test_86_trend_trailing_live.py --live --confirm

필요 .env 키
------------
- APPKEY / APPSECRET            (LS 해외주식 실전)
- TELEGRAM-TOKEN / TELEGRAM-CHAT-ID  (선택 — 없으면 텔레그램 노드 자동 strip)

HWM 영속성
----------
트레일링스탑의 고점(HWM)은 `{storage_dir}/86-trend-trailing-live_workflow.db`
(risk_high_water_mark 테이블)에 30초마다 flush 되어 재시작 간 유지된다.
storage_dir 는 이 스크립트 디렉토리의 `.runtime_data_86/` 으로 고정한다.
"""

from __future__ import annotations

import argparse
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

from programgarden import WorkflowExecutor  # noqa: E402
from programgarden_core.bases.listener import BaseExecutionListener  # noqa: E402

WORKFLOWS_DIR = (
    project_root / "src" / "programgarden" / "examples" / "workflows"
)
DEFAULT_WORKFLOW = "86-trend-trailing-live.json"
# main()에서 --workflow 인자로 재지정 가능 (변종 86b-penny-live 등)
WORKFLOW_PATH = WORKFLOWS_DIR / DEFAULT_WORKFLOW
STORAGE_DIR = Path(__file__).parent / ".runtime_data_86"

TELEGRAM_NODE_IDS = {"tg_buy_a", "tg_buy_b", "tg_sell"}
ORDER_NODE_IDS = {"order_a", "order_b", "sell_order"}


class LiveListener(BaseExecutionListener):
    def __init__(self) -> None:
        super().__init__()
        self.cycles = 0
        self.errors: list[str] = []
        self.orders: list[dict] = []

    async def on_node_state_change(self, event):
        state = event.state.value
        if state == "failed":
            print(f"  ❌ [{event.node_id}] failed: {event.error}")
        elif state == "completed":
            outputs = event.outputs or {}
            if event.node_id in ORDER_NODE_IDS:
                result = outputs.get("result")
                if result:
                    self.orders.append({"node": event.node_id, **result} if isinstance(result, dict) else {"node": event.node_id, "result": result})
                    print(f"  🧾 [{event.node_id}] order result: {json.dumps(result, ensure_ascii=False, default=str)}")
            elif event.node_id in ("top2", "trailing", "cash_guard", "if_slot1", "if_has_pos"):
                compact = json.dumps(outputs, ensure_ascii=False, default=str)
                print(f"  ✔ [{event.node_id}] {compact[:300]}")

    async def on_log(self, event):
        if event.level == "error":
            self.errors.append(f"{event.node_id}: {event.message}")
            print(f"  [error] {event.node_id}: {event.message}")
        elif event.level == "warning":
            print(f"  [warn ] {event.node_id}: {event.message}")

    async def on_display_data(self, event):
        body = json.dumps(event.data, ensure_ascii=False, default=str)
        print(f"  📊 [{event.node_id}] {event.title}: {body[:400]}")

    async def on_job_state_change(self, event):
        print(f"  [job] -> {event.state}")
        if event.state == "cycle_completed":
            self.cycles += 1
            print(f"  ── cycle {self.cycles} done ──")

    async def on_notification(self, event):
        print(f"  🔔 {getattr(event, 'title', '')}: {getattr(event, 'message', '')}")


def load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def inject_credentials(workflow: dict, *, allow_missing_telegram: bool = True) -> dict:
    appkey = os.environ.get("APPKEY")
    appsecret = os.environ.get("APPSECRET")
    if not (appkey and appsecret):
        raise SystemExit("APPKEY / APPSECRET 미설정 — .env (LS 해외주식 실전 키) 확인")

    tg_token = os.environ.get("TELEGRAM-TOKEN")
    tg_chat = os.environ.get("TELEGRAM-CHAT-ID")
    has_telegram = bool(tg_token and tg_chat)
    if not has_telegram and not allow_missing_telegram:
        raise SystemExit("TELEGRAM-TOKEN / TELEGRAM-CHAT-ID 미설정")

    for cred in workflow.get("credentials", []):
        if cred.get("type") == "broker_ls_overseas_stock":
            cred["data"] = [
                {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
            ]
        elif cred.get("type") == "telegram" and has_telegram:
            cred["data"] = [
                {"key": "bot_token", "value": tg_token, "type": "password", "label": "Bot Token"},
                {"key": "chat_id", "value": tg_chat, "type": "text", "label": "Chat ID"},
            ]

    if not has_telegram:
        print("⚠️ 텔레그램 키 없음 → 텔레그램 노드 strip")
        strip_nodes(workflow, TELEGRAM_NODE_IDS)
    return workflow


def strip_nodes(workflow: dict, node_ids: set) -> None:
    """노드 제거 + 선행→후행 재배선 (단순 게이트 노드 strip 용)."""
    present = {n["id"] for n in workflow["nodes"]} & set(node_ids)
    if not present:
        return
    preds: dict = {}
    succs: dict = {}
    for e in workflow["edges"]:
        if e["to"] in present:
            preds.setdefault(e["to"], []).append(e["from"])
        if e["from"] in present:
            succs.setdefault(e["from"], []).append(e["to"])
    workflow["nodes"] = [n for n in workflow["nodes"] if n["id"] not in present]
    workflow["edges"] = [
        e for e in workflow["edges"]
        if e["from"] not in present and e["to"] not in present
    ]
    for nid in present:
        for p in preds.get(nid, []):
            for s in succs.get(nid, []):
                if p not in present and s not in present:
                    workflow["edges"].append({"from": p, "to": s})
    # 제거된 credential 참조 정리는 불필요 (credentials 는 노드가 참조할 때만 사용)


def validate_or_die(workflow: dict) -> None:
    result = WorkflowExecutor().validate(workflow)
    print(f"validate: is_valid={result.is_valid}")
    if not result.is_valid:
        for e in result.errors:
            print("  ERROR:", e)
        raise SystemExit(2)


async def run_job(workflow: dict, *, dry_run: bool, max_cycles: int, max_minutes: float) -> int:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    executor = WorkflowExecutor()
    listener = LiveListener()
    job = await executor.execute(
        workflow,
        context_params={"dry_run": True} if dry_run else None,
        listeners=[listener],
        storage_dir=str(STORAGE_DIR),
    )

    loop = asyncio.get_event_loop()
    deadline = loop.time() + max_minutes * 60
    while not job._task.done():
        if listener.cycles >= max_cycles:
            print(f"\n⏹ {max_cycles} 사이클 완료 — 정지")
            await job.stop()
            break
        if loop.time() > deadline:
            print(f"\n⏹ {max_minutes}분 경과 — 정지")
            await job.stop()
            break
        await asyncio.sleep(1)
    if not job._task.done():
        try:
            await asyncio.wait_for(job._task, timeout=15)
        except asyncio.TimeoutError:
            pass

    state = job.get_state()
    print(f"\n=== 최종 상태: {state['status']} | stats={state['stats']} ===")
    for nid, info in state["nodes"].items():
        line = f"  {nid:18s} {info['state']}"
        if info.get("error"):
            line += f"  err={info['error']}"
        print(line)

    print("\n=== 주요 출력 ===")
    for nid in ("account", "screener1", "top2", "market_a", "sizing_a", "market_b", "sizing_b", "order_a", "order_b", "trailing", "sell_pick"):
        outputs = job.context.get_all_outputs(nid) or {}
        for port, value in outputs.items():
            if port.startswith("_"):
                continue
            text = json.dumps(value, ensure_ascii=False, default=str)
            print(f"  {nid}.{port}: {text[:400]}")
    if listener.orders:
        print("\n=== 주문 내역 ===")
        for o in listener.orders:
            print(" ", json.dumps(o, ensure_ascii=False, default=str))

    ok = state["status"] in ("completed", "stopped") and not listener.errors
    return 0 if ok else 1


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true", help="validate + 실로그인 dry_run (기본)")
    mode.add_argument("--read", action="store_true", help="read-only 라이브 (주문/텔레그램/시간게이트 strip)")
    mode.add_argument("--live", action="store_true", help="실주문 라이브 (--confirm 필수)")
    parser.add_argument("--confirm", action="store_true", help="실주문 발사 확인")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--minutes", type=float, default=30.0)
    parser.add_argument(
        "--workflow",
        type=str,
        default=DEFAULT_WORKFLOW,
        help="실행할 워크플로우 JSON 파일명 (기본: 86-trend-trailing-live.json, 변종: 86b-penny-live.json)",
    )
    args = parser.parse_args()

    # --workflow 로 워크플로우/HWM 저장경로 재지정 (변종별 HWM DB 분리)
    global WORKFLOW_PATH, STORAGE_DIR
    WORKFLOW_PATH = WORKFLOWS_DIR / args.workflow
    if not WORKFLOW_PATH.exists():
        print(f"⛔ 워크플로우 파일이 없습니다: {WORKFLOW_PATH}")
        return 4
    STORAGE_DIR = Path(__file__).parent / f".runtime_data_{Path(args.workflow).stem}"
    print(f"📄 워크플로우: {args.workflow}  | HWM 저장: {STORAGE_DIR.name}")

    workflow = load_workflow()
    inject_credentials(workflow)

    if args.live:
        if not (args.confirm or os.environ.get("L4_CONFIRM") == "1"):
            print("⛔ --live 는 실계좌 주문입니다. --confirm 또는 L4_CONFIRM=1 로만 실행 가능.")
            return 3
        validate_or_die(workflow)
        print("🚀 LIVE 실행 (실계좌 주문 활성)")
        return await run_job(workflow, dry_run=False, max_cycles=args.cycles, max_minutes=args.minutes)

    if args.read:
        strip_nodes(workflow, ORDER_NODE_IDS | TELEGRAM_NODE_IDS | {"hours"})
        validate_or_die(workflow)
        print("👁 READ-ONLY 라이브 (주문/텔레그램/시간게이트 제거)")
        return await run_job(workflow, dry_run=False, max_cycles=1, max_minutes=args.minutes)

    validate_or_die(workflow)
    print("🧪 VALIDATE + dry_run (주문/텔레그램 skip)")
    return await run_job(workflow, dry_run=True, max_cycles=1, max_minutes=5.0)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
