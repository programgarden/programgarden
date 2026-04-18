"""JIF (Market Status) real-time subscription example.

EN:
    Subscribes to the broker-agnostic JIF stream for 60 seconds and
    prints each event. At the end, dumps the current snapshot of the 12
    supported markets so you can verify coverage visually.

KO:
    broker credential 타입에 무관한 JIF 장운영정보 스트림을 60초간
    구독한 뒤, 12개 지원 시장의 현재 스냅샷을 출력합니다. Phase 1
    실측 검증용 (평일 한국시간 09~15시 실행 권장).

Usage:
    cd src/finance && poetry run python example/common/real_JIF.py
"""

import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from programgarden_finance import LS
from programgarden_finance.ls.common.real.JIF.blocks import JIFRealResponse
from programgarden_finance.ls.common.real.JIF.constants import (
    JANGUBUN_LABELS,
    SUPPORTED_MARKETS,
    resolve_jstatus,
    resolve_market,
)

logger = logging.getLogger(__name__)

load_dotenv()


def _format_event(resp: JIFRealResponse) -> str:
    body = getattr(resp, "body", None)
    if body is None:
        return f"(no body) rsp_cd={resp.rsp_cd} rsp_msg={resp.rsp_msg}"
    jangubun = str(getattr(body, "jangubun", "") or "")
    jstatus = str(getattr(body, "jstatus", "") or "")
    market = resolve_market(jangubun)
    status_info = resolve_jstatus(jstatus)
    return (
        f"jangubun={jangubun!s:>2}  market={market:<12}  "
        f"jstatus={jstatus!s:>3}  label={status_info['label']!r}  "
        f"regular_open={status_info['is_regular_open']}  "
        f"extended_open={status_info['is_extended_open']}"
    )


async def run_example(duration_sec: int = 60) -> None:
    appkey = os.getenv("APPKEY")
    appsecret = os.getenv("APPSECRET")
    if not appkey or not appsecret:
        logger.error(".env 에 APPKEY / APPSECRET 이 필요합니다.")
        return

    ls = LS.get_instance()
    if not ls.login(appkey=appkey, appsecretkey=appsecret):
        logger.error("로그인 실패")
        return

    client = ls.common().real()
    await client.connect()

    jif = client.JIF()

    def on_message(resp: JIFRealResponse) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {_format_event(resp)}")

    jif.on_jif_message(on_message)
    print(
        f"✅ JIF 구독 시작. {duration_sec}초 대기 중 (평일 KST 09~15시 권장)…"
    )

    try:
        await asyncio.sleep(duration_sec)
    finally:
        jif.on_remove_jif_message()

    snapshot = jif.get_snapshot()
    print("\n──── JIF 스냅샷 (수신 이벤트 기반) ─────────────────────")
    if not snapshot:
        print("(수신된 이벤트 없음 — 장 외 시간이거나 이벤트 push 지연 가능)")
    else:
        for jangubun, entry in sorted(snapshot.items()):
            ts = datetime.fromtimestamp(entry["updated_at"]).strftime("%H:%M:%S")
            print(
                f"[{ts}] {entry['market']:<12} jstatus={entry['jstatus']:>3}  "
                f"{entry['label']!r}  "
                f"(regular_open={entry['is_regular_open']})"
            )

    print("\n──── 12개 지원 시장 커버리지 ──────────────────────────")
    received = {entry["market"] for entry in snapshot.values()}
    for market in SUPPORTED_MARKETS:
        mark = "✅" if market in received else "·"
        jangubun = next(
            (code for code, info in JANGUBUN_LABELS.items() if info["market"] == market),
            "?",
        )
        print(f"  {mark}  {market:<12} (jangubun={jangubun})")

    await client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_example(duration_sec=60))
