"""DCF Fair Value companion — free-cash-flow 데이터경로 (HTTPRequestNode → FieldMapping → DCF).

DCFFairValue 플러그인의 유일 필수 upstream 입력은 `fcf`(자유현금흐름)입니다.
그런데 FMP FundamentalDataNode 는 cash_flow 를 **제공하지 않으므로**(data_type ∈
{profile, key_metrics, income_statement, balance_sheet}) fcf 를 만들 수 없습니다.
그래서 FMP 의 cash-flow-statement 엔드포인트를 HTTPRequestNode 로 직접 호출하고,
freeCashFlow 를 fcf 로 리매핑한 뒤 DCF 플러그인에 투입합니다:

  HTTPRequestNode(FMP /cash-flow-statement)
     → FieldMappingNode(freeCashFlow → fcf)
     → ConditionNode(plugin=DCFFairValue)

fcf 가 없으면 DCF 는 per-symbol missing_reason="fcf_unavailable" 을 반환합니다
(숨은 추정 금지). shares_outstanding / current_price 는 profile 등에서 별도 확보.

⚠️ 후속(FMP cash_flow data_type 정식화)이 완료되면 HTTPRequestNode 우회 없이
   FundamentalDataNode(data_type=cash_flow) 로 단순화됩니다.

실행 (실제 FMP API 키 필요 — 환경변수 FMP_API_KEY 로 주입):
    cd src/programgarden
    poetry run python examples/programmer_example/dcf_cashflow_datapath.py

참고 — 대응하는 워크플로우 스니펫 (fcf 리매핑 후 DCF):
    {
      "id": "http_cf",
      "type": "HTTPRequestNode",
      "url": "https://financialmodelingprep.com/api/v3/cash-flow-statement/AAPL?period=annual&limit=1&apikey={{ ... }}",
      "method": "GET"
    },
    {
      "id": "map_fcf",
      "type": "FieldMappingNode",
      "data": "{{ nodes.http_cf.data }}",
      "mappings": [
        {"source": "symbol", "target": "symbol"},
        {"source": "freeCashFlow", "target": "fcf"}
      ]
    },
    {
      "id": "dcf",
      "type": "ConditionNode",
      "plugin": "DCFFairValue",
      "items": {
        "from": "{{ nodes.map_fcf.data }}",
        "extract": {
          "symbol": "{{ row.symbol }}",
          "exchange": "{{ row.exchange }}",
          "fcf": "{{ row.fcf }}",
          "shares_outstanding": "{{ row.shares_outstanding }}",
          "current_price": "{{ row.current_price }}"
        }
      },
      "fields": {"growth_rate": 0.10, "discount_rate": 0.09, "terminal_growth": 0.025, "years": 10, "margin_of_safety": 0.25}
    }
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

from programgarden import NodeRunner
from programgarden_community.plugins.dcf_fair_value import dcf_fair_value_condition

# ⚠️ 자리표시자 — 실제 FMP API 키로 교체하세요 (환경변수 FMP_API_KEY 우선).
FMP_API_KEY = os.environ.get("FMP_API_KEY", "YOUR_FMP_API_KEY_HERE")

SYMBOLS = [
    {"symbol": "AAPL", "exchange": "NASDAQ"},
    {"symbol": "MSFT", "exchange": "NASDAQ"},
]

_FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _remap_freecashflow(cf_rows, symbol, exchange, shares, price):
    """HTTPRequestNode 응답(list[dict])에서 freeCashFlow → fcf 리매핑 (FieldMappingNode 등가)."""
    if not isinstance(cf_rows, list) or not cf_rows:
        return {
            "symbol": symbol, "exchange": exchange,
            "fcf": None,  # fcf 없음 → DCF 가 missing_reason 반환 (숨은 추정 금지)
            "shares_outstanding": shares, "current_price": price,
        }
    latest = cf_rows[0] if isinstance(cf_rows[0], dict) else {}
    fcf = latest.get("freeCashFlow")
    return {
        "symbol": symbol, "exchange": exchange,
        "fcf": fcf,
        "shares_outstanding": shares,
        "current_price": price,
    }


async def fetch_cashflow_row(runner: "NodeRunner", symbol: str, exchange: str) -> dict:
    """HTTPRequestNode 로 FMP cash-flow-statement 직접 호출 → fcf 리매핑."""
    url = f"{_FMP_BASE}/cash-flow-statement/{symbol}?period=annual&limit=1&apikey={FMP_API_KEY}"
    http_out = await runner.run("HTTPRequestNode", url=url, method="GET")
    # HTTPRequestNode 출력 포트는 배포 버전에 따라 data/body/json 중 하나
    cf_rows = None
    for key in ("data", "json", "body", "response"):
        if isinstance(http_out, dict) and key in http_out:
            cf_rows = http_out[key]
            break
    if isinstance(cf_rows, str):
        try:
            cf_rows = json.loads(cf_rows)
        except (ValueError, TypeError):
            cf_rows = None

    # shares / price 는 별도 확보 필요 — 여기서는 profile 조회로 대체 가능하나,
    # companion 단순화를 위해 자리표시자(실운영 시 profile/quote 로 채움).
    shares = None
    price = None
    return _remap_freecashflow(cf_rows, symbol, exchange, shares, price)


async def main():
    print("=" * 64)
    print("  DCF companion — HTTPRequestNode(FMP cash-flow) → fcf → DCFFairValue")
    print("=" * 64)

    if FMP_API_KEY == "YOUR_FMP_API_KEY_HERE":
        print("\n⚠️ FMP_API_KEY 가 자리표시자입니다. 환경변수 FMP_API_KEY 를 설정하거나")
        print("   스크립트 상단 FMP_API_KEY 를 실제 키로 교체한 뒤 다시 실행하세요.")
        return

    rows = []
    async with NodeRunner() as runner:
        for s in SYMBOLS:
            row = await fetch_cashflow_row(runner, s["symbol"], s["exchange"])
            print(f"  {s['symbol']}: fcf={row.get('fcf')} shares={row.get('shares_outstanding')} "
                  f"price={row.get('current_price')}")
            rows.append(row)

    result = await dcf_fair_value_condition(
        data=rows,
        fields={
            "growth_rate": 0.10,
            "discount_rate": 0.09,
            "terminal_growth": 0.025,
            "years": 10,
            "margin_of_safety": 0.25,
        },
    )

    print("\n--- analysis ---")
    print(f"  {json.dumps(result.get('analysis', {}), ensure_ascii=False)}")

    print("\n--- per symbol ---")
    for sr in result.get("symbol_results", []):
        if sr.get("missing_reason"):
            print(f"  [{sr['symbol']}] missing_reason={sr['missing_reason']}"
                  f"{' (fcf 데이터경로가 fcf 를 못 채웠음)' if sr['missing_reason'] == 'fcf_unavailable' else ''}")
        else:
            print(f"  [{sr['symbol']}] fair_value={sr['fair_value']} price={sr['current_price']} "
                  f"undervalued={sr['undervalued']}")


if __name__ == "__main__":
    asyncio.run(main())
