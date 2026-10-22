"""
MACD 플러그인 데이터 흐름 디버깅 테스트

HistoricalDataNode → flatten → ConditionNode(MACD) 흐름 검증
"""

import asyncio
from datetime import datetime, timedelta
import random
import pytest

# flatten 함수 테스트
def _flatten(lst: list, nested_key: str) -> list:
    """
    배열의 각 요소에서 중첩 배열을 평탄화하면서 부모 필드를 유지
    """
    if not isinstance(lst, (list, tuple)):
        return []
    
    result = []
    for item in lst:
        if not isinstance(item, dict):
            continue
        
        nested_rows = item.get(nested_key, [])
        if not isinstance(nested_rows, (list, tuple)):
            continue
        
        # 부모 필드 추출 (nested_key 제외)
        parent_fields = {k: v for k, v in item.items() if k != nested_key}
        
        # 각 중첩 행에 부모 필드 병합
        for row in nested_rows:
            if isinstance(row, dict):
                result.append({**parent_fields, **row})
    
    return result


def generate_historical_data_output(symbols: list, days: int = 100) -> list:
    """
    HistoricalDataNode 출력 형식 시뮬레이션
    
    출력 형식:
    [
        {
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "time_series": [
                {"date": "20251001", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000000},
                ...
            ]
        },
        ...
    ]
    """
    result = []
    base_date = datetime.now() - timedelta(days=days)
    
    for sym_info in symbols:
        symbol = sym_info["symbol"]
        exchange = sym_info["exchange"]
        
        # 가격 시계열 생성
        price = 100.0
        time_series = []
        
        for i in range(days):
            change_pct = random.uniform(-0.03, 0.03)
            price = price * (1 + change_pct)
            
            daily_high = price * random.uniform(1.0, 1.02)
            daily_low = price * random.uniform(0.98, 1.0)
            daily_open = random.uniform(daily_low, daily_high)
            daily_close = random.uniform(daily_low, daily_high)
            volume = random.randint(1000000, 5000000)
            
            date_str = (base_date + timedelta(days=i)).strftime("%Y%m%d")
            
            time_series.append({
                "date": date_str,
                "open": round(daily_open, 2),
                "high": round(daily_high, 2),
                "low": round(daily_low, 2),
                "close": round(daily_close, 2),
                "volume": volume,
            })
        
        result.append({
            "symbol": symbol,
            "exchange": exchange,
            "time_series": time_series,
        })
    
    return result


@pytest.mark.asyncio
async def test_data_flow():
    """데이터 흐름 테스트"""
    from programgarden_community.plugins.macd import macd_condition
    
    print("=" * 60)
    print("데이터 흐름 테스트: HistoricalDataNode → flatten → MACD")
    print("=" * 60)
    
    random.seed(42)
    
    # 1. WatchlistNode 시뮬레이션
    symbols = [
        {"exchange": "NASDAQ", "symbol": "AAPL"},
        {"exchange": "NASDAQ", "symbol": "TSLA"},
        {"exchange": "NASDAQ", "symbol": "NVDA"},
    ]
    print(f"\n1. 종목 리스트: {symbols}")
    
    # 2. HistoricalDataNode 출력 시뮬레이션
    historical_values = generate_historical_data_output(symbols, days=100)
    print(f"\n2. HistoricalDataNode 출력:")
    print(f"   - values 배열 길이: {len(historical_values)}")
    for item in historical_values:
        print(f"   - {item['symbol']}: {len(item['time_series'])} bars")
    
    # 3. flatten() 적용
    print(f"\n3. flatten(values, 'time_series') 적용:")
    flattened_data = _flatten(historical_values, 'time_series')
    print(f"   - 평탄화 후 행 수: {len(flattened_data)}")
    
    if flattened_data:
        print(f"   - 첫 번째 행: {flattened_data[0]}")
        print(f"   - 마지막 행: {flattened_data[-1]}")
        
        # 종목별 행 수 확인
        symbol_counts = {}
        for row in flattened_data:
            sym = row.get("symbol", "?")
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        print(f"   - 종목별 행 수: {symbol_counts}")
    
    # 4. MACD 플러그인 호출
    print(f"\n4. MACD 조건 평가:")
    result = await macd_condition(
        data=flattened_data,
        fields={
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "signal_type": "bullish_cross",
        },
        symbols=symbols,
    )
    
    print(f"   - 결과: {result.get('result')}")
    print(f"   - 통과 종목: {result.get('passed_symbols')}")
    print(f"   - 실패 종목: {result.get('failed_symbols')}")
    
    if result.get('symbol_results'):
        print(f"\n   종목별 상세:")
        for sr in result['symbol_results']:
            error = sr.get('error', '')
            if error:
                print(f"   - {sr['symbol']}: ERROR = {error}")
            else:
                print(f"   - {sr['symbol']}: MACD={sr['macd']:.4f}, Signal={sr['signal']:.4f}, Hist={sr['histogram']:.4f}")
    
    if result.get('values'):
        print(f"\n   values (time_series 포함):")
        for v in result['values']:
            ts_len = len(v.get('time_series', []))
            print(f"   - {v['symbol']}: {ts_len} time_series entries")
    
    return result


@pytest.mark.asyncio
async def test_empty_time_series():
    """빈 time_series 테스트 (데이터 부족 시나리오)"""
    from programgarden_community.plugins.macd import macd_condition
    
    print("\n" + "=" * 60)
    print("테스트: 빈 time_series (API 응답 없음 시뮬레이션)")
    print("=" * 60)
    
    # HistoricalDataNode가 빈 time_series를 반환하는 경우
    historical_values = [
        {"symbol": "AAPL", "exchange": "NASDAQ", "time_series": []},
        {"symbol": "TSLA", "exchange": "NASDAQ", "time_series": []},
        {"symbol": "NVDA", "exchange": "NASDAQ", "time_series": []},
    ]
    
    print(f"HistoricalDataNode 출력: time_series 모두 빈 배열")
    
    flattened_data = _flatten(historical_values, 'time_series')
    print(f"flatten 후 행 수: {len(flattened_data)}")
    
    result = await macd_condition(
        data=flattened_data,
        fields={"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"},
        symbols=[
            {"exchange": "NASDAQ", "symbol": "AAPL"},
            {"exchange": "NASDAQ", "symbol": "TSLA"},
            {"exchange": "NASDAQ", "symbol": "NVDA"},
        ],
    )
    
    print(f"결과: {result}")
    print(f"- 이것이 사용자가 받은 에러와 동일한지 확인!")


@pytest.mark.asyncio
async def test_short_time_series():
    """짧은 time_series 테스트 (데이터 부족)"""
    from programgarden_community.plugins.macd import macd_condition
    
    print("\n" + "=" * 60)
    print("테스트: 짧은 time_series (30일 < 35일 필요)")
    print("=" * 60)
    
    random.seed(42)
    symbols = [
        {"exchange": "NASDAQ", "symbol": "AAPL"},
        {"exchange": "NASDAQ", "symbol": "TSLA"},
        {"exchange": "NASDAQ", "symbol": "NVDA"},
    ]
    
    # 30일 데이터만 (MACD는 26+9=35일 필요)
    historical_values = generate_historical_data_output(symbols, days=30)
    
    print(f"HistoricalDataNode 출력: 각 종목 30일 데이터")
    
    flattened_data = _flatten(historical_values, 'time_series')
    print(f"flatten 후 행 수: {len(flattened_data)}")
    
    result = await macd_condition(
        data=flattened_data,
        fields={"fast_period": 12, "slow_period": 26, "signal_period": 9, "signal_type": "bullish_cross"},
        symbols=symbols,
    )
    
    print(f"결과: {result.get('result')}")
    if result.get('symbol_results'):
        for sr in result['symbol_results']:
            print(f"- {sr['symbol']}: error={sr.get('error', 'none')}")


async def main():
    """메인 테스트"""
    # 정상 케이스
    await test_data_flow()
    
    # 에러 케이스 1: 빈 time_series
    await test_empty_time_series()
    
    # 에러 케이스 2: 짧은 time_series
    await test_short_time_series()
    
    print("\n" + "=" * 60)
    print("🎯 결론")
    print("=" * 60)
    print("""
사용자가 받은 에러 분석:
- 모든 종목에서 "insufficient_data" 에러 발생
- 이는 flatten() 후 데이터가 비어있거나
- HistoricalDataNode가 time_series를 빈 배열로 반환했기 때문

확인 필요 사항:
1. HistoricalDataNode가 실제로 데이터를 가져오고 있는지
2. API 응답에서 block1이 비어있는지
3. start_date/end_date 범위가 올바른지
4. 종목 코드가 유효한지 (AAPL, TSLA, NVDA)
""")


if __name__ == "__main__":
    asyncio.run(main())
