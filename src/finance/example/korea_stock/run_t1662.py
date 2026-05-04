"""run_t1662.py — manual integration test for t1662 시간대별프로그램매매추이차트.

Scenarios:
  1. KOSPI (gubun='0') / 금액 (gubun1='0') / 당일 (gubun3='0') / KRX (exchgubun='K').
  2. KOSDAQ (gubun='1') / 수량 (gubun1='1') / 당일 (gubun3='0') / KRX.
  3. KOSPI / 금액 / 전일 (gubun3='1') / 통합 (exchgubun='U').

Requires .env with APPKEY_KOREA / APPSECRET_KOREA.
Run: cd src/finance && poetry run python example/korea_stock/run_t1662.py

NOTE: t1662 returns the entire chart in a single response — there is NO
``occurs_req`` / cursor continuation (unlike t1632 / t1633 / t1637).
Only ``req()`` is called.

NOTE: Row meaning, array ordering, ``volume`` units, and any arithmetic
relationship between fields (tot1/tot2/tot3, cha1/cha2/cha3,
bcha1/bcha2/bcha3) are not documented in the LS public spec — values
are printed as reported by LS.
"""

import logging
from dotenv import load_dotenv
import os
from programgarden_finance import LS, t1662

logger = logging.getLogger(__name__)

load_dotenv()


def _print_block_summary(label: str, block: list) -> None:
    """Print a summary of t1662OutBlock rows (first / last row shown in full)."""
    logger.info(f"[{label}] block — {len(block)} rows")
    if not block:
        return
    first = block[0]
    last = block[-1]
    logger.info(
        f"  row[0]: time={first.time!r}, k200jisu={first.k200jisu}, "
        f"sign={first.sign!r}, change={first.change}, k200basis={first.k200basis}"
    )
    logger.info(
        f"  row[0]: tot1={first.tot1:,}, tot2={first.tot2:,}, tot3={first.tot3:,}"
    )
    logger.info(
        f"  row[0]: cha1={first.cha1:,}, cha2={first.cha2:,}, cha3={first.cha3:,}"
    )
    logger.info(
        f"  row[0]: bcha1={first.bcha1:,}, bcha2={first.bcha2:,}, bcha3={first.bcha3:,}, "
        f"volume={first.volume:,}"
    )
    if len(block) > 1:
        logger.info(
            f"  row[-1]: time={last.time!r}, k200jisu={last.k200jisu}, "
            f"sign={last.sign!r}, change={last.change}"
        )


def _print_response(label: str, response) -> None:
    """Pretty-print a single t1662 response."""
    logger.info("=" * 110)
    logger.info(f"[{label}] rsp_cd={response.rsp_cd!r}, rsp_msg={response.rsp_msg!r}")

    if response.error_msg:
        logger.error(f"[{label}] Request failed: {response.error_msg}")
        return

    _print_block_summary(label, response.block)


def _login_or_exit(label: str):
    """Login helper — returns LS instance or None on failure."""
    appkey = os.getenv("APPKEY_KOREA")
    appsecret = os.getenv("APPSECRET_KOREA")
    if not appkey or not appsecret:
        logger.error(
            f"[{label}] APPKEY_KOREA / APPSECRET_KOREA not set in .env — skipping"
        )
        return None
    ls = LS()
    login_result = ls.login(appkey=appkey, appsecretkey=appsecret)
    if login_result is False:
        logger.error(f"[{label}] Login failed")
        return None
    return ls


def test_scenario1_kospi_amount_today():
    """Scenario 1 — KOSPI / 금액 / 당일 / KRX."""
    ls = _login_or_exit("KOSPI/amount/today/KRX")
    if ls is None:
        return

    tr = ls.국내주식().프로그램매매().시간대별프로그램매매추이차트(
        t1662.T1662InBlock(
            gubun="0",     # 거래소 (KOSPI)
            gubun1="0",    # 금액
            gubun3="0",    # 당일
            exchgubun="K",  # KRX
        )
    )
    response = tr.req()
    _print_response("KOSPI/amount/today/KRX", response)


def test_scenario2_kosdaq_quantity_today():
    """Scenario 2 — KOSDAQ / 수량 / 당일 / KRX."""
    ls = _login_or_exit("KOSDAQ/quantity/today/KRX")
    if ls is None:
        return

    tr = ls.국내주식().프로그램매매().시간대별프로그램매매추이차트(
        t1662.T1662InBlock(
            gubun="1",     # 코스닥 (KOSDAQ)
            gubun1="1",    # 수량
            gubun3="0",    # 당일
            exchgubun="K",  # KRX
        )
    )
    response = tr.req()
    _print_response("KOSDAQ/quantity/today/KRX", response)


def test_scenario3_kospi_amount_prev_unified():
    """Scenario 3 — KOSPI / 금액 / 전일 / 통합 (exchgubun='U')."""
    ls = _login_or_exit("KOSPI/amount/prior/Unified")
    if ls is None:
        return

    tr = ls.국내주식().프로그램매매().시간대별프로그램매매추이차트(
        t1662.T1662InBlock(
            gubun="0",     # 거래소 (KOSPI)
            gubun1="0",    # 금액
            gubun3="1",    # 전일
            exchgubun="U",  # 통합
        )
    )
    response = tr.req()
    _print_response("KOSPI/amount/prior/Unified", response)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_scenario1_kospi_amount_today()
    test_scenario2_kosdaq_quantity_today()
    test_scenario3_kospi_amount_prev_unified()
