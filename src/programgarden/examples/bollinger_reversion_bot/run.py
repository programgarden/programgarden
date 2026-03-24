"""
볼린저밴드 역추세 자동매매 봇 (텔레그램 알림)

매수: 볼린저밴드(20,2) 하단 터치 과매도 종목 1주 시장가 매수
매도: 보유종목 전량 시장가 매도
알림: 매수/매도 체결 시 텔레그램 메시지

실행 방법:
    cd src/programgarden
    poetry run python examples/bollinger_reversion_bot/run.py

환경변수 (.env 또는 직접 설정):
    APPKEY          - LS증권 App Key
    APPSECRET       - LS증권 App Secret
    TELEGRAM-TOKEN  - 텔레그램 봇 토큰 (BotFather에서 발급)
    TELEGRAM-CHAT-ID - 텔레그램 채팅 ID
"""

import asyncio
import json
import signal
import sys
import os
from datetime import datetime
from pathlib import Path

# 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../core"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../community"))

# .env 로드 (프로젝트 루트)
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
from programgarden_core.bases.listener import (
    BaseExecutionListener,
    NotificationEvent,
    NotificationCategory,
)


class BotListener(BaseExecutionListener):
    """볼린저밴드 역추세 봇 리스너 — 콘솔 로그 + 상태 추적"""

    def __init__(self, bot_token="", chat_id=""):
        super().__init__()
        self.cycle_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.start_time = datetime.now()
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def _send_telegram(self, message):
        """실제 텔레그램 발송 (봇 토큰 있을 때만)"""
        if not self.bot_token or not self.chat_id:
            return
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                })
        except Exception:
            pass

    async def on_node_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""
            node_type = event.node_type or event.node_id

            # 주요 노드만 로그
            if node_type in (
                "OverseasStockNewOrderNode",
                "TelegramNode",
                "ConditionNode",
                "OverseasStockAccountNode",
            ):
                print(f"  ✅ {event.node_id} ({node_type}){duration}")

            # 볼린저 조건 결과 출력
            if "bollinger" in event.node_id and event.outputs:
                passed = event.outputs.get("passed_symbols", [])
                failed = event.outputs.get("failed_symbols", [])
                results = event.outputs.get("symbol_results", [])
                if results:
                    print(f"     볼린저 분석: {len(passed)} 과매도 / {len(failed)} 정상")
                    for r in results:
                        sym = r.get("symbol", "?")
                        price = r.get("current_price", 0)
                        lower = r.get("lower", 0)
                        middle = r.get("middle", 0)
                        status = "⬇️ 과매도" if price < lower else "✔️ 정상"
                        print(f"       {sym}: ${price:.2f} (하단 ${lower:.2f} / 중간 ${middle:.2f}) {status}")

            # 실제 매도 체결 시 텔레그램 발송
            if "sell_order" in event.node_id and event.outputs:
                orders = event.outputs.get("result", event.outputs.get("submitted_orders", []))
                if orders and isinstance(orders, list) and len(orders) > 0:
                    symbols = [o.get("symbol", "?") for o in orders if isinstance(o, dict)]
                    if symbols:
                        self.sell_count += 1
                        await self._send_telegram(
                            f"📈 <b>평균회귀 매도</b>\n종목: {', '.join(symbols)}"
                        )
                        return

            if "buy_order" in event.node_id:
                self.buy_count += 1

        elif state == "failed":
            print(f"  ❌ {event.node_id} FAILED: {event.error}")

    async def on_log(self, event):
        level = event.level if hasattr(event, "level") else "info"
        message = event.message if hasattr(event, "message") else str(event)
        if level in ("error", "warning"):
            print(f"  [{level.upper()}] {message}")

    async def on_notification(self, event: NotificationEvent):
        cat = event.category.value if hasattr(event.category, "value") else event.category

        if cat == "schedule_started":
            self.cycle_count += 1
            elapsed = datetime.now() - self.start_time
            print(f"\n{'─'*50}")
            print(f"  📅 Cycle #{self.cycle_count}  ({elapsed})")
            print(f"     매수 {self.buy_count}건 / 매도 {self.sell_count}건 (누적)")
            print(f"{'─'*50}")
        elif cat == "signal_triggered":
            print(f"  📊 {event.title}")
        elif cat in ("risk_alert", "risk_halt"):
            print(f"  ⚠️  {event.title}: {event.message}")
        elif cat == "workflow_started":
            print(f"  🚀 워크플로우 시작")
        elif cat == "workflow_completed":
            print(f"  🏁 워크플로우 완료")
        elif cat == "workflow_failed":
            print(f"  💥 워크플로우 실패: {event.message}")

    async def on_job_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            print(f"\n{'='*50}")
            print(f"  봇 종료 (총 {self.cycle_count} cycles)")
            print(f"  매수 {self.buy_count}건 / 매도 {self.sell_count}건")
            print(f"  가동시간: {datetime.now() - self.start_time}")
            print(f"{'='*50}")


def load_workflow() -> dict:
    """workflow.json 로드 + credential 주입"""
    workflow_path = Path(__file__).parent / "workflow.json"
    with open(workflow_path) as f:
        workflow = json.load(f)

    # LS증권 API 키
    appkey = os.environ.get("APPKEY", "")
    appsecret = os.environ.get("APPSECRET", "")
    if not appkey or not appsecret:
        print("❌ APPKEY/APPSECRET 환경변수가 없습니다.")
        print("   .env 파일에 설정하거나 환경변수로 export 해주세요.")
        sys.exit(1)

    # 텔레그램 봇
    bot_token = os.environ.get("TELEGRAM-TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM-CHAT-ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print("⚠️  TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID 미설정 — 텔레그램 알림 비활성")

    # credential 주입
    workflow["credentials"] = [
        {
            "credential_id": "broker_cred",
            "type": "broker_ls_overseas_stock",
            "data": [
                {"key": "appkey", "value": appkey},
                {"key": "appsecret", "value": appsecret},
            ],
        },
    ]

    if bot_token and chat_id:
        workflow["credentials"].append({
            "credential_id": "telegram_cred",
            "type": "telegram",
            "data": [
                {"key": "bot_token", "value": bot_token},
                {"key": "chat_id", "value": chat_id},
            ],
        })

    return workflow


async def main():
    print("=" * 50)
    print("  볼린저밴드 역추세 자동매매 봇")
    print("  (하단 터치 매수 / 평균회귀 매도 / 텔레그램)")
    print("=" * 50)

    workflow = load_workflow()

    # watchlist 표시
    symbols = [n for n in workflow["nodes"] if n["id"] == "watchlist"][0]["symbols"]
    sym_list = ", ".join(s["symbol"] for s in symbols)
    print(f"\n  감시 종목: {sym_list}")
    print(f"  전략: 볼린저밴드(20,2) 하단 터치 = 과매도 매수")
    print(f"  스케줄: 30분마다 (평일 09:30-15:55 ET)")
    print(f"  매수: 하단 밴드 이하 → 1주 시장가")
    print(f"  매도: 보유종목 전량 시장가")
    print(f"\n  Ctrl+C 로 종료\n")

    pg = ProgramGarden()
    bot_token = os.environ.get("TELEGRAM-TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM-CHAT-ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "")
    listener = BotListener(bot_token=bot_token, chat_id=chat_id)

    job = await pg.run_async(workflow, listeners=[listener])

    # Ctrl+C graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        print("\n\n  ⏹️  종료 신호 수신 — 봇을 정지합니다...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # 워크플로우 실행 대기 (또는 Ctrl+C)
    done = asyncio.ensure_future(job._task)
    stop = asyncio.ensure_future(stop_event.wait())

    finished, pending = await asyncio.wait(
        [done, stop],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for p in pending:
        p.cancel()

    if stop_event.is_set() and not done.done():
        try:
            await job.cancel()
        except Exception:
            pass

    print("\n  봇이 종료되었습니다. 👋")


if __name__ == "__main__":
    asyncio.run(main())
