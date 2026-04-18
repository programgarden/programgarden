"""
실전 봇 실행 스크립트

사용법:
    cd /Users/jyj/ls_projects/programgarden/src/programgarden
    poetry run python ../../scripts/live_bot/runner.py
또는:
    poetry run python -m runner  (scripts/live_bot 에서)

필수 환경변수 (.env 또는 shell export):
    LS_APPKEY            - LS증권 해외주식 App Key
    LS_APPSECRET         - LS증권 해외주식 App Secret
    TELEGRAM_TOKEN       - 텔레그램 봇 토큰
    TELEGRAM_CHAT_ID     - 텔레그램 채팅 ID
"""

import asyncio
import json
import os
import signal
import sys
import urllib.parse
import urllib.request
from pathlib import Path


HERE = Path(__file__).parent
PROJECT_ROOT = HERE.parent.parent
WORKFLOW_JSON = HERE / "workflow.json"


def _load_env_file(path: Path) -> None:
    """.env 파일을 파싱하여 os.environ에 주입 (python-dotenv 없이 동작)."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_env(key_candidates: list[str]) -> str:
    """여러 키 후보 중 먼저 발견되는 값을 반환."""
    for key in key_candidates:
        val = os.environ.get(key)
        if val:
            return val
    raise RuntimeError(
        f"환경변수 누락: {' / '.join(key_candidates)} 중 하나를 .env 또는 shell에 설정하세요."
    )


def _build_secrets() -> dict:
    appkey = _resolve_env(["LS_APPKEY", "APPKEY"])
    appsecret = _resolve_env(["LS_APPSECRET", "APPSECRET"])
    tg_token = _resolve_env(["TELEGRAM_TOKEN", "TELEGRAM-TOKEN"])
    tg_chat = _resolve_env(["TELEGRAM_CHAT_ID", "TELEGRAM-CHAT-ID"])

    return {
        "broker_cred": {"appkey": appkey, "appsecret": appsecret},
        "telegram_cred": {"bot_token": tg_token, "chat_id": tg_chat},
    }


def _inject_credentials_into_workflow(workflow: dict, secrets: dict) -> dict:
    """워크플로우 JSON의 credentials[].data 의 빈 value 필드에 실제 값 주입."""
    for cred in workflow.get("credentials", []):
        cred_id = cred.get("credential_id", "")
        values = secrets.get(cred_id)
        if not values:
            continue
        data = cred.get("data", [])
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "key" in item:
                    key = item["key"]
                    if key in values and not item.get("value"):
                        item["value"] = values[key]
        elif isinstance(data, dict):
            for k, v in values.items():
                if not data.get(k):
                    data[k] = v
    return workflow


def _register_custom_plugins() -> None:
    """scripts/live_bot/plugins 의 동적 플러그인 등록."""
    sys.path.insert(0, str(HERE))
    from plugins import register_all  # type: ignore[import-not-found]
    register_all()


class ConsoleListener:
    """ExecutionListener — 콘솔 로그 출력 + 텔레그램 포워딩."""

    def __init__(self, tg_token: str | None = None, tg_chat_id: str | None = None):
        self._tg_token = tg_token
        self._tg_chat_id = tg_chat_id

    async def _send_telegram(self, text: str) -> None:
        if not self._tg_token or not self._tg_chat_id:
            return
        url = f"https://api.telegram.org/bot{self._tg_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self._tg_chat_id,
            "text": text[:4000],
            "parse_mode": "HTML",
        }).encode()
        try:
            await asyncio.to_thread(
                lambda: urllib.request.urlopen(
                    urllib.request.Request(url, data=data, method="POST"),
                    timeout=10,
                ).read()
            )
        except Exception as e:  # noqa: BLE001
            print(f"[telegram-forward-error] {e}")

    async def on_node_state_change(self, event):  # type: ignore[override]
        state = getattr(event, "state", "")
        node_id = getattr(event, "node_id", "?")
        print(f"[node] {node_id}: {state}", flush=True)

    async def on_edge_state_change(self, event):  # type: ignore[override]
        state = getattr(event, "state", "")
        src = getattr(event, "from_node", getattr(event, "source", "?"))
        dst = getattr(event, "to_node", getattr(event, "target", "?"))
        print(f"[edge] {src}→{dst}: {state}", flush=True)

    async def on_log(self, event):  # type: ignore[override]
        level = getattr(event, "level", "INFO")
        msg = getattr(event, "message", "")
        print(f"[{level}] {msg}", flush=True)
        if str(level).upper() in ("ERROR", "CRITICAL"):
            await self._send_telegram(f"⚠️ <b>{level}</b>\n{msg}")

    async def on_notification(self, event):  # type: ignore[override]
        category = getattr(event, "category", "?")
        severity = getattr(event, "severity", "INFO")
        msg = getattr(event, "message", "")
        print(f"[notif:{category}:{severity}] {msg}", flush=True)
        icon = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(
            str(severity).upper(), "📢"
        )
        await self._send_telegram(
            f"{icon} <b>[{category}]</b> {severity}\n{msg}"
        )

    async def on_job_state_change(self, event):  # type: ignore[override]
        state = getattr(event, "state", "")
        print(f"[job] state={state}", flush=True)
        await self._send_telegram(f"🔄 <b>Job state</b>: {state}")

    async def on_retry(self, event):  # type: ignore[override]
        node = getattr(event, "node_id", "?")
        attempt = getattr(event, "attempt", "?")
        err = getattr(event, "error_type", "")
        print(f"[retry] {node} attempt={attempt} error={err}", flush=True)

    async def on_risk_event(self, event):  # type: ignore[override]
        kind = getattr(event, "event_type", getattr(event, "kind", "?"))
        msg = getattr(event, "message", str(event))
        print(f"[risk] {kind}: {msg}", flush=True)
        await self._send_telegram(f"🛡️ <b>Risk</b> {kind}\n{msg}")

    async def on_workflow_pnl_update(self, event):  # type: ignore[override]
        pass

    async def on_display_data(self, event):  # type: ignore[override]
        pass

    async def on_token_usage(self, event):  # type: ignore[override]
        pass

    async def on_ai_tool_call(self, event):  # type: ignore[override]
        pass

    async def on_llm_stream(self, event):  # type: ignore[override]
        pass


async def main() -> int:
    _load_env_file(PROJECT_ROOT / ".env")
    _register_custom_plugins()

    # programgarden lazy import (플러그인 등록 후)
    from programgarden import ProgramGarden, register_all_plugins
    register_all_plugins()  # community 플러그인 일괄 등록

    with WORKFLOW_JSON.open(encoding="utf-8") as f:
        workflow = json.load(f)

    secrets = _build_secrets()
    workflow = _inject_credentials_into_workflow(workflow, secrets)

    pg = ProgramGarden()

    validation = pg.validate(workflow)
    if not validation.is_valid:
        print("❌ 워크플로우 검증 실패:")
        for err in getattr(validation, "errors", []):
            print(f"  - {err}")
        return 1
    warnings = getattr(validation, "warnings", []) or []
    for w in warnings:
        print(f"⚠️  {w}")

    print("✅ 워크플로우 검증 통과 — 실행 시작")
    print(f"  workflow: {workflow.get('name')}")
    print(f"  nodes: {len(workflow.get('nodes', []))}개")

    listener = ConsoleListener(
        tg_token=secrets["telegram_cred"]["bot_token"],
        tg_chat_id=secrets["telegram_cred"]["chat_id"],
    )
    await listener._send_telegram("🤖 <b>live_bot 시작</b> — 워크플로우 검증 통과")
    job = await pg.run_async(
        workflow,
        secrets=secrets,
        storage_dir=str(HERE / "data"),
        listeners=[listener],
    )

    print(f"▶️  Job started: {job.job_id}")

    # 우아한 종료 핸들러 (Ctrl+C)
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        print("\n🛑 종료 신호 수신 — 작업 정리 중 ...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        # 실시간 트레일링스탑 + 30분 주기 매수이므로 무기한 실행
        task = getattr(job, "_task", None)
        if task is not None:
            done, _ = await asyncio.wait(
                [task, asyncio.create_task(stop_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stop_event.is_set():
                await job.stop()
        else:
            await stop_event.wait()
            await job.stop()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 실행 중 오류: {e}")
        try:
            await job.stop()
        except Exception:
            pass
        return 2

    print("✅ Job 종료")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
