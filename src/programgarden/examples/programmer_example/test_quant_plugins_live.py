"""퀀트 플러그인 Phase 3 실전 테스트.

LS증권 API로 실제 과거 데이터를 가져와 5개 플러그인을 직접 호출 테스트합니다.
- GoldenRatio, PivotPoint, MeanReversion, BreakoutRetest, ThreeLineStrike

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_quant_plugins_live.py
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

# .env 로드
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from programgarden import ProgramGarden
from programgarden_core.bases.listener import BaseExecutionListener

# 플러그인 직접 import
from programgarden_community.plugins.golden_ratio import golden_ratio_condition
from programgarden_community.plugins.pivot_point import pivot_point_condition
from programgarden_community.plugins.mean_reversion import mean_reversion_condition
from programgarden_community.plugins.breakout_retest import breakout_retest_condition
from programgarden_community.plugins.three_line_strike import three_line_strike_condition

TEST_TIMEOUT = 30


class SilentListener(BaseExecutionListener):
    async def on_log(self, event):
        if event.level == "error":
            print(f"  [error] {event.message}")


async def fetch_historical_data(symbols: list) -> list:
    """LS증권 API로 과거 데이터 조회 (워크플로우 실행)"""
    watchlist_symbols = [{"exchange": "NASDAQ", "symbol": s} for s in symbols]

    workflow = {
        "id": "fetch-data",
        "name": "Fetch Historical Data",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "broker",
                "type": "OverseasStockBrokerNode",
                "credential_id": "test-cred",
            },
            {
                "id": "watchlist",
                "type": "WatchlistNode",
                "symbols": watchlist_symbols,
            },
            {
                "id": "historical",
                "type": "OverseasStockHistoricalDataNode",
                "symbol": "{{ item }}",
                "period": "D",
                "start_date": "{{ date.ago(90, format='yyyymmdd') }}",
                "end_date": "{{ date.today(format='yyyymmdd') }}",
            },
        ],
        "edges": [
            {"from": "start", "to": "broker"},
            {"from": "broker", "to": "watchlist"},
            {"from": "watchlist", "to": "historical"},
        ],
        "credentials": [
            {
                "credential_id": "test-cred",
                "type": "broker_ls_overseas_stock",
                "data": {
                    "appkey": os.environ.get("APPKEY", ""),
                    "appsecret": os.environ.get("APPSECRET", ""),
                },
            }
        ],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[SilentListener()])
    await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)

    hist = job.context.get_all_outputs("historical")
    if not isinstance(hist, dict):
        return []

    # value 포트에서 데이터 추출
    value_list = hist.get("value", [])
    if not isinstance(value_list, list):
        value_list = [value_list]

    # 플랫 배열로 변환 (플러그인 입력 형식)
    flat_data = []
    for item in value_list:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol", "")
        exchange = item.get("exchange", "")
        time_series = item.get("time_series", [])
        for row in time_series:
            if isinstance(row, dict):
                flat_row = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "date": row.get("date", ""),
                    "open": row.get("open", 0),
                    "high": row.get("high", 0),
                    "low": row.get("low", 0),
                    "close": row.get("close", 0),
                    "volume": row.get("volume", 0),
                }
                flat_data.append(flat_row)

    return flat_data


def _print_results(plugin_name: str, result: dict):
    """결과 출력"""
    passed = result.get("passed_symbols", [])
    failed = result.get("failed_symbols", [])
    print(f"  Passed: {[s.get('symbol', s) for s in passed]}")
    print(f"  Failed: {[s.get('symbol', s) for s in failed]}")

    for sr in result.get("symbol_results", []):
        sym = sr.get("symbol", "?")
        error = sr.get("error")
        if error:
            print(f"  [{sym}] error: {error}")
        else:
            filtered = {k: v for k, v in sr.items()
                       if k not in ("symbol", "exchange") and v is not None}
            # 긴 값 자르기
            for k, v in filtered.items():
                if isinstance(v, float):
                    filtered[k] = round(v, 4)
            print(f"  [{sym}] {json.dumps(filtered, ensure_ascii=False)}")

    for val in result.get("values", []):
        ts_len = len(val.get("time_series", []))
        sym = val.get("symbol", "?")
        print(f"  [{sym}] time_series: {ts_len} rows")


async def main():
    print("=" * 60)
    print("  퀀트 플러그인 Phase 3 실전 테스트")
    print("  (LS증권 API + 실제 과거 데이터 → 플러그인 직접 호출)")
    print("=" * 60)

    appkey = os.environ.get("APPKEY", "")
    if not appkey:
        print("\nAPPKEY 환경변수가 없습니다. .env 파일을 확인하세요.")
        return

    # Step 1: 실제 데이터 가져오기
    print("\n[Step 1] LS증권 API에서 AAPL 90일 과거 데이터 조회...")
    data = await fetch_historical_data(["AAPL"])

    if not data:
        print("  데이터 조회 실패!")
        return

    print(f"  {len(data)} rows loaded (symbol={data[0].get('symbol')})")
    print(f"  기간: {data[0].get('date')} ~ {data[-1].get('date')}")
    print(f"  최근 종가: {data[-1].get('close')}")

    # Step 2: 각 플러그인 직접 호출
    tests = [
        (
            "GoldenRatio",
            golden_ratio_condition,
            {"lookback": 50, "level": "0.618", "direction": "support", "tolerance": 0.03},
        ),
        (
            "PivotPoint",
            pivot_point_condition,
            {"pivot_type": "standard", "direction": "support", "tolerance": 0.015},
        ),
        (
            "MeanReversion",
            mean_reversion_condition,
            {"ma_period": 20, "deviation": 2.0, "direction": "oversold"},
        ),
        (
            "BreakoutRetest",
            breakout_retest_condition,
            {"lookback": 20, "retest_threshold": 0.02, "direction": "bullish"},
        ),
        (
            "ThreeLineStrike",
            three_line_strike_condition,
            {"pattern": "bullish", "min_body_pct": 0.3},
        ),
    ]

    results = {}
    for name, fn, fields in tests:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print("=" * 60)
        try:
            result = await fn(data=data, fields=fields)
            _print_results(name, result)

            # PASS 기준: symbol_results에 데이터가 있고 에러가 없음
            has_results = len(result.get("symbol_results", [])) > 0
            no_error = all("error" not in sr for sr in result.get("symbol_results", []))
            has_time_series = any(
                len(v.get("time_series", [])) > 0
                for v in result.get("values", [])
            )

            success = has_results and no_error and has_time_series
            print(f"\n  {'PASS' if success else 'FAIL'}"
                  f" (results={has_results}, no_error={no_error}, time_series={has_time_series})")
            results[name] = success

        except Exception as e:
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # 요약
    print(f"\n{'=' * 60}")
    print("  실전 테스트 결과 요약")
    print("=" * 60)
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {name:20s} {status}")

    total_pass = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  Total: {total_pass}/{total} passed")


if __name__ == "__main__":
    asyncio.run(main())
