"""왕초보 + 중급 텔레그램 워크플로우 (68~77) 실전 실행 테스트.

`.env` 의 credential 을 workflow JSON 에 주입하여 실행합니다:
    - broker_ls_overseas_stock: APPKEY / APPSECRET (실전계좌 조회만)
    - broker_ls_overseas_futures: APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE (모의)
    - telegram: TELEGRAM-TOKEN / TELEGRAM-CHAT-ID

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_beginner_telegram.py

주의:
    - 실제 텔레그램 메시지가 발송됩니다.
    - 68/69/70/72 는 실전 해외주식 조회만 (주문 없음).
    - 71 은 ScheduleNode 포함 → 20초 후 강제 stop.
    - 73~77 은 해외선물 모의계좌로 실제 주문 포함 (안전). Schedule 포함 워크플로우는 force_stop.
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


# .env 로드 (TELEGRAM-TOKEN 같은 하이픈 키도 포함)
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


WORKFLOWS_DIR = project_root / "src" / "programgarden" / "examples" / "workflows"

# 타임아웃 (초)
TIMEOUT_SHORT = 30   # 단발 실행 (68, 69, 70, 72)
TIMEOUT_SCHEDULE = 20  # ScheduleNode 포함 워크플로우 (71) 강제 stop


class TestListener(BaseExecutionListener):
    """간단 리스너 — 노드 상태 및 텔레그램 발송 로그."""

    async def on_node_state_change(self, event):
        print(f"  [{event.node_id}] {event.state.value}")

    async def on_log(self, event):
        if event.level in ("warning", "error"):
            print(f"  📝 [{event.level}] {event.message}")


def _inject_credentials(workflow: dict) -> dict | None:
    """워크플로우 JSON 의 credential 들을 .env 값으로 치환."""
    appkey = os.environ.get("APPKEY")
    appsecret = os.environ.get("APPSECRET")
    fut_appkey = os.environ.get("APPKEY_FUTURE_FAKE")
    fut_appsecret = os.environ.get("APPSECRET_FUTURE_FAKE")
    tg_token = os.environ.get("TELEGRAM-TOKEN")
    tg_chat = os.environ.get("TELEGRAM-CHAT-ID")

    new_creds = []
    for cred in workflow.get("credentials", []):
        cred_id = cred.get("credential_id", "")
        cred_type = cred.get("type", "")

        if cred_type == "broker_ls_overseas_stock":
            if not (appkey and appsecret):
                print("  ⚠️ APPKEY/APPSECRET 없음 → SKIP")
                return None
            new_creds.append({
                "credential_id": cred_id,
                "type": "broker_ls_overseas_stock",
                "data": [
                    {"key": "appkey", "value": appkey, "type": "password", "label": "App Key"},
                    {"key": "appsecret", "value": appsecret, "type": "password", "label": "App Secret"},
                ],
            })

        elif cred_type == "broker_ls_overseas_futures":
            if not (fut_appkey and fut_appsecret):
                print("  ⚠️ APPKEY_FUTURE_FAKE/APPSECRET_FUTURE_FAKE 없음 → SKIP")
                return None
            new_creds.append({
                "credential_id": cred_id,
                "type": "broker_ls_overseas_futures",
                "data": [
                    {"key": "appkey", "value": fut_appkey, "type": "password", "label": "App Key"},
                    {"key": "appsecret", "value": fut_appsecret, "type": "password", "label": "App Secret"},
                ],
            })

        elif cred_type == "telegram":
            if not (tg_token and tg_chat):
                print("  ⚠️ TELEGRAM-TOKEN/CHAT-ID 없음 → SKIP")
                return None
            new_creds.append({
                "credential_id": cred_id,
                "type": "telegram",
                "data": [
                    {"key": "bot_token", "value": tg_token, "type": "password", "label": "Bot Token"},
                    {"key": "chat_id", "value": tg_chat, "type": "text", "label": "Chat ID"},
                ],
            })

        else:
            new_creds.append(cred)

    workflow["credentials"] = new_creds
    return workflow


async def _wait_for_job(job, timeout: float, force_stop: bool = False) -> str:
    """Job 완료 대기. force_stop=True 면 타임아웃 도달 시 stop() 호출."""
    try:
        await asyncio.wait_for(job._task, timeout=timeout)
        return job.status
    except asyncio.TimeoutError:
        if force_stop:
            print(f"  ⏰ TIMEOUT ({timeout}s) → force stop (ScheduleNode 포함)")
            await job.stop()
            # stop 후 terminal state 로 전환 대기
            try:
                await asyncio.wait_for(job._task, timeout=5)
            except asyncio.TimeoutError:
                pass
            return job.status
        print(f"  ⏰ TIMEOUT ({timeout}s) — FAIL")
        await job.stop()
        return "timeout"


async def run_workflow(filename: str, timeout: float, force_stop: bool = False) -> bool:
    """단일 워크플로우 실행."""
    filepath = WORKFLOWS_DIR / filename
    if not filepath.exists():
        print(f"  ❌ 파일 없음: {filename}")
        return False

    with open(filepath) as f:
        workflow = json.load(f)

    print(f"\n{'=' * 70}")
    print(f"▶ {filename}")
    print(f"  {workflow.get('name', '')}")
    print(f"  nodes={len(workflow.get('nodes', []))} edges={len(workflow.get('edges', []))}")
    print("=" * 70)

    workflow = _inject_credentials(workflow)
    if workflow is None:
        return False

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[TestListener()])
    status = await _wait_for_job(job, timeout, force_stop=force_stop)

    print(f"  Status: {status}")

    # force_stop=True 인 경우 cancelled/stopped 도 정상으로 간주
    terminal_ok = status in ("completed", "cancelled", "stopped")
    if force_stop and terminal_ok:
        print("  ✅ PASS (forced terminal state)")
        return True
    if status == "completed":
        print("  ✅ PASS")
        return True
    print(f"  ❌ FAIL ({status})")
    return False


async def main():
    print("🤖 왕초보 텔레그램 워크플로우 실전 테스트 (68~72)")
    print("=" * 70)

    has_stock = bool(os.environ.get("APPKEY") and os.environ.get("APPSECRET"))
    has_futures = bool(os.environ.get("APPKEY_FUTURE_FAKE") and os.environ.get("APPSECRET_FUTURE_FAKE"))
    has_tg = bool(os.environ.get("TELEGRAM-TOKEN") and os.environ.get("TELEGRAM-CHAT-ID"))
    print(f"  해외주식 실계좌 키: {'✅' if has_stock else '❌'}")
    print(f"  해외선물 모의계좌 키: {'✅' if has_futures else '❌'}")
    print(f"  텔레그램 봇: {'✅' if has_tg else '❌'}")

    if not (has_stock and has_futures and has_tg):
        print("\n❌ 필요한 credential 이 .env 에 없습니다.")
        print("   APPKEY, APPSECRET, APPKEY_FUTURE_FAKE, APPSECRET_FUTURE_FAKE,")
        print("   TELEGRAM-TOKEN, TELEGRAM-CHAT-ID 필요")
        sys.exit(1)

    tests = [
        # 68~72: 왕초보 (해외주식 실계좌 조회 + 텔레그램)
        ("68-telegram-portfolio-summary.json", TIMEOUT_SHORT, False),
        ("69-telegram-price-alert.json", TIMEOUT_SHORT, False),
        ("70-telegram-rsi-oversold.json", TIMEOUT_SHORT, False),
        ("71-telegram-scheduled-morning-report.json", TIMEOUT_SCHEDULE, True),
        ("72-telegram-loss-alert.json", TIMEOUT_SHORT, False),
        # 73~77: 중급 (해외선물 모의 + 실제 매매 자동화)
        ("73-auto-buy-bollinger-lower.json", TIMEOUT_SHORT, False),
        ("74-auto-stop-loss-per-position.json", TIMEOUT_SCHEDULE, True),  # Schedule
        ("75-day-trading-bot.json", TIMEOUT_SCHEDULE, True),  # 2중 Schedule
        ("76-golden-cross-auto-buy.json", TIMEOUT_SCHEDULE, True),  # Schedule
        ("77-risk-manager-bot.json", TIMEOUT_SCHEDULE, True),  # Schedule
    ]

    results = []
    for filename, timeout, force_stop in tests:
        passed = await run_workflow(filename, timeout, force_stop=force_stop)
        results.append((filename, passed))

    print(f"\n{'=' * 70}")
    print("📊 결과 요약")
    print("=" * 70)
    pass_count = sum(1 for _, p in results if p)
    for filename, passed in results:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {filename}")
    print(f"\n  총 {pass_count}/{len(results)} 통과")

    sys.exit(0 if pass_count == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
