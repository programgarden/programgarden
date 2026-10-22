"""o3117 (Overseas futures/options tick chart) example — paper_trading.

LS 모의투자 환경에서 o3117 차트 데이터 조회를 검증한다.

검증 결과 (2026-05-15):
    - REST endpoint: paper/live 모두 https://openapi.ls-sec.co.kr:8080 동일
      (LS 설계상 단일 REST endpoint + 토큰으로 환경 구분; WebSocket만
      29443 으로 분기됨).
    - paper 환경에서 HKEX 차트 데이터는 정상 제공 (항셍 미니선물 HMHxxx 등).
    - paper 환경에서 CME(NQ/MNQ/ES) 차트 데이터는 미제공
      → rsp_cd=00000 + rsp_msg="해당자료가 없습니다" + block1=[].

paper 로 시스템 검증 시 HKEX 심볼(HSI·HMH·HMCE·HTI 시리즈) 권장.
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from programgarden_finance import LS, o3101, o3117
from programgarden_finance.ls.config import URLS


ENV_PATH = Path(__file__).resolve().parents[2] / ".env.t1310-live"
load_dotenv(dotenv_path=ENV_PATH)

logger = logging.getLogger(__name__)

# Series prefixes verified active on paper_trading=True (2026-05-15).
# Used to scope the o3101 master result to actively-traded HKEX futures
# so the picker does not silently fall back to an option or low-liquidity
# instrument the user did not intend to test.
HKEX_ACTIVE_SERIES = ("HSI", "HMH", "HMCE", "HTI")


def _pick_active_hkex_symbol(master_resp) -> str:
    if not master_resp or not getattr(master_resp, "block", None):
        raise RuntimeError(
            "o3101 master response empty — cannot pick HKEX symbol"
        )
    candidates = sorted(
        getattr(item, "Symbol", "")
        for item in master_resp.block
        if getattr(item, "ExchCd", "") == "HKEX"
        and getattr(item, "Symbol", "").startswith(HKEX_ACTIVE_SERIES)
    )
    candidates = [s for s in candidates if s]
    if not candidates:
        raise RuntimeError(
            "No active HKEX symbol found in o3101 master "
            f"(filtered by series prefixes: {HKEX_ACTIVE_SERIES})"
        )
    return candidates[0]


async def call_o3117(ls: LS, shcode: str, label: str) -> None:
    print()
    print("=" * 70)
    print(f"[{label}] o3117 shcode={shcode}")
    print("=" * 70)

    req = ls.overseas_futureoption().chart().o3117(
        o3117.O3117InBlock(
            shcode=shcode,
            ncnt=0,
            qrycnt=10,
            cts_seq="",
            cts_daygb="",
        )
    )
    try:
        result = await req.req_async()
    except Exception as exc:
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        return

    print(f"  status_code = {result.status_code}")
    print(f"  rsp_cd      = {result.rsp_cd}")
    print(f"  rsp_msg     = {result.rsp_msg}")
    print(f"  error_msg   = {result.error_msg}")
    print(f"  block       = {result.block}")
    print(f"  block1 len  = {len(result.block1)}")
    if result.raw_data is not None:
        print(f"  req url     = {getattr(result.raw_data, 'url', None)}")


async def test_req_o3117() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    print("[URLS] FO_CHART_URL  =", URLS.FO_CHART_URL)
    print("[URLS] OAUTH_URL     =", URLS.OAUTH_URL)
    print("[URLS] WSS (paper)   =", URLS.get_wss_url(paper_trading=True))
    print("[URLS] WSS (live)    =", URLS.get_wss_url(paper_trading=False))

    appkey = os.getenv("APPKEY_FUTURE_FAKE")
    appsecret = os.getenv("APPSECRET_FUTURE_FAKE")
    if not appkey or not appsecret:
        logger.error("APPKEY_FUTURE_FAKE / APPSECRET_FUTURE_FAKE 가 .env.t1310-live 에 없음")
        return

    ls = LS()
    if not ls.login(appkey=appkey, appsecretkey=appsecret, paper_trading=True):
        logger.error("로그인 실패 (paper_trading=True)")
        return
    print("[login] OK (paper_trading=True)")

    # 1) HKEX 마스터 조회 → active 심볼 1개
    print()
    print("=" * 70)
    print("[master] o3101 paper HKEX")
    print("=" * 70)
    master = ls.overseas_futureoption().market().o3101(
        body=o3101.O3101InBlock(gubun="1")
    )
    try:
        master_resp = await master.req_async()
    except Exception as exc:
        logger.error("o3101 EXCEPTION: %s: %s", type(exc).__name__, exc)
        master_resp = None

    if master_resp is not None:
        print(f"  rsp_cd  = {master_resp.rsp_cd}")
        print(f"  rsp_msg = {master_resp.rsp_msg}")
        block_len = len(master_resp.block) if getattr(master_resp, "block", None) else 0
        print(f"  block len = {block_len}")
        if master_resp.raw_data is not None:
            print(f"  req url = {getattr(master_resp.raw_data, 'url', None)}")

    # 2) HKEX active 심볼 (paper 에서 데이터 정상 수신 기대)
    #    picker 가 빈 결과면 RuntimeError 로 즉시 중단 — silent skip 시
    #    뒤따르는 CME 비교만 실행되어 검증 자체가 무의미해지는 사고 방지.
    hkex_symbol = _pick_active_hkex_symbol(master_resp)
    print(f"  picked HKEX symbol = {hkex_symbol}")
    await call_o3117(ls, hkex_symbol, label="HKEX")

    # 3) CME 비교 (paper 에서 데이터 없음 — rsp_cd=00000 + 해당자료가 없습니다)
    for cme_sym in ("NQM26", "MNQM26", "ESM26"):
        await call_o3117(ls, cme_sym, label=f"CME-{cme_sym}")


if __name__ == "__main__":
    asyncio.run(test_req_o3117())
