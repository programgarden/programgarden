"""Piotroski F-Score companion — income_statement + balance_sheet 병합 데이터경로.

PiotroskiFScore 플러그인은 종목당 최소 2개 연도의 손익계산서(income_statement)와
재무상태표(balance_sheet) 항목을 **한 행으로 병합**해서 받아야 합니다. 그런데
FMP FundamentalDataNode 는 호출당 하나의 statement type 만 반환하고
(data_type ∈ {profile, key_metrics, income_statement, balance_sheet}),
cash_flow 는 아예 제공하지 않습니다. 따라서:

  1) FundamentalDataNode(data_type=income_statement) 로 손익계산서 조회
  2) FundamentalDataNode(data_type=balance_sheet)  로 재무상태표 조회
  3) (symbol, calendarYear) 키로 두 결과를 파이썬에서 병합
  4) 병합된 다년치 배열을 PiotroskiFScore 플러그인에 단일 호출로 투입

⚠️ 축소역량: FMP 에 cash_flow 가 없어 CFO 의존 2신호(cfo_positive, accruals)는
   생략되어 max_score=7 로 채점됩니다 (analysis.skipped_signals / analysis.note).

⚠️ ConditionNode auto-iterate 는 종목별로 1행만 넘겨 연도 비교가 불가하므로,
   이 스크립트처럼 다년치 배열을 단일 호출로 넘기거나 NodeRunner 를 사용하세요.

실행 (실제 FMP API 키 필요 — 아래 credential 자리표시자를 교체):
    cd src/programgarden
    poetry run python examples/programmer_example/piotroski_income_balance_merge.py

참고 — 위 데이터경로에 대응하는 ConditionNode 워크플로우 스니펫:
    {
      "id": "piotroski",
      "type": "ConditionNode",
      "plugin": "PiotroskiFScore",
      "items": {
        "from": "{{ nodes.merged.data }}",   # income+balance 병합 배열
        "extract": {
          "symbol": "{{ row.symbol }}",
          "exchange": "{{ row.exchange }}",
          "calendarYear": "{{ row.calendarYear }}",
          "netIncome": "{{ row.netIncome }}",
          "revenue": "{{ row.revenue }}",
          "grossProfit": "{{ row.grossProfit }}",
          "weightedAverageShsOut": "{{ row.weightedAverageShsOut }}",
          "totalAssets": "{{ row.totalAssets }}",
          "longTermDebt": "{{ row.longTermDebt }}",
          "totalCurrentAssets": "{{ row.totalCurrentAssets }}",
          "totalCurrentLiabilities": "{{ row.totalCurrentLiabilities }}"
        }
      },
      "fields": {"min_score": 5}
    }
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 경로 설정 (repo 루트 기준 core/community/programgarden 소스 추가)
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))

# .env 로드 (있으면)
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

# 플러그인 직접 import (중앙 등록 여부와 무관하게 companion 이 동작)
from programgarden_community.plugins.piotroski_f_score import piotroski_f_score_condition

TEST_TIMEOUT = 60

# ⚠️ 자리표시자 — 실제 FMP API 키로 교체하세요 (환경변수 FMP_API_KEY 우선).
FMP_API_KEY = os.environ.get("FMP_API_KEY", "YOUR_FMP_API_KEY_HERE")

SYMBOLS = [
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "exchange": "NASDAQ"},
]


class SilentListener(BaseExecutionListener):
    async def on_log(self, event):
        if event.level == "error":
            print(f"  [error] {event.message}")


def _fmp_credential():
    return {
        "credential_id": "fmp-cred",
        "type": "fmp_api",
        "data": [{"key": "api_key", "value": FMP_API_KEY, "type": "password", "label": "FMP API Key"}],
    }


async def fetch_statements(data_type: str) -> list:
    """FundamentalDataNode 로 지정 statement type 을 다년치 조회 (limit=4)."""
    workflow = {
        "id": f"fetch-{data_type}",
        "name": f"Fetch {data_type}",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {
                "id": "fundamental",
                "type": "FundamentalDataNode",
                "credential_id": "fmp-cred",
                "symbols": SYMBOLS,
                "data_type": data_type,
                "period": "annual",
                "limit": 4,
            },
        ],
        "edges": [{"from": "start", "to": "fundamental"}],
        "credentials": [_fmp_credential()],
    }

    pg = ProgramGarden()
    job = await pg.run_async(workflow, listeners=[SilentListener()])
    await asyncio.wait_for(job._task, timeout=TEST_TIMEOUT)

    out = job.context.get_all_outputs("fundamental")
    if not isinstance(out, dict):
        return []
    data = out.get("data", [])
    return data if isinstance(data, list) else []


def _year_of(row: dict) -> str:
    return str(row.get("calendarYear") or row.get("date", ""))[:4]


def merge_income_balance(income_rows: list, balance_rows: list) -> list:
    """(symbol, calendarYear) 키로 손익계산서 + 재무상태표를 한 행으로 병합."""
    merged: dict = {}
    for row in income_rows:
        if not isinstance(row, dict):
            continue
        key = (row.get("symbol", ""), _year_of(row))
        merged.setdefault(key, {})
        merged[key].update(row)
    for row in balance_rows:
        if not isinstance(row, dict):
            continue
        key = (row.get("symbol", ""), _year_of(row))
        merged.setdefault(key, {})
        # balance 필드가 income 필드를 덮어쓰지 않도록 income 우선, 신규 키만 추가
        for k, v in row.items():
            merged[key].setdefault(k, v)
    # calendarYear 를 4자리로 정규화 (플러그인 정렬 안정성)
    result = []
    for (sym, year), rec in merged.items():
        rec = dict(rec)
        rec["symbol"] = sym
        rec.setdefault("exchange", "UNKNOWN")
        rec["calendarYear"] = year
        result.append(rec)
    return result


async def main():
    print("=" * 64)
    print("  Piotroski F-Score companion — income+balance 병합 → 7/9 채점")
    print("=" * 64)

    if FMP_API_KEY == "YOUR_FMP_API_KEY_HERE":
        print("\n⚠️ FMP_API_KEY 가 자리표시자입니다. 환경변수 FMP_API_KEY 를 설정하거나")
        print("   스크립트 상단 FMP_API_KEY 를 실제 키로 교체한 뒤 다시 실행하세요.")
        return

    print("\n[1/3] income_statement 조회...")
    income = await fetch_statements("income_statement")
    print(f"      income rows: {len(income)}")

    print("[2/3] balance_sheet 조회...")
    balance = await fetch_statements("balance_sheet")
    print(f"      balance rows: {len(balance)}")

    merged = merge_income_balance(income, balance)
    print(f"[3/3] 병합 결과: {len(merged)} rows (symbol×year)")

    if not merged:
        print("  병합 데이터가 비었습니다. API 키/응답을 확인하세요.")
        return

    result = await piotroski_f_score_condition(
        data=merged,
        fields={"min_score": 5},
    )

    analysis = result.get("analysis", {})
    print("\n--- analysis ---")
    print(f"  max_score       : {analysis.get('max_score')}")
    print(f"  skipped_signals : {analysis.get('skipped_signals')}")
    print(f"  note            : {analysis.get('note')}")
    print(f"  passed_count    : {analysis.get('passed_count')}")

    print("\n--- per symbol ---")
    for sr in result.get("symbol_results", []):
        if sr.get("missing_reason"):
            print(f"  [{sr['symbol']}] missing_reason={sr['missing_reason']}")
        else:
            print(f"  [{sr['symbol']}] f_score={sr['f_score']}/{sr['max_score']} "
                  f"year={sr.get('year')} signals={json.dumps(sr.get('signals', {}))}")

    print(f"\n  passed_symbols: {[s['symbol'] for s in result.get('passed_symbols', [])]}")


if __name__ == "__main__":
    asyncio.run(main())
